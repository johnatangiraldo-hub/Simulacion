#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Simulación del juego Yahtzee clásico (2 jugadores) con el método de Montecarlo
===============================================================================
 Materia : Simulación  -  Actividad didáctica 2-M1
 Autor   : Johnatan Giraldo Cardona

 Variable aleatoria : valor de cada dado, X ~ Uniforme discreta {1,...,6}
                      P(X = k) = 1/6,  E[X] = 3.5,  Var(X) = 35/12 ≈ 2.917

 Modos de ejecución (ver README.md):
   python3 yahtzee_montecarlo.py                      -> menú interactivo
   python3 yahtzee_montecarlo.py interactivo          -> 2 jugadores humanos
   python3 yahtzee_montecarlo.py interactivo --rival ia
   python3 yahtzee_montecarlo.py partida              -> 1 partida narrada IA vs IA
   python3 yahtzee_montecarlo.py simulacion -n 1000   -> N partidas + estadísticas
   python3 yahtzee_montecarlo.py probabilidades -n 200000
   python3 yahtzee_montecarlo.py convergencia -n 100000
   python3 yahtzee_montecarlo.py todo                 -> genera todos los resultados

 Los resultados (tablas CSV y gráficos PNG) se guardan en la carpeta
 "resultados/" junto a este archivo. Los gráficos requieren matplotlib.
===============================================================================
"""

import argparse
import csv
import itertools
import math
import os
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# =============================================================================
# 1. PARÁMETROS DEL JUEGO
# =============================================================================
NUM_DADOS = 5              # dados por lanzamiento
CARAS = 6                  # caras de cada dado
MAX_LANZAMIENTOS = 3       # lanzamientos por turno (1 inicial + 2 relanzamientos)
TURNOS = 13                # turnos por jugador (uno por categoría)

CATEGORIAS = [
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "threeOfKind", "fourOfKind", "fullHouse",
    "smallStraight", "largeStraight", "yahtzee", "chance",
]

NOMBRES = {
    "ones": "Unos", "twos": "Doses", "threes": "Treses",
    "fours": "Cuatros", "fives": "Cincos", "sixes": "Seises",
    "threeOfKind": "Trío", "fourOfKind": "Póker", "fullHouse": "Full House",
    "smallStraight": "Escalera Menor", "largeStraight": "Escalera Mayor",
    "yahtzee": "Yahtzee", "chance": "Chance",
}

# Cuando dos categorías dan el mismo puntaje, se usa primero la que aparece
# antes en esta lista (se "sacrifican" primero las de menor valor y se
# reserva Chance para el final).
PREFERENCIA_EMPATE = [
    "yahtzee", "largeStraight", "smallStraight", "fullHouse", "fourOfKind",
    "threeOfKind", "sixes", "fives", "fours", "threes", "twos", "ones", "chance",
]
SACRIFICIO = [  # orden en que se anota un 0 cuando ninguna categoría da puntos
    "ones", "yahtzee", "twos", "largeStraight", "threes", "fourOfKind",
    "smallStraight", "fullHouse", "fours", "fives", "sixes", "threeOfKind", "chance",
]

CARPETA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

# Generador pseudoaleatorio (Mersenne Twister). Se usa una instancia propia
# para poder fijar la semilla y reproducir los experimentos.
RNG = random.Random()


def fijar_semilla(semilla: Optional[int]) -> None:
    """Fija la semilla del generador (None = aleatorio)."""
    RNG.seed(semilla)


# =============================================================================
# 2. GENERACIÓN DE NÚMEROS ALEATORIOS  (núcleo del método de Montecarlo)
# =============================================================================
def lanzar_dado() -> int:
    """
    Lanza un dado con distribución uniforme discreta en {1,...,6}.

    U ~ Uniforme continua [0, 1)  ->  X = floor(6·U) + 1
    Cada cara tiene probabilidad exacta 1/6 (equivalente a
    Math.floor(Math.random() * 6) + 1 del material del curso).
    """
    u = RNG.random()
    return int(u * CARAS) + 1


def lanzar_dados(valores: List[int], bloqueados: Sequence[bool]) -> List[int]:
    """
    Relanza solo los dados NO bloqueados (modifica 'valores').
    Devuelve la lista de valores efectivamente lanzados (para estadísticas).
    """
    lanzados = []
    for i in range(NUM_DADOS):
        if not bloqueados[i]:
            valores[i] = lanzar_dado()
            lanzados.append(valores[i])
    return lanzados


# =============================================================================
# 3. REGLAS DE PUNTUACIÓN
# =============================================================================
def hay_escalera(valores: Sequence[int], largo: int) -> bool:
    """¿Existen 'largo' valores consecutivos entre los dados?"""
    unicos = sorted(set(valores))
    mejor = actual = 1
    for a, b in zip(unicos, unicos[1:]):
        actual = actual + 1 if b == a + 1 else 1
        mejor = max(mejor, actual)
    return mejor >= largo


def puntuar(categoria: str, dados: Sequence[int]) -> int:
    """Puntaje que obtienen los 'dados' en la 'categoria' (reglas clásicas)."""
    conteo = Counter(dados)
    frecuencias = conteo.values()
    suma = sum(dados)
    if categoria in CATEGORIAS[:6]:                 # Unos ... Seises
        cara = CATEGORIAS.index(categoria) + 1
        return conteo[cara] * cara
    if categoria == "threeOfKind":
        return suma if max(frecuencias) >= 3 else 0
    if categoria == "fourOfKind":
        return suma if max(frecuencias) >= 4 else 0
    if categoria == "fullHouse":
        return 25 if sorted(frecuencias) == [2, 3] else 0
    if categoria == "smallStraight":
        return 30 if hay_escalera(dados, 4) else 0
    if categoria == "largeStraight":
        return 40 if hay_escalera(dados, 5) else 0
    if categoria == "yahtzee":
        return 50 if max(frecuencias) == 5 else 0
    if categoria == "chance":
        return suma
    raise ValueError(f"Categoría desconocida: {categoria}")


# Tabla precalculada: para cada una de las 252 combinaciones posibles (sin
# orden) de 5 dados se guarda el puntaje en las 13 categorías. Acelera la
# simulación Montecarlo de las decisiones (miles de evaluaciones por turno).
TABLA_PUNTAJES: Dict[Tuple[int, ...], Dict[str, int]] = {
    combo: {c: puntuar(c, combo) for c in CATEGORIAS}
    for combo in itertools.combinations_with_replacement(range(1, CARAS + 1), NUM_DADOS)
}


def puntajes_de(dados: Sequence[int]) -> Dict[str, int]:
    return TABLA_PUNTAJES[tuple(sorted(dados))]


def mejor_categoria(dados: Sequence[int], disponibles: Sequence[str]) -> Tuple[str, int]:
    """
    Elige la categoría disponible que da más puntos.
    Empates -> PREFERENCIA_EMPATE; si todo da 0 -> se sacrifica según SACRIFICIO.
    """
    tabla = puntajes_de(dados)
    maximo = max(tabla[c] for c in disponibles)
    if maximo == 0:
        cat = next(c for c in SACRIFICIO if c in disponibles)
        return cat, 0
    candidatas = [c for c in disponibles if tabla[c] == maximo]
    cat = min(candidatas, key=PREFERENCIA_EMPATE.index)
    return cat, maximo


def valor_final(dados: Sequence[int], disponibles: Sequence[str]) -> int:
    """Puntos que se anotarían con estos dados (función objetivo del turno)."""
    return mejor_categoria(dados, disponibles)[1]


# =============================================================================
# 4. ESTRUCTURAS DE DATOS
# =============================================================================
@dataclass
class Estadisticas:
    """Acumula los resultados aleatorios para su análisis posterior."""
    dados_lanzados: int = 0                                  # dados individuales
    frecuencia_caras: Counter = field(default_factory=Counter)
    tiradas: int = 0                                         # lanzamientos (1 a 3 por turno)
    turnos: int = 0
    yahtzees: int = 0

    def registrar(self, valores_lanzados: List[int]) -> None:
        # Solo se cuentan los dados que realmente se lanzaron (no los bloqueados)
        self.dados_lanzados += len(valores_lanzados)
        self.frecuencia_caras.update(valores_lanzados)
        self.tiradas += 1

    def fusionar(self, otra: "Estadisticas") -> None:
        self.dados_lanzados += otra.dados_lanzados
        self.frecuencia_caras.update(otra.frecuencia_caras)
        self.tiradas += otra.tiradas
        self.turnos += otra.turnos
        self.yahtzees += otra.yahtzees


@dataclass
class Jugador:
    nombre: str
    estrategia: "Estrategia"
    puntajes: Dict[str, Optional[int]] = field(
        default_factory=lambda: {c: None for c in CATEGORIAS})

    @property
    def total(self) -> int:
        return sum(v for v in self.puntajes.values() if v is not None)

    def disponibles(self) -> List[str]:
        return [c for c in CATEGORIAS if self.puntajes[c] is None]


# =============================================================================
# 5. ESTRATEGIAS DE LOS JUGADORES
# =============================================================================
class Estrategia:
    nombre = "base"

    def elegir_bloqueo(self, dados, lanzamientos_restantes, disponibles) -> List[bool]:
        """Devuelve qué dados conservar (True = bloquear). Todo True = plantarse."""
        raise NotImplementedError

    def elegir_categoria(self, dados, disponibles) -> str:
        return mejor_categoria(dados, disponibles)[0]


def bloqueo_heuristico(dados: Sequence[int]) -> List[bool]:
    """Regla simple: conservar los dados del valor que más se repite
    (en empate, el valor más alto) y relanzar el resto."""
    conteo = Counter(dados)
    objetivo = max(conteo, key=lambda v: (conteo[v], v))
    return [d == objetivo for d in dados]


class EstrategiaHeuristica(Estrategia):
    """Jugador de referencia: conserva el valor más repetido; se planta si ya
    tiene Yahtzee, Escalera Mayor o Full House disponibles."""
    nombre = "Heurística (conservar el valor más repetido)"

    def elegir_bloqueo(self, dados, lanzamientos_restantes, disponibles):
        tabla = puntajes_de(dados)
        for c in ("yahtzee", "largeStraight", "fullHouse"):
            if c in disponibles and tabla[c] > 0:
                return [True] * NUM_DADOS
        return bloqueo_heuristico(dados)


class EstrategiaMontecarlo(Estrategia):
    """
    Jugador que decide qué dados conservar con el método de Montecarlo.

    Para cada una de las 32 formas de conservar dados (máscaras) simula
    'sims' veces el resto del turno y estima el valor esperado (EV) del
    puntaje final; elige la máscara con mayor EV estimado.
        EV(máscara) ≈ (1/N) · Σ puntaje_final_i
    Dentro de cada simulación, los lanzamientos posteriores al próximo se
    juegan con la regla heurística (política de "rollout").
    """

    def __init__(self, sims: int = 100):
        self.sims = sims
        self.nombre = f"Montecarlo ({sims} simulaciones por máscara)"

    def estimar_ev(self, dados, mascara, lanzamientos_restantes, disponibles, sims=None) -> float:
        sims = self.sims if sims is None else sims
        if all(mascara):                         # plantarse: valor conocido
            return float(valor_final(dados, disponibles))
        total = 0
        for _ in range(sims):
            sim = list(dados)
            lanzar_dados(sim, mascara)               # próximo lanzamiento
            for _ in range(lanzamientos_restantes - 1):  # lanzamientos posteriores
                lanzar_dados(sim, bloqueo_heuristico(sim))
            total += valor_final(sim, disponibles)
        return total / sims

    def elegir_bloqueo(self, dados, lanzamientos_restantes, disponibles):
        mejor_mascara, mejor_ev = None, -1.0
        evaluadas = set()
        for m in range(2 ** NUM_DADOS):
            mascara = [(m >> i) & 1 == 1 for i in range(NUM_DADOS)]
            # Máscaras que conservan los mismos valores son equivalentes
            clave = tuple(sorted(d for d, b in zip(dados, mascara) if b))
            if clave in evaluadas:
                continue
            evaluadas.add(clave)
            ev = self.estimar_ev(dados, mascara, lanzamientos_restantes, disponibles)
            if ev > mejor_ev:
                mejor_mascara, mejor_ev = mascara, ev
        return mejor_mascara


class EstrategiaHumana(Estrategia):
    """Decisiones tomadas por una persona desde la consola."""
    nombre = "Humano"

    def elegir_bloqueo(self, dados, lanzamientos_restantes, disponibles):
        print(f"   Te quedan {lanzamientos_restantes} lanzamiento(s).")
        while True:
            r = input("   ¿Qué dados conservas? Posiciones 1-5 separadas por espacio "
                      "(Enter = relanzar todos, 'p' = plantarse): ").strip().lower()
            if r == "p":
                return [True] * NUM_DADOS
            if r == "":
                return [False] * NUM_DADOS
            try:
                pos = {int(x) for x in r.replace(",", " ").split()}
                if pos <= set(range(1, NUM_DADOS + 1)):
                    return [(i + 1) in pos for i in range(NUM_DADOS)]
            except ValueError:
                pass
            print("   Entrada no válida. Ejemplo: 1 3 5")

    def elegir_categoria(self, dados, disponibles):
        tabla = puntajes_de(dados)
        print("   Categorías disponibles:")
        for i, c in enumerate(disponibles, 1):
            print(f"     {i:2d}. {NOMBRES[c]:15s} -> {tabla[c]:2d} puntos")
        while True:
            r = input("   Elige el número de la categoría: ").strip()
            if r.isdigit() and 1 <= int(r) <= len(disponibles):
                return disponibles[int(r) - 1]
            print("   Número no válido.")


# =============================================================================
# 6. FLUJO DEL JUEGO
# =============================================================================
def mostrar_dados(dados, bloqueados=None) -> str:
    caras = "⚀⚁⚂⚃⚄⚅"
    partes = []
    for i, d in enumerate(dados):
        candado = "🔒" if bloqueados and bloqueados[i] else ""
        partes.append(f"{caras[d - 1]} {d}{candado}")
    return "  ".join(partes)


def jugar_turno(jugador: Jugador, stats: Estadisticas, verbose: bool = False) -> Tuple[str, int]:
    """Un turno: hasta 3 lanzamientos con bloqueo de dados y anotación."""
    dados = [0] * NUM_DADOS
    bloqueados = [False] * NUM_DADOS
    disponibles = jugador.disponibles()

    stats.registrar(lanzar_dados(dados, bloqueados))         # lanzamiento 1
    restantes = MAX_LANZAMIENTOS - 1
    if verbose:
        print(f"   Lanzamiento 1: {mostrar_dados(dados)}")

    while restantes > 0:
        bloqueados = jugador.estrategia.elegir_bloqueo(dados, restantes, disponibles)
        if all(bloqueados):
            if verbose:
                print("   -> Se planta.")
            break
        stats.registrar(lanzar_dados(dados, bloqueados))
        restantes -= 1
        if verbose:
            n = MAX_LANZAMIENTOS - restantes
            print(f"   Lanzamiento {n}: {mostrar_dados(dados, bloqueados)}")

    categoria = jugador.estrategia.elegir_categoria(dados, disponibles)
    puntos = puntajes_de(dados)[categoria]
    jugador.puntajes[categoria] = puntos
    stats.turnos += 1
    if categoria == "yahtzee" and puntos == 50:
        stats.yahtzees += 1
    if verbose:
        print(f"   => Anota {puntos} en '{NOMBRES[categoria]}'. Total: {jugador.total}")
    return categoria, puntos


def jugar_partida(jugadores: List[Jugador], verbose: bool = False) -> Estadisticas:
    """13 rondas; en cada una juegan los 2 jugadores por turnos."""
    stats = Estadisticas()
    for ronda in range(1, TURNOS + 1):
        for j in jugadores:
            if verbose:
                print(f"\n--- Ronda {ronda}/{TURNOS} · {j.nombre} ({j.estrategia.nombre}) ---")
            jugar_turno(j, stats, verbose)
    return stats


def ganador(jugadores: List[Jugador]) -> str:
    a, b = jugadores
    if a.total == b.total:
        return "Empate"
    return a.nombre if a.total > b.total else b.nombre


def imprimir_marcador(jugadores: List[Jugador]) -> None:
    print("\n" + "=" * 52)
    print(f"{'MARCADOR FINAL':20s}" + "".join(f"{j.nombre:>16s}" for j in jugadores))
    print("=" * 52)
    for c in CATEGORIAS:
        print(f"{NOMBRES[c]:20s}" + "".join(f"{(j.puntajes[c] or 0):>16d}" for j in jugadores))
    print("-" * 52)
    print(f"{'TOTAL':20s}" + "".join(f"{j.total:>16d}" for j in jugadores))
    print(f"\n🏆 Ganador: {ganador(jugadores)}")


# =============================================================================
# 7. ANÁLISIS DE RESULTADOS
# =============================================================================
def clasificar_lanzamiento(dados: Sequence[int]) -> str:
    """Clasifica un lanzamiento de 5 dados en una combinación excluyente."""
    f = sorted(Counter(dados).values(), reverse=True)
    if f[0] == 5:
        return "Yahtzee"
    if f[0] == 4:
        return "Póker"
    if f == [3, 2]:
        return "Full House"
    if hay_escalera(dados, 5):
        return "Escalera Mayor"
    if hay_escalera(dados, 4):
        return "Escalera Menor"
    if f[0] == 3:
        return "Trío"
    if f[0] == 2 and f[1] == 2:
        return "Doble par"
    if f[0] == 2:
        return "Un par"
    return "Nada"


ORDEN_COMBINACIONES = ["Yahtzee", "Póker", "Full House", "Escalera Mayor",
                       "Escalera Menor", "Trío", "Doble par", "Un par", "Nada"]


def probabilidades_teoricas() -> Dict[str, float]:
    """Probabilidad exacta de cada combinación: enumeración de los 6^5 = 7776
    resultados equiprobables de un lanzamiento."""
    conteo = Counter(clasificar_lanzamiento(d)
                     for d in itertools.product(range(1, CARAS + 1), repeat=NUM_DADOS))
    total = CARAS ** NUM_DADOS
    return {k: conteo[k] / total for k in ORDEN_COMBINACIONES}


def chi_cuadrado_uniforme(frecuencias: Counter) -> Tuple[float, float]:
    """Estadístico chi-cuadrado contra la uniforme (gl = 5).
    Devuelve (chi2, valor crítico al 5 %)."""
    n = sum(frecuencias.values())
    esperado = n / CARAS
    chi2 = sum((frecuencias[k] - esperado) ** 2 / esperado for k in range(1, CARAS + 1))
    return chi2, 11.0705          # χ²(0.95; 5)


def asegurar_carpeta() -> str:
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    return CARPETA_RESULTADOS


def cargar_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("   (matplotlib no está instalado: se omiten los gráficos. "
              "Instálalo con: pip3 install matplotlib)")
        return None


def intervalo_95(p: float, n: int) -> float:
    """Medio ancho del intervalo de confianza del 95 % para una proporción."""
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 0.0


# ---------------------------------------------------------------------------
# 7.1 Probabilidades de un lanzamiento: Montecarlo vs teoría
# ---------------------------------------------------------------------------
def experimento_probabilidades(n: int = 200_000) -> Dict:
    print(f"\n📐 EXPERIMENTO 1: {n:,} lanzamientos de 5 dados")
    conteo = Counter()
    caras = Counter()
    for _ in range(n):
        d = [lanzar_dado() for _ in range(NUM_DADOS)]
        caras.update(d)
        conteo[clasificar_lanzamiento(d)] += 1
    teo = probabilidades_teoricas()

    print(f"\n{'Combinación':16s}{'Simulada':>11s}{'Teórica':>11s}{'Error abs.':>12s}{'IC 95 %':>11s}")
    filas = []
    for k in ORDEN_COMBINACIONES:
        p_sim = conteo[k] / n
        filas.append([k, conteo[k], p_sim, teo[k], abs(p_sim - teo[k]), intervalo_95(p_sim, n)])
        print(f"{k:16s}{p_sim*100:10.3f}%{teo[k]*100:10.3f}%{abs(p_sim-teo[k])*100:11.3f}%"
              f"{'±' + format(intervalo_95(p_sim, n)*100, '.3f') + '%':>11s}")

    total = sum(caras.values())
    media = sum(k * v for k, v in caras.items()) / total
    var = sum(v * (k - media) ** 2 for k, v in caras.items()) / total
    chi2, critico = chi_cuadrado_uniforme(caras)
    print(f"\nDados individuales: {total:,}")
    print(f"Media simulada {media:.4f}  (teórica 3.5000)")
    print(f"Varianza simulada {var:.4f}  (teórica {35/12:.4f})")
    print(f"Chi-cuadrado = {chi2:.3f}  (crítico 5 % = {critico}) -> "
          f"{'NO se rechaza' if chi2 < critico else 'Se rechaza'} la uniformidad")

    carpeta = asegurar_carpeta()
    with open(os.path.join(carpeta, "probabilidades_combinaciones.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["combinacion", "frecuencia", "prob_simulada", "prob_teorica", "error_abs", "ic95_medio_ancho"])
        for fila in filas:
            w.writerow([fila[0], fila[1]] + [f"{x:.6f}" for x in fila[2:]])

    plt = cargar_matplotlib()
    if plt:
        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(ORDEN_COMBINACIONES))
        ax.bar([i - 0.2 for i in x], [r[2] * 100 for r in filas], 0.4, label="Simulada (Montecarlo)")
        ax.bar([i + 0.2 for i in x], [r[3] * 100 for r in filas], 0.4, label="Teórica (7776 casos)")
        ax.set_xticks(list(x))
        for i, r in zip(x, filas):
            ax.text(i, max(r[2], r[3]) * 100 + 0.6, f"{r[2]*100:.2f}% | {r[3]*100:.2f}%",
                    ha="center", fontsize=7)
        ax.set_xticklabels(ORDEN_COMBINACIONES, rotation=30, ha="right")
        ax.set_ylabel("Probabilidad (%)")
        ax.set_title(f"Combinaciones en un lanzamiento de 5 dados (n = {n:,})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "probabilidades_combinaciones.png"), dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4.5))
        rel = [caras[k] / total * 100 for k in range(1, 7)]
        ax.bar(range(1, 7), rel, color="#4C72B0")
        ax.axhline(100 / 6, color="red", linestyle="--", label="Teórica 1/6 = 16.67 %")
        for k, v in zip(range(1, 7), rel):
            ax.text(k, v + 0.2, f"{v:.2f}%", ha="center", fontsize=9)
        ax.set_ylim(0, 20)
        ax.set_xlabel("Cara del dado")
        ax.set_ylabel("Frecuencia relativa (%)")
        ax.set_title(f"Distribución de las caras ({total:,} dados)")
        ax.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "distribucion_caras.png"), dpi=150)
        plt.close(fig)
    return {"filas": filas, "media": media, "varianza": var, "chi2": chi2, "dados": total}


# ---------------------------------------------------------------------------
# 7.2 Convergencia: probabilidad de Yahtzee en un turno (3 lanzamientos)
# ---------------------------------------------------------------------------
P_YAHTZEE_TURNO_REF = 2_783_176 / 6 ** 10   # ≈ 0.04603 (valor exacto conocido
                                             # conservando el valor más repetido)


def experimento_convergencia(n: int = 100_000) -> Dict:
    print(f"\n📈 EXPERIMENTO 2: convergencia de P(Yahtzee en un turno) con {n:,} turnos")
    exitos = 0
    puntos_control = sorted({int(10 ** (k / 4)) for k in range(4, int(4 * math.log10(n)) + 1)} | {n})
    serie = []
    for i in range(1, n + 1):
        d = [0] * NUM_DADOS
        lanzar_dados(d, [False] * NUM_DADOS)
        for _ in range(MAX_LANZAMIENTOS - 1):
            if max(Counter(d).values()) == 5:
                break
            lanzar_dados(d, bloqueo_heuristico(d))
        exitos += max(Counter(d).values()) == 5
        if i in puntos_control:
            serie.append((i, exitos / i))
    print(f"\n{'Turnos':>10s}{'Estimación':>13s}{'Error':>10s}")
    for i, p in serie:
        print(f"{i:>10,d}{p*100:12.3f}%{abs(p-P_YAHTZEE_TURNO_REF)*100:9.3f}%")
    p = exitos / n
    print(f"Referencia teórica: {P_YAHTZEE_TURNO_REF*100:.3f}%   IC 95 % de la estimación: "
          f"{p*100:.3f}% ± {intervalo_95(p, n)*100:.3f}%")

    carpeta = asegurar_carpeta()
    with open(os.path.join(carpeta, "convergencia_yahtzee.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["turnos", "estimacion", "referencia"])
        for i, q in serie:
            w.writerow([i, f"{q:.6f}", f"{P_YAHTZEE_TURNO_REF:.6f}"])

    plt = cargar_matplotlib()
    if plt:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        xs = [i for i, _ in serie]
        ys = [q * 100 for _, q in serie]
        ax.plot(xs, ys, marker="o", label="Estimación Montecarlo")
        ax.axhline(P_YAHTZEE_TURNO_REF * 100, color="red", linestyle="--",
                   label=f"Valor teórico ≈ {P_YAHTZEE_TURNO_REF*100:.2f} %")
        banda = [1.96 * math.sqrt(P_YAHTZEE_TURNO_REF * (1 - P_YAHTZEE_TURNO_REF) / i) * 100 for i in xs]
        ax.fill_between(xs, [max(0.0, P_YAHTZEE_TURNO_REF * 100 - b) for b in banda],
                        [P_YAHTZEE_TURNO_REF * 100 + b for b in banda], color="red", alpha=0.1,
                        label="Banda 95 % esperada")
        ax.set_xscale("log")
        ax.set_xlabel("Número de turnos simulados (escala log)")
        ax.set_ylabel("P(Yahtzee en un turno) (%)")
        ax.set_title("Convergencia del estimador (Ley de los Grandes Números)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "convergencia_yahtzee.png"), dpi=150)
        plt.close(fig)
    return {"serie": serie, "p": p, "n": n}


# ---------------------------------------------------------------------------
# 7.3 Simulación de N partidas completas entre 2 jugadores
# ---------------------------------------------------------------------------
def crear_jugadores(sims: int) -> List[Jugador]:
    return [Jugador("Jugador 1", EstrategiaMontecarlo(sims)),
            Jugador("Jugador 2", EstrategiaHeuristica())]


def experimento_partidas(n: int = 1000, sims: int = 100) -> Dict:
    print(f"\n🎲 EXPERIMENTO 3: {n:,} partidas completas")
    nombres = [j.estrategia.nombre for j in crear_jugadores(sims)]
    print(f"   Jugador 1: {nombres[0]}\n   Jugador 2: {nombres[1]}")
    totales = {"Jugador 1": [], "Jugador 2": []}
    por_categoria = {"Jugador 1": Counter(), "Jugador 2": Counter()}
    ceros = {"Jugador 1": Counter(), "Jugador 2": Counter()}
    victorias = Counter()
    stats_global = Estadisticas()
    filas = []
    t0 = time.time()
    for k in range(1, n + 1):
        jugadores = crear_jugadores(sims)
        stats = jugar_partida(jugadores)
        stats_global.fusionar(stats)
        g = ganador(jugadores)
        victorias[g] += 1
        for j in jugadores:
            totales[j.nombre].append(j.total)
            for c in CATEGORIAS:
                por_categoria[j.nombre][c] += j.puntajes[c]
                ceros[j.nombre][c] += j.puntajes[c] == 0
        filas.append([k, jugadores[0].total, jugadores[1].total, g, stats.yahtzees, stats.tiradas])
        if k % max(1, n // 10) == 0:
            print(f"   ... {k:,}/{n:,} partidas ({time.time() - t0:.0f} s)")
    duracion = time.time() - t0

    resumen = {}
    print(f"\n{'Indicador':28s}{'Jugador 1':>14s}{'Jugador 2':>14s}")
    for nombre in ("Jugador 1", "Jugador 2"):
        t = totales[nombre]
        resumen[nombre] = {
            "media": statistics.mean(t), "desv": statistics.stdev(t) if n > 1 else 0.0,
            "min": min(t), "max": max(t), "mediana": statistics.median(t),
            "victorias": victorias[nombre],
        }
    for etiqueta, clave, fmt in [("Puntaje promedio", "media", "{:.2f}"),
                                 ("Desviación estándar", "desv", "{:.2f}"),
                                 ("Mediana", "mediana", "{:.1f}"),
                                 ("Mínimo", "min", "{}"), ("Máximo", "max", "{}"),
                                 ("Victorias", "victorias", "{}")]:
        print(f"{etiqueta:28s}" + "".join(f"{fmt.format(resumen[x][clave]):>14s}"
                                          for x in ("Jugador 1", "Jugador 2")))
    for nombre in ("Jugador 1", "Jugador 2"):
        r = resumen[nombre]
        r["ic95"] = 1.96 * r["desv"] / math.sqrt(n)
        r["pct_victorias"] = r["victorias"] / n
    print(f"{'% de victorias':28s}" + "".join(f"{resumen[x]['pct_victorias']*100:>13.1f}%"
                                              for x in ("Jugador 1", "Jugador 2")))
    print(f"{'IC 95 % del promedio':28s}" + "".join(f"{'±' + format(resumen[x]['ic95'], '.2f'):>14s}"
                                                    for x in ("Jugador 1", "Jugador 2")))
    print(f"Empates: {victorias['Empate']}")
    chi2, critico = chi_cuadrado_uniforme(stats_global.frecuencia_caras)
    print(f"Dados lanzados en las partidas: {stats_global.dados_lanzados:,} · "
          f"Yahtzees: {stats_global.yahtzees} · χ² caras = {chi2:.2f} (crítico {critico})")
    print(f"Tiempo total: {duracion:.1f} s ({duracion / n:.3f} s por partida)")

    print(f"\n{'Promedio por categoría':22s}{'Jugador 1':>11s}{'Jugador 2':>11s}{'% ceros J1':>12s}{'% ceros J2':>12s}")
    for c in CATEGORIAS:
        print(f"{NOMBRES[c]:22s}{por_categoria['Jugador 1'][c]/n:11.2f}{por_categoria['Jugador 2'][c]/n:11.2f}"
              f"{ceros['Jugador 1'][c]/n*100:11.1f}%{ceros['Jugador 2'][c]/n*100:11.1f}%")

    carpeta = asegurar_carpeta()
    with open(os.path.join(carpeta, "partidas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["partida", "puntos_jugador1", "puntos_jugador2", "ganador", "yahtzees", "lanzamientos"])
        w.writerows(filas)
    with open(os.path.join(carpeta, "promedio_categorias.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "promedio_j1", "promedio_j2", "pct_ceros_j1", "pct_ceros_j2"])
        for c in CATEGORIAS:
            w.writerow([NOMBRES[c], f"{por_categoria['Jugador 1'][c]/n:.3f}",
                        f"{por_categoria['Jugador 2'][c]/n:.3f}",
                        f"{ceros['Jugador 1'][c]/n:.4f}", f"{ceros['Jugador 2'][c]/n:.4f}"])

    plt = cargar_matplotlib()
    if plt:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        lo = min(min(v) for v in totales.values())
        hi = max(max(v) for v in totales.values())
        bins = range(lo - lo % 10, hi + 10, 10)
        for nombre, color in (("Jugador 1", "#4C72B0"), ("Jugador 2", "#DD8452")):
            ax.hist(totales[nombre], bins=bins, alpha=0.6, color=color,
                    label=f"{nombre} (media {resumen[nombre]['media']:.1f})")
            ax.axvline(resumen[nombre]["media"], color=color, linestyle="--")
        ax.set_xlabel("Puntaje final de la partida")
        ax.set_ylabel("Número de partidas")
        ax.set_title(f"Distribución de puntajes finales ({n:,} partidas)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "puntajes_partidas.png"), dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(CATEGORIAS))
        ax.bar([i - 0.2 for i in x], [por_categoria["Jugador 1"][c] / n for c in CATEGORIAS], 0.4,
               label="Jugador 1 (Montecarlo)")
        ax.bar([i + 0.2 for i in x], [por_categoria["Jugador 2"][c] / n for c in CATEGORIAS], 0.4,
               label="Jugador 2 (Heurística)")
        ax.set_xticks(list(x))
        ax.set_xticklabels([NOMBRES[c] for c in CATEGORIAS], rotation=35, ha="right")
        ax.set_ylabel("Puntos promedio")
        ax.set_title("Puntaje promedio por categoría")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "promedio_categorias.png"), dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        etiquetas = ["Jugador 1", "Jugador 2", "Empate"]
        ax.bar(etiquetas, [victorias[e] / n * 100 for e in etiquetas],
               color=["#4C72B0", "#DD8452", "#999999"])
        for i, e in enumerate(etiquetas):
            ax.text(i, victorias[e] / n * 100 + 1, f"{victorias[e] / n * 100:.1f}%", ha="center")
        ax.set_ylabel("% de partidas")
        ax.set_ylim(0, 100)
        ax.set_title("Porcentaje de victorias")
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "victorias.png"), dpi=150)
        plt.close(fig)
    return {"resumen": resumen, "victorias": victorias, "por_categoria": por_categoria,
            "ceros": ceros, "n": n, "sims": sims, "duracion": duracion,
            "stats": stats_global, "chi2": chi2}


# ---------------------------------------------------------------------------
# 7.4 Efecto del número de simulaciones por máscara
# ---------------------------------------------------------------------------
def experimento_sensibilidad(partidas: int = 100, lista_sims=(5, 20, 100, 300)) -> List[Dict]:
    print(f"\n⚙️  EXPERIMENTO 4: efecto de las simulaciones por máscara ({partidas} partidas c/u)")
    print("(cada partida: 13 turnos de un jugador Montecarlo)")
    print(f"{'Sims/máscara':>13s}{'Promedio':>10s}{'IC 95 %':>10s}{'s/partida':>11s}")
    filas = []
    for s in lista_sims:
        estrategia = EstrategiaMontecarlo(s)
        t0 = time.time()
        totales = []
        for _ in range(partidas):
            j = Jugador("Jugador 1", estrategia)
            for _ in range(TURNOS):
                jugar_turno(j, Estadisticas())
            totales.append(j.total)
        dur = (time.time() - t0) / partidas
        media = statistics.mean(totales)
        ic = 1.96 * statistics.stdev(totales) / math.sqrt(partidas)
        filas.append({"sims": s, "media": media, "ic95": ic, "seg": dur})
        print(f"{s:>13d}{media:>10.2f}{'±' + format(ic, '.2f'):>10s}{dur:>11.3f}")
    carpeta = asegurar_carpeta()
    with open(os.path.join(carpeta, "sensibilidad_sims.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sims_por_mascara", "puntaje_promedio", "ic95", "segundos_por_partida"])
        for r in filas:
            w.writerow([r["sims"], f"{r['media']:.2f}", f"{r['ic95']:.2f}", f"{r['seg']:.4f}"])

    plt = cargar_matplotlib()
    if plt:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        xs = [str(r["sims"]) for r in filas]
        ax.errorbar(xs, [r["media"] for r in filas], yerr=[r["ic95"] for r in filas],
                    marker="o", capsize=5, label="Puntaje promedio (IC 95 %)")
        ax.set_xlabel("Simulaciones por máscara")
        ax.set_ylabel("Puntaje promedio por partida")
        ax2 = ax.twinx()
        ax2.plot(xs, [r["seg"] for r in filas], color="green", marker="s", linestyle="--",
                 label="Segundos por partida")
        ax2.set_ylabel("Segundos por partida", color="green")
        ax.set_title("Precisión vs costo computacional")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="lower right")
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, "sensibilidad_sims.png"), dpi=150)
        plt.close(fig)
    return filas


# =============================================================================
# 8. MODOS DE EJECUCIÓN
# =============================================================================
def modo_interactivo(rival: str = "humano", sims: int = 100) -> None:
    print("\n🎲 YAHTZEE - 2 jugadores (consola)")
    print("Reglas: 13 rondas; en cada turno hasta 3 lanzamientos de 5 dados;")
    print("puedes conservar dados entre lanzamientos y luego eliges una categoría.\n")
    n1 = input("Nombre del Jugador 1 [Jugador 1]: ").strip() or "Jugador 1"
    if rival == "ia":
        jugadores = [Jugador(n1, EstrategiaHumana()), Jugador("IA Montecarlo", EstrategiaMontecarlo(sims))]
    else:
        n2 = input("Nombre del Jugador 2 [Jugador 2]: ").strip() or "Jugador 2"
        jugadores = [Jugador(n1, EstrategiaHumana()), Jugador(n2, EstrategiaHumana())]
    stats = jugar_partida(jugadores, verbose=True)
    imprimir_marcador(jugadores)
    print(f"Dados lanzados: {stats.dados_lanzados} · Yahtzees: {stats.yahtzees}")


def modo_partida(sims: int = 100) -> None:
    jugadores = crear_jugadores(sims)
    stats = jugar_partida(jugadores, verbose=True)
    imprimir_marcador(jugadores)
    total = stats.dados_lanzados
    print(f"\nDados lanzados: {total} · Lanzamientos: {stats.tiradas} · Yahtzees: {stats.yahtzees}")
    for k in range(1, 7):
        print(f"  Cara {k}: {stats.frecuencia_caras[k]:3d} ({stats.frecuencia_caras[k] / total * 100:5.2f} %)")


def menu() -> None:
    opciones = {
        "1": ("Jugar: 2 jugadores humanos", lambda: modo_interactivo("humano")),
        "2": ("Jugar: humano vs IA Montecarlo", lambda: modo_interactivo("ia")),
        "3": ("Ver 1 partida narrada (IA vs IA)", lambda: modo_partida()),
        "4": ("Simular 1000 partidas + estadísticas", lambda: experimento_partidas(1000)),
        "5": ("Probabilidades: Montecarlo vs teoría", lambda: experimento_probabilidades()),
        "6": ("Convergencia (Ley de los Grandes Números)", lambda: experimento_convergencia()),
        "0": ("Salir", None),
    }
    while True:
        print("\n========== YAHTZEE · MÉTODO DE MONTECARLO ==========")
        for k, (texto, _) in opciones.items():
            print(f"  {k}. {texto}")
        r = input("Opción: ").strip()
        if r == "0":
            return
        if r in opciones:
            opciones[r][1]()
        else:
            print("Opción no válida.")


def main() -> None:
    p = argparse.ArgumentParser(description="Yahtzee con el método de Montecarlo")
    p.add_argument("modo", nargs="?", default="menu",
                   choices=["menu", "interactivo", "partida", "simulacion",
                            "probabilidades", "convergencia", "sensibilidad", "todo"])
    p.add_argument("-n", type=int, default=None, help="número de repeticiones")
    p.add_argument("--sims", type=int, default=100, help="simulaciones por máscara (IA)")
    p.add_argument("--rival", choices=["humano", "ia"], default="humano")
    p.add_argument("--semilla", type=int, default=None, help="semilla para reproducir resultados")
    a = p.parse_args()
    fijar_semilla(a.semilla)

    if a.modo == "menu":
        menu()
    elif a.modo == "interactivo":
        modo_interactivo(a.rival, a.sims)
    elif a.modo == "partida":
        modo_partida(a.sims)
    elif a.modo == "simulacion":
        experimento_partidas(a.n or 1000, a.sims)
    elif a.modo == "probabilidades":
        experimento_probabilidades(a.n or 200_000)
    elif a.modo == "convergencia":
        experimento_convergencia(a.n or 100_000)
    elif a.modo == "sensibilidad":
        experimento_sensibilidad(a.n or 100)
    elif a.modo == "todo":
        experimento_probabilidades(200_000)
        experimento_convergencia(100_000)
        experimento_partidas(a.n or 1000, a.sims)
        experimento_sensibilidad(100)
        print(f"\n✅ Resultados guardados en: {CARPETA_RESULTADOS}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nPrograma interrumpido por el usuario. ¡Hasta pronto!")
