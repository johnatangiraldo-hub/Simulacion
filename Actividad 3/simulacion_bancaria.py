"""Simulación reproducible del laboratorio de cajas bancarias.

Cada caja tiene una cola FIFO independiente y un único servidor. Los usuarios
que llegan antes del minuto 480 conservan su lugar; se termina de atenderlos
después del cierre para medir su espera completa y el trabajo adicional.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

CIERRE = 480.0
TIPOS = ("Rápido", "Normal", "Lento", "Muy lento")
ACCIONES = ("Retiro", "Pago")
PROB_ACCION = {"Retiro": 0.70, "Pago": 0.30}
PROB_TIPO = {"Retiro": (0.23, 0.40, 0.17, 0.20),
             "Pago": (0.10, 0.20, 0.30, 0.40)}
MEDIA_SERVICIO = {"Retiro": (1.0, 2.0, 3.0, 4.0),
                  "Pago": (3.0, 3.0, 5.0, 7.0)}
MEDIA_ENTRELLEGADA = {"Retiro": (1.0, 2.0, 3.0, 3.0),
                      "Pago": (1.0, 2.0, 3.0, 4.0)}

# Etiquetas fijas: garantizan que las tablas y la memoria se puedan reproducir.
ESCENARIOS = {
    "A_3_mixtas": ("Mixto", "Mixto", "Mixto"),
    "B_1R_2P": ("Retiro", "Pago", "Pago"),
    "C_2R_1P": ("Retiro", "Retiro", "Pago"),
    "D_4_mixtas": ("Mixto", "Mixto", "Mixto", "Mixto"),
    "E_2R_2P": ("Retiro", "Retiro", "Pago", "Pago"),
    "F_1R_3P": ("Retiro", "Pago", "Pago", "Pago"),
    "G_3R_1P": ("Retiro", "Retiro", "Retiro", "Pago"),
}


@dataclass(frozen=True)
class Cliente:
    numero: int
    llegada: float
    accion: str
    tipo: str
    servicio: float


def media_global_llegada() -> float:
    """Media teórica ponderada de los intervalos condicionados por clase."""
    return sum(PROB_ACCION[a] * sum(p * m for p, m in zip(PROB_TIPO[a],
               MEDIA_ENTRELLEGADA[a])) for a in ACCIONES)


def generar_clientes(semilla: int, replica: int, modo: str = "condicional",
                    cierre: float = CIERRE) -> list[Cliente]:
    """Construye un día aleatorio independiente de la asignación de cajas.

    condicional: reproduce literalmente la tabla 1: E[intervalo | acción,tipo].
    poisson: intervalo ~ Exp(media ponderada) independiente de la clase.
    Este segundo modo conserva proporciones y llegadas Poisson agregadas,
    pero NO reproduce las medias de llegada individuales de la tabla 1.
    """
    if modo not in ("condicional", "poisson"):
        raise ValueError("El modo debe ser 'condicional' o 'poisson'.")
    if replica < 1 or semilla < 0 or cierre <= 0:
        raise ValueError("Réplica >= 1, semilla >= 0 y cierre > 0.")
    rng_clase = np.random.default_rng(np.random.SeedSequence([semilla, replica, 1]))
    rng_llegada = np.random.default_rng(np.random.SeedSequence([semilla, replica, 2]))
    rng_servicio = np.random.default_rng(np.random.SeedSequence([semilla, replica, 3]))
    clientes = []
    instante = 0.0
    while True:
        accion = "Retiro" if rng_clase.random() < PROB_ACCION["Retiro"] else "Pago"
        indice = int(rng_clase.choice(4, p=PROB_TIPO[accion]))
        media = (MEDIA_ENTRELLEGADA[accion][indice] if modo == "condicional"
                 else media_global_llegada())
        instante += float(rng_llegada.exponential(media))
        if instante >= cierre:
            break
        # Muestrear el servicio aquí garantiza un día idéntico por escenario.
        servicio = float(rng_servicio.exponential(MEDIA_SERVICIO[accion][indice]))
        clientes.append(Cliente(len(clientes) + 1, instante, accion,
                                TIPOS[indice], servicio))
    return clientes


def simular_escenario(clientes: list[Cliente], capacidades: tuple[str, ...],
                     cierre: float = CIERRE) -> list[dict]:
    """Enruta al servidor elegible con menos trabajos pendientes.

    Cada caja conserva su propia cola FIFO. En empate se prefiere la caja cuya
    agenda acaba antes; se rota el siguiente empate mediante el ID del cliente.
    Una caja libre comienza a atender de inmediato; el servicio no dura cero.
    """
    if not capacidades or any(c not in (*ACCIONES, "Mixto") for c in capacidades):
        raise ValueError("La configuración contiene cajas inválidas.")
    pendientes = [deque() for _ in capacidades]
    registros = []
    anterior = -1.0
    for cliente in clientes:
        if cliente.llegada < anterior or cliente.llegada >= cierre:
            raise ValueError("Llegadas fuera de orden o después del cierre.")
        anterior = cliente.llegada
        candidatos = []
        for i, clase_caja in enumerate(capacidades):
            if clase_caja not in (cliente.accion, "Mixto"):
                continue
            # La agenda contiene los finales previstos de trabajos pendientes.
            while pendientes[i] and pendientes[i][0] <= cliente.llegada:
                pendientes[i].popleft()
            candidatos.append(i)
        if not candidatos:
            raise ValueError("Un tipo de operación no tiene cajas asignadas.")
        puntuaciones = [(len(pendientes[i]),
                         pendientes[i][-1] if pendientes[i] else cliente.llegada)
                        for i in candidatos]
        mejor = min(puntuaciones)
        empatados = [i for i, valor in zip(candidatos, puntuaciones) if valor == mejor]
        i = empatados[(cliente.numero - 1) % len(empatados)]
        inicio = max(cliente.llegada, pendientes[i][-1] if pendientes[i] else cliente.llegada)
        fin = inicio + cliente.servicio
        pendientes[i].append(fin)
        registros.append({"numero": cliente.numero, "llegada": cliente.llegada,
                         "accion": cliente.accion, "tipo": cliente.tipo,
                         "caja": f"C{i + 1}", "capacidad": capacidades[i],
                         "inicio": inicio, "fin": fin,
                         "espera": inicio - cliente.llegada,
                         "servicio": cliente.servicio,
                         "sistema": fin - cliente.llegada,
                         "finalizado_al_cierre": int(fin <= cierre)})
    return registros


def _promedio(valores: list[float]) -> float:
    return statistics.mean(valores) if valores else 0.0


def _percentil95(valores: list[float]) -> float:
    return float(np.percentile(valores, 95)) if valores else 0.0


def _demanda(clientes: list[Cliente], replica: int) -> dict:
    fila = {"replica": replica, "total": len(clientes)}
    for accion in ACCIONES:
        fila[accion] = sum(c.accion == accion for c in clientes)
        for tipo in TIPOS:
            fila[f"{accion}_{tipo}"] = sum(c.accion == accion and c.tipo == tipo
                                            for c in clientes)
    for tipo in TIPOS:
        fila[f"Todos_{tipo}"] = sum(c.tipo == tipo for c in clientes)
    return fila


def _resumen(registros: list[dict], replica: int, escenario: str,
             capacidades: tuple[str, ...], cierre: float) -> tuple[dict, list[dict], list[dict]]:
    esperas = [r["espera"] for r in registros]
    fila = {"replica": replica, "escenario": escenario,
            "cajas": len(capacidades), "llegados": len(registros),
            "retiros": sum(r["accion"] == "Retiro" for r in registros),
            "pagos": sum(r["accion"] == "Pago" for r in registros),
            "terminados_al_cierre": sum(r["finalizado_al_cierre"] for r in registros),
            "pendientes_al_cierre": sum(not r["finalizado_al_cierre"] for r in registros),
            "espera_media": _promedio(esperas),
            "espera_p95": _percentil95(esperas),
            "espera_max": max(esperas, default=0),
            "servicio_medio": _promedio([r["servicio"] for r in registros]),
            "sistema_medio": _promedio([r["sistema"] for r in registros]),
            "atencion_fuera_horario": max(0.0, max((r["fin"] for r in registros), default=0) - cierre),
            "Lq_durante_horario": sum(max(0.0, min(r["inicio"], cierre) - r["llegada"])
                                     for r in registros) / cierre}
    for accion in ACCIONES:
        filas = [r for r in registros if r["accion"] == accion]
        fila[f"espera_{accion}"] = _promedio([r["espera"] for r in filas])
        fila[f"espera_p95_{accion}"] = _percentil95([r["espera"] for r in filas])
        fila[f"pendientes_{accion}"] = sum(not r["finalizado_al_cierre"] for r in filas)

    cajas = []
    for i, capacidad in enumerate(capacidades):
        filas = [r for r in registros if r["caja"] == f"C{i + 1}"]
        ocupado_en_horario = sum(max(0.0, min(r["fin"], cierre) - r["inicio"])
                                 for r in filas if r["inicio"] < cierre)
        cajas.append({"replica": replica, "escenario": escenario,
                      "caja": f"C{i + 1}", "capacidad": capacidad,
                      "clientes": len(filas), "servicio_medio": _promedio([r["servicio"] for r in filas]),
                      "espera_media": _promedio([r["espera"] for r in filas]),
                      "utilizacion_horario": ocupado_en_horario / cierre})
    fila["utilizacion_media"] = _promedio([c["utilizacion_horario"] for c in cajas])

    tipos = []
    for accion in ACCIONES:
        for tipo in TIPOS:
            filas = [r for r in registros if r["accion"] == accion and r["tipo"] == tipo]
            tipos.append({"replica": replica, "escenario": escenario,
                          "accion": accion, "tipo": tipo,
                          "llegados": len(filas),
                          "finalizados_al_cierre": sum(r["finalizado_al_cierre"] for r in filas),
                          "espera_media": _promedio([r["espera"] for r in filas])})
    return fila, cajas, tipos


def _escribir_csv(ruta: Path, filas: list[dict]) -> None:
    if not filas:
        return
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def ejecutar(replicas: int = 30, semilla: int = 20261122,
            modo: str = "condicional", salida: Path | None = None,
            cierre: float = CIERRE) -> dict:
    """Ejecuta réplicas independientes y escenarios emparejados dentro del día."""
    if replicas < 10:
        raise ValueError("El laboratorio exige un mínimo de 10 réplicas.")
    if salida is None:
        salida = Path("resultados")
    salida.mkdir(parents=True, exist_ok=True)
    demanda, corridas, cajas, por_tipo, detalle = [], [], [], [], []
    for replica in range(1, replicas + 1):
        clientes = generar_clientes(semilla, replica, modo, cierre)
        demanda.append(_demanda(clientes, replica))
        for escenario, capacidades in ESCENARIOS.items():
            registros = simular_escenario(clientes, capacidades, cierre)
            resumen, cajas_rep, tipos_rep = _resumen(registros, replica,
                                                      escenario, capacidades, cierre)
            corridas.append(resumen)
            cajas.extend(cajas_rep)
            por_tipo.extend(tipos_rep)
            detalle.extend(dict(replica=replica, escenario=escenario, **r)
                           for r in registros)
    for nombre, filas in (("demanda_por_replica", demanda), ("escenarios_por_replica", corridas),
                          ("cajeros_por_replica", cajas), ("tipos_por_replica", por_tipo),
                          ("clientes_detalle", detalle)):
        _escribir_csv(salida / f"{nombre}.csv", filas)
    metadata = {"replicas": replicas, "semilla_base": semilla, "modo": modo,
                "cierre_minutos": cierre, "media_global_entrellegadas_teorica": media_global_llegada(),
                "escenarios": ESCENARIOS,
                "regla": "menor número pendiente, luego finalización prevista, luego empate rotativo",
                "cohorte": "llegados antes del cierre; se termina el servicio después del cierre"}
    (salida / "configuracion.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    return metadata


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--replicas", type=int, default=30)
    analizador.add_argument("--semilla", type=int, default=20261122)
    analizador.add_argument("--modo", choices=("condicional", "poisson"), default="condicional")
    analizador.add_argument("--salida", type=Path, default=Path("resultados"))
    parametros = analizador.parse_args()
    print(json.dumps(ejecutar(parametros.replicas, parametros.semilla, parametros.modo,
                             parametros.salida), ensure_ascii=False, indent=2))
