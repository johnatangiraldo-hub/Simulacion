"""Simulación de los cajeros de pago del parqueadero del centro comercial Supercentro.

Actividad didáctica 2-M4 · Simulación · Grupo 15 (IU Digital de Antioquia).

Metodología USA → MODIFICA → CREA. Las etiquetas en los comentarios indican el origen:
  [USA]         reutilizado de la Actividad 3 (simulacion_bancaria.py, problema bancario).
  [MODIFICA Mx] adaptado al problema del parqueadero.
  [CREA Cx]     componente nuevo de esta actividad.
El detalle de cada cambio está en MODIFICACIONES.md.

Modelo: cada salida tiene 3 cajeros con filas independientes, sin cambio de fila ni
abandono. Cada cajero se comporta como un servidor único (tipo M/M/1) que recibe su propio
flujo de usuarios. El cajero responde de inmediato; el tiempo de servicio es lo que tarda
el usuario en digitar la placa, seleccionar el vehículo y pagar.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Parámetros del enunciado
# ---------------------------------------------------------------------------
HORIZONTE = 720.0  # [MODIFICA M1] jornada de 12 h (10:00-22:00); antes 480 min del banco
TIPOS = ("Rápido", "Normal", "Lento", "Muy lento")
# [MODIFICA M2] una sola operación (pago) y 4 tipos; el 55 % restante se reparte por partes
# iguales entre lentos y muy lentos (supuesto del grupo, con análisis de sensibilidad).
PROB_TIPO = (0.25, 0.20, 0.275, 0.275)
MEDIA_SERVICIO = (1.0, 3.0, 4.0, 6.0)   # minutos (exponencial de uso del servicio)
MEDIA_LLEGADA = (3.0, 3.0, 5.0, 7.0)    # minutos (media de llegada)
CAJEROS_ACTUALES = 3
SEMILLA = 20261128

# [CREA C1] Estrategias evaluadas: (número de cajeros, regla de asignación)
#   propio         : cada cajero recibe su propio flujo (situación actual, M/M/1 independientes)
#   aleatoria      : la misma demanda total se reparte al azar entre más cajeros
#   fila_mas_corta : una pantalla indica la fila más corta y el usuario se ubica en ella
#   fila_unica     : una sola fila alimenta a todos los cajeros (el primero libre atiende)
ESCENARIOS = {
    "A_3_actual": (3, "propio"),
    "B_4_cajeros": (4, "aleatoria"),
    "C_5_cajeros": (5, "aleatoria"),
    "D_3_fila_mas_corta": (3, "fila_mas_corta"),
    "E_4_fila_mas_corta": (4, "fila_mas_corta"),
    "F_3_fila_unica": (3, "fila_unica"),
}


@dataclass(frozen=True)
class Usuario:  # [USA] equivalente a la clase Cliente de la Actividad 3
    numero: int
    flujo: int        # cajero de origen en la situación actual (0, 1, 2)
    llegada: float
    tipo: str
    servicio: float


def medias_teoricas(prob: tuple[float, ...] = PROB_TIPO) -> dict:
    """[USA] Medias ponderadas; [MODIFICA M3] se agregan ρ y los segundos momentos."""
    p, s, a = np.array(prob), np.array(MEDIA_SERVICIO), np.array(MEDIA_LLEGADA)
    es, ea = float(p @ s), float(p @ a)
    es2, ea2 = float(2 * p @ s**2), float(2 * p @ a**2)  # E[X²] de una mezcla de exponenciales
    return {"E_servicio": es, "E_entrellegada": ea, "rho": es / ea, "lambda": 1 / ea,
            "E_servicio2": es2, "E_entrellegada2": ea2,
            "cs2": (es2 - es**2) / es**2, "ca2": (ea2 - ea**2) / ea**2}


def generar_usuarios(semilla: int, replica: int, flujos: int = CAJEROS_ACTUALES,
                     horizonte: float = HORIZONTE, modo: str = "condicional",
                     prob: tuple[float, ...] = PROB_TIPO) -> list[Usuario]:
    """Genera la demanda de un día, independiente de cómo se organicen los cajeros.

    condicional: [USA] el intervalo hasta la llegada usa la media del tipo del usuario que llega.
    mm1:         [CREA C2] llegadas y servicios exponenciales con una sola media (M/M/1 puro),
                 usado solo para verificar el motor contra las fórmulas exactas.
    [MODIFICA M4] Se genera un flujo independiente por cada cajero actual (filas independientes).
    """
    if modo not in ("condicional", "mm1"):
        raise ValueError("modo debe ser 'condicional' o 'mm1'")
    teo = medias_teoricas(prob)
    usuarios = []
    for f in range(flujos):
        rng_tipo = np.random.default_rng(np.random.SeedSequence([semilla, replica, f, 1]))
        rng_lleg = np.random.default_rng(np.random.SeedSequence([semilla, replica, f, 2]))
        rng_serv = np.random.default_rng(np.random.SeedSequence([semilla, replica, f, 3]))
        t = 0.0
        while True:
            k = int(rng_tipo.choice(4, p=prob))
            media_a = MEDIA_LLEGADA[k] if modo == "condicional" else teo["E_entrellegada"]
            t += float(rng_lleg.exponential(media_a))
            if t >= horizonte:
                break
            media_s = MEDIA_SERVICIO[k] if modo == "condicional" else teo["E_servicio"]
            usuarios.append(Usuario(0, f, t, TIPOS[k], float(rng_serv.exponential(media_s))))
    usuarios.sort(key=lambda u: u.llegada)
    return [Usuario(i + 1, u.flujo, u.llegada, u.tipo, u.servicio) for i, u in enumerate(usuarios)]


def simular(usuarios: list[Usuario], cajeros: int, regla: str, semilla_azar: int = 0) -> list[dict]:
    """Atiende a los usuarios según la regla. Cola FIFO, sin cambio de fila ni abandono."""
    libre = [0.0] * cajeros                 # [USA] instante en que cada cajero queda libre
    pendientes = [[] for _ in range(cajeros)]  # fines previstos (para contar la fila)
    servidores = [(0.0, i) for i in range(cajeros)]  # [CREA C1] montículo para la fila única
    heapq.heapify(servidores)
    rng = np.random.default_rng(np.random.SeedSequence([semilla_azar, cajeros, 99]))
    azar = rng.integers(0, cajeros, size=len(usuarios))  # azar común para todos los escenarios
    registros = []
    for j, u in enumerate(usuarios):
        if regla == "propio":
            if cajeros != CAJEROS_ACTUALES:
                raise ValueError("La regla 'propio' solo aplica con los 3 cajeros actuales")
            i = u.flujo
        elif regla == "aleatoria":
            i = int(azar[j])
        elif regla == "fila_mas_corta":
            for c in range(cajeros):
                pendientes[c] = [x for x in pendientes[c] if x > u.llegada]
            n_min = min(len(p) for p in pendientes)
            empatados = [c for c in range(cajeros) if len(pendientes[c]) == n_min]
            i = empatados[int(azar[j]) % len(empatados)]
        elif regla == "fila_unica":
            libre_i, i = heapq.heappop(servidores)
            libre[i] = libre_i
        else:
            raise ValueError(f"Regla desconocida: {regla}")
        inicio = max(u.llegada, libre[i])
        fin = inicio + u.servicio
        libre[i] = fin
        if regla == "fila_unica":
            heapq.heappush(servidores, (fin, i))
        else:
            pendientes[i].append(fin)
        registros.append({"numero": u.numero, "flujo": u.flujo, "tipo": u.tipo,
                          "llegada": u.llegada, "cajero": f"C{i + 1}", "inicio": inicio,
                          "fin": fin, "espera": inicio - u.llegada, "servicio": u.servicio,
                          "sistema": fin - u.llegada})
    return registros


def escribir_csv(ruta: Path, filas: list[dict]) -> None:  # [USA]
    if not filas:
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def correr_replicas(replicas: int, semilla: int = SEMILLA, escenarios: dict = ESCENARIOS,
                    modo: str = "condicional", prob: tuple[float, ...] = PROB_TIPO) -> dict:
    """[USA] Réplicas independientes; en cada una, todos los escenarios reciben los mismos
    usuarios (números aleatorios comunes). Devuelve {escenario: [registros por réplica]}."""
    salida = {e: [] for e in escenarios}
    for r in range(1, replicas + 1):
        usuarios = generar_usuarios(semilla, r, modo=modo, prob=prob)
        for e, (c, regla) in escenarios.items():
            salida[e].append(simular(usuarios, c, regla, semilla_azar=semilla * 1000 + r))
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Simulación de cajeros del parqueadero")
    ap.add_argument("--replicas", type=int, default=10)
    ap.add_argument("--semilla", type=int, default=SEMILLA)
    ap.add_argument("--salida", type=Path, default=Path("resultados"))
    a = ap.parse_args()
    datos = correr_replicas(a.replicas, a.semilla)
    filas = [dict(replica=r + 1, **reg) for r, regs in enumerate(datos["A_3_actual"]) for reg in regs]
    escribir_csv(a.salida / "usuarios_situacion_actual.csv", filas)
    print(json.dumps({"replicas": a.replicas, "usuarios": len(filas),
                      **medias_teoricas()}, ensure_ascii=False, indent=2))
