"""
modelo_f1.py - Especificación formal del HMM "clima -> neutralización" en F1.

Estados ocultos  S = {S0: Seco estable, S1: Riesgo (lluvia/incidentes), S2: Neutralización (SC/VSC/bandera roja)}
Observaciones    V = (lluvia, amarilla): lluvia in {0: ninguna, 1: intermitente, 2: continua} x amarilla in {0,1}
                 índice k = 2*lluvia + amarilla  (M = 6 símbolos)
Unidad de tiempo: una vuelta de carrera.
"""
import numpy as np
from hmm import HMM

ESTADOS = ["S0 Seco estable", "S1 Riesgo", "S2 Neutralizacion"]
SIMBOLOS = ["sin lluvia/sin amarilla", "sin lluvia/amarilla",
            "lluvia interm./sin amarilla", "lluvia interm./amarilla",
            "lluvia cont./sin amarilla", "lluvia cont./amarilla"]
SIMBOLOS_SOLO_AMARILLA = ["sin amarilla", "amarilla"]

# Parámetros de ARRANQUE del EM (supuestos del equipo, NO estimaciones): ver artículo, sección 4.
A0 = np.array([[0.97, 0.025, 0.005],
               [0.10, 0.85, 0.05],
               [0.05, 0.15, 0.80]])
B0 = np.array([[0.90, 0.08, 0.010, 0.005, 0.004, 0.001],
               [0.45, 0.25, 0.100, 0.050, 0.100, 0.050],
               [0.40, 0.35, 0.050, 0.050, 0.100, 0.050]])
PI0 = np.array([0.85, 0.14, 0.01])

B0_SOLO_AMARILLA = np.array([[0.92, 0.08], [0.65, 0.35], [0.50, 0.50]])


# Variante EXPLORATORIA (decidida DESPUES de ver los resultados del modelo completo): lluvia binaria (0 / >0)
SIMBOLOS_LLUVIA_BINARIA = ["sin lluvia/sin amarilla", "sin lluvia/amarilla", "lluvia/sin amarilla", "lluvia/amarilla"]
B0_LLUVIA_BINARIA = np.column_stack([B0[:, 0], B0[:, 1], B0[:, 2] + B0[:, 4], B0[:, 3] + B0[:, 5]])


def hmm_inicial(modo="completo"):
    """modo: 'completo' (6 símbolos) | 'solo_amarilla' (2) | 'lluvia_binaria' (4, exploratorio)."""
    if modo is True: modo = "completo"
    if modo is False: modo = "solo_amarilla"
    if modo == "completo":
        return HMM(A0, B0, PI0, ESTADOS, SIMBOLOS)
    if modo == "solo_amarilla":
        return HMM(A0, B0_SOLO_AMARILLA, PI0, ESTADOS, SIMBOLOS_SOLO_AMARILLA)
    return HMM(A0, B0_LLUVIA_BINARIA, PI0, ESTADOS, SIMBOLOS_LLUVIA_BINARIA)


def transformar_obs(obs, modo):
    obs = np.asarray(obs)
    if modo == "completo": return obs
    if modo == "solo_amarilla": return obs % 2
    return (obs // 2 > 0).astype(int) * 2 + obs % 2


def simbolo(lluvia, amarilla):
    return 2 * lluvia + amarilla


def a_solo_amarilla(obs):
    return np.asarray(obs) % 2
