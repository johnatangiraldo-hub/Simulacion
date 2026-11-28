"""Análisis del modelo de cajeros del parqueadero (Actividad 2-M4, Grupo 15).

Procedimiento (todo reproducible con la semilla de simulacion_parqueadero.py):
  1. Método de Welch (promedio por ventana + media móvil) para ubicar
     el fin del estado transitorio (periodo de calentamiento L).            [CREA C3]
  2. Número de réplicas con la técnica de la media: media acumulada de la espera diaria
     y precisión relativa del intervalo de confianza del 95 %.              [CREA C4]
  3. Corrida final y puntos 1 a 3 del enunciado con los datos SIN transitorio.
  4. Verificación, calibración y validación del modelo.                      [CREA C5]
  5. Eliminación del transitorio: comparación antes / después.               [CREA C6]
  6. Sensibilidad al reparto de lentos y muy lentos.                         [CREA C7]

Uso:  python analisis_parqueadero.py            (≈ 2-4 min)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from scipy import stats

from simulacion_parqueadero import (CAJEROS_ACTUALES, ESCENARIOS, HORIZONTE, MEDIA_LLEGADA,
                                    MEDIA_SERVICIO, PROB_TIPO, SEMILLA, TIPOS, correr_replicas,
                                    escribir_csv, generar_usuarios, medias_teoricas, simular)

RAIZ = Path(__file__).resolve().parent
RES, FIG = RAIZ / "resultados", RAIZ / "figuras"
VENTANA = 10.0          # minutos por ventana para el método de Welch
W_MOVIL = 6             # media móvil de ±6 ventanas (1 hora)
TOLERANCIA_L = 0.10     # banda de ±10 % alrededor del nivel estable
REPLICAS = 100        # réplicas para Welch y para la corrida final
PRECISION_REL = 0.10    # semiancho del IC 95 % ≤ 10 % de la media
CRITERIO = {"espera_media_max": 5.0, "prob_espera_10_max": 0.10, "utilizacion_max": 0.80}
AZUL, NARANJA, GRIS, VERDE, ROJO = "#1F4E79", "#E07B39", "#8C8C8C", "#2E8B57", "#C0392B"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110})


# ---------------------------------------------------------------------------
# Utilidades estadísticas [USA: misma lógica de IC t-Student de la Actividad 3]
# ---------------------------------------------------------------------------
def ic95(x) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    m, n = x.mean(), len(x)
    h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n) if n > 1 else 0.0
    return float(m), float(m - h), float(m + h)


def guardar(fig, nombre: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / nombre, dpi=200, bbox_inches="tight")
    plt.close(fig)


def solapamiento(a, b, lo, hi):
    return np.clip(np.minimum(b, hi) - np.maximum(a, lo), 0, None)


# ---------------------------------------------------------------------------
# 1. Método de Welch
# ---------------------------------------------------------------------------
def matriz_ventanas(registros_rep: list[list[dict]]) -> np.ndarray:
    """Espera media por ventana de llegada (filas = réplicas, columnas = ventanas)."""
    k = int(HORIZONTE // VENTANA)
    Y = np.full((len(registros_rep), k), np.nan)
    for r, regs in enumerate(registros_rep):
        df = pd.DataFrame(regs)
        idx = (df["llegada"] // VENTANA).astype(int).clip(upper=k - 1)
        g = df.groupby(idx)["espera"].mean()
        Y[r, g.index] = g.values
    return Y


def media_movil_welch(y: np.ndarray, w: int) -> np.ndarray:
    """Media móvil de Welch: ventana centrada de 2w+1 que se acorta al inicio."""
    m = len(y)
    out = np.full(m, np.nan)
    for i in range(m - w):
        s = min(i, w)
        out[i] = np.nanmean(y[i - s:i + s + 1])
    return out


def fin_transitorio(mm: np.ndarray) -> tuple[int, float]:
    """Primer índice a partir del cual la media móvil queda dentro de ±10 % del nivel
    estable (promedio de la media móvil en el último 40 % de la jornada)."""
    validos = np.where(~np.isnan(mm))[0]
    cola = validos[int(0.6 * len(validos)):]
    nivel = float(np.nanmean(mm[cola]))
    dentro = np.abs(mm - nivel) <= TOLERANCIA_L * nivel
    for i in validos:
        if dentro[i:validos[-1] + 1].all():
            return int(i), nivel
    return int(validos[-1]), nivel


# ---------------------------------------------------------------------------
# 3. Indicadores por réplica (con o sin transitorio)
# ---------------------------------------------------------------------------
def indicadores(regs: list[dict], L: float, cajeros: int) -> tuple[dict, list[dict]]:
    df = pd.DataFrame(regs)
    d = df[df["llegada"] >= L]
    dur = HORIZONTE - L
    fila = {"usuarios": len(d), "espera_media": d["espera"].mean(),
            "espera_p95": float(np.percentile(d["espera"], 95)),
            "prob_espera_10": float((d["espera"] > 10).mean()),
            "sistema_medio": d["sistema"].mean(), "servicio_medio": d["servicio"].mean()}
    caj = []
    for c in range(1, cajeros + 1):
        x = df[df["cajero"] == f"C{c}"]
        xs = x[x["llegada"] >= L]
        ocupado = solapamiento(x["inicio"].values, x["fin"].values, L, HORIZONTE).sum()
        en_cola = solapamiento(x["llegada"].values, x["inicio"].values, L, HORIZONTE).sum()
        caj.append({"cajero": f"C{c}", "usuarios": len(xs), "servicio_medio": xs["servicio"].mean(),
                    "espera_media": xs["espera"].mean(), "sistema_medio": xs["sistema"].mean(),
                    "utilizacion": ocupado / dur, "Lq": en_cola / dur, "lambda": len(xs) / dur})
    fila["utilizacion"] = float(np.mean([c["utilizacion"] for c in caj]))
    for t in TIPOS:
        dt = d[d["tipo"] == t]
        fila[f"espera_{t}"] = dt["espera"].mean()
        fila[f"sistema_{t}"] = dt["sistema"].mean()
    return fila, caj


def resumir(datos: dict, L: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    filas, cajs = [], []
    for e, reps in datos.items():
        c = ESCENARIOS[e][0]
        for r, regs in enumerate(reps, 1):
            f, cj = indicadores(regs, L, c)
            filas.append({"escenario": e, "replica": r, **f})
            cajs += [{"escenario": e, "replica": r, **x} for x in cj]
    return pd.DataFrame(filas), pd.DataFrame(cajs)


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    RES.mkdir(exist_ok=True)
    teo = medias_teoricas()
    salida = {"teoria": teo, "criterio": CRITERIO}

    # ---- Paso 1: método de Welch sobre REPLICAS réplicas ---------------------------
    datos = correr_replicas(REPLICAS)
    A = datos["A_3_actual"]
    Y = matriz_ventanas(A)
    ens = np.nanmean(Y, 0)
    mm = media_movil_welch(ens, W_MOVIL)
    i_L, nivel = fin_transitorio(mm)
    L = (i_L + 1) * VENTANA  # se descarta hasta el final de la ventana i_L
    salida["welch"] = {"replicas": REPLICAS, "ventana_min": VENTANA, "media_movil_ventanas": W_MOVIL,
                       "tolerancia": TOLERANCIA_L, "indice_ventana": i_L, "L_min": L, "nivel_estable": nivel}
    t_ventana = (np.arange(len(ens)) + 0.5) * VENTANA
    pd.DataFrame({"minuto": t_ventana, "espera_promedio": ens, "media_movil": mm}).to_csv(
        RES / "welch.csv", index=False)

    # ---- Paso 2: número de réplicas (técnica de la media) ---------------------
    diarias = np.array([indicadores(regs, L, 3)[0]["espera_media"] for regs in A])
    m10, s10 = diarias[:10].mean(), diarias[:10].std(ddof=1)  # piloto: primeras 10 réplicas
    n_req = math.ceil((stats.t.ppf(0.975, 9) * s10 / (PRECISION_REL * m10)) ** 2)
    if n_req > REPLICAS:  # si el piloto exige más réplicas, se amplía la corrida
        datos = correr_replicas(n_req)
        A = datos["A_3_actual"]
    n_final = max(REPLICAS, n_req)
    semi_final = stats.t.ppf(0.975, n_final - 1) * diarias.std(ddof=1) / math.sqrt(n_final)
    salida["replicas"] = {"piloto": 10, "media_piloto": m10, "desv_piloto": s10, "n_requeridas": n_req,
                          "n_final": n_final, "precision_relativa_objetivo": PRECISION_REL,
                          "precision_relativa_lograda": semi_final / diarias.mean()}

    # Media acumulada de la espera diaria (sin transitorio) vs réplicas
    res, caj = resumir(datos, L)
    res_con, caj_con = resumir({"A_3_actual": A}, 0.0)
    resA = res[res.escenario == "A_3_actual"].reset_index(drop=True)
    acum = resA["espera_media"].expanding().mean()
    semi = [np.nan] + [stats.t.ppf(.975, k - 1) * resA["espera_media"][:k].std(ddof=1) / math.sqrt(k)
                       for k in range(2, len(resA) + 1)]
    pd.DataFrame({"replica": resA["replica"], "espera_dia": resA["espera_media"],
                  "media_acumulada": acum, "semiancho_ic95": semi}).to_csv(RES / "replicas.csv", index=False)
    res.to_csv(RES / "escenarios_por_replica.csv", index=False)
    caj.to_csv(RES / "cajeros_por_replica.csv", index=False)

    # ---- Punto 1: cajeros -------------------------------------------------------
    cA = caj[caj.escenario == "A_3_actual"]
    p1 = []
    for c, g in cA.groupby("cajero"):
        ms, lo, hi = ic95(g["servicio_medio"])
        p1.append({"cajero": c, "usuarios_dia": g["usuarios"].mean(), "servicio_medio": ms,
                   "ic_inf": lo, "ic_sup": hi, "desv": g["servicio_medio"].std(ddof=1),
                   "min": g["servicio_medio"].min(), "max": g["servicio_medio"].max(),
                   "espera_media": g["espera_media"].mean(), "sistema_medio": g["sistema_medio"].mean(),
                   "utilizacion": g["utilizacion"].mean()})
    p1 = pd.DataFrame(p1)
    grupos = [g["servicio_medio"].values for _, g in cA.groupby("cajero")]
    anova = stats.f_oneway(*grupos)
    kw = stats.kruskal(*grupos)
    c_min = p1.loc[p1.servicio_medio.idxmin(), "cajero"]
    c_max = p1.loc[p1.servicio_medio.idxmax(), "cajero"]
    dif = (cA[cA.cajero == c_max]["servicio_medio"].values - cA[cA.cajero == c_min]["servicio_medio"].values)
    salida["punto1"] = {"tabla": p1.to_dict("records"), "cajero_min": c_min, "cajero_max": c_max,
                        "anova_F": float(anova.statistic), "anova_p": float(anova.pvalue),
                        "kruskal_H": float(kw.statistic), "kruskal_p": float(kw.pvalue),
                        "dif_max_min": ic95(dif)}
    p1.to_csv(RES / "punto1_cajeros.csv", index=False)

    # ---- Punto 2: usuarios por tipo (jornada completa, 3 cajeros) ----------------
    filas = []
    for r, regs in enumerate(A, 1):
        df = pd.DataFrame(regs)
        fila = {"replica": r, "total": len(df)}
        for t in TIPOS:
            fila[t] = int((df["tipo"] == t).sum())
            for c in range(1, 4):
                fila[f"{t}_C{c}"] = int(((df["tipo"] == t) & (df["cajero"] == f"C{c}")).sum())
        filas.append(fila)
    tipos = pd.DataFrame(filas)
    tipos.to_csv(RES / "usuarios_tipo_por_replica.csv", index=False)
    esperado_total = 3 * HORIZONTE / teo["E_entrellegada"]
    p2 = []
    for t, p in zip(TIPOS, PROB_TIPO):
        m, lo, hi = ic95(tipos[t])
        p2.append({"tipo": t, "promedio": m, "ic_inf": lo, "ic_sup": hi, "desv": tipos[t].std(ddof=1),
                   "min": int(tipos[t].min()), "max": int(tipos[t].max()),
                   "C1": tipos[f"{t}_C1"].mean(), "C2": tipos[f"{t}_C2"].mean(), "C3": tipos[f"{t}_C3"].mean(),
                   "porcentaje": m / tipos["total"].mean(), "esperado_teorico": esperado_total * p})
    m, lo, hi = ic95(tipos["total"])
    p2.append({"tipo": "Total", "promedio": m, "ic_inf": lo, "ic_sup": hi, "desv": tipos["total"].std(ddof=1),
               "min": int(tipos["total"].min()), "max": int(tipos["total"].max()),
               "C1": sum(tipos[f"{t}_C1"].mean() for t in TIPOS), "C2": sum(tipos[f"{t}_C2"].mean() for t in TIPOS),
               "C3": sum(tipos[f"{t}_C3"].mean() for t in TIPOS), "porcentaje": 1.0, "esperado_teorico": esperado_total})
    p2 = pd.DataFrame(p2)
    p2.to_csv(RES / "punto2_usuarios_tipo.csv", index=False)
    salida["punto2"] = p2.to_dict("records")

    # ---- Punto 3: estrategias y criterio ----------------------------------------
    p3 = []
    base = res[res.escenario == "A_3_actual"].set_index("replica")["espera_media"]
    for e, g in res.groupby("escenario", sort=False):
        m, lo, hi = ic95(g["espera_media"])
        dif = ic95(base.values - g.set_index("replica")["espera_media"].reindex(base.index).values)
        fila = {"escenario": e, "cajeros": ESCENARIOS[e][0], "regla": ESCENARIOS[e][1],
                "espera_media": m, "ic_inf": lo, "ic_sup": hi, "espera_p95": g["espera_p95"].mean(),
                "prob_espera_10": g["prob_espera_10"].mean(), "sistema_medio": g["sistema_medio"].mean(),
                "utilizacion": g["utilizacion"].mean(), "ahorro_vs_actual": dif[0],
                "ahorro_ic_inf": dif[1], "ahorro_ic_sup": dif[2],
                **{f"sistema_{t}": g[f"sistema_{t}"].mean() for t in TIPOS}}
        fila["cumple"] = bool(fila["espera_media"] <= CRITERIO["espera_media_max"]
                              and fila["prob_espera_10"] <= CRITERIO["prob_espera_10_max"]
                              and fila["utilizacion"] <= CRITERIO["utilizacion_max"])
        p3.append(fila)
    p3 = pd.DataFrame(p3)
    p3.to_csv(RES / "punto3_estrategias.csv", index=False)
    cumplen = p3[p3.cumple].sort_values(["cajeros", "espera_media"])
    salida["punto3"] = {"tabla": p3.to_dict("records"),
                        "recomendada": cumplen.iloc[0]["escenario"] if len(cumplen) else None}

    # ---- Punto 4: verificación, calibración y validación ------------------------
    vv = verificacion_validacion(n_final, L, teo, resA, cA)
    salida["punto4"] = vv

    # ---- Punto 5: antes / después del transitorio -------------------------------
    con = res_con.reset_index(drop=True)
    p5 = []
    for col, nom in (("espera_media", "Espera media (min)"), ("espera_p95", "Percentil 95 de espera (min)"),
                     ("prob_espera_10", "Proporción que espera > 10 min"), ("utilizacion", "Utilización"),
                     ("sistema_medio", "Tiempo en el sistema (min)")):
        a, d = ic95(con[col]), ic95(resA[col])
        p5.append({"indicador": nom, "antes": a[0], "antes_ic": [a[1], a[2]],
                   "despues": d[0], "despues_ic": [d[1], d[2]], "cambio_pct": (d[0] - a[0]) / a[0] * 100})
    salida["punto5"] = p5
    pd.DataFrame(p5).to_csv(RES / "punto5_antes_despues.csv", index=False)
    cajeros_ad = (caj_con.groupby("cajero")["espera_media"].mean().rename("antes").to_frame()
                  .join(cA.groupby("cajero")["espera_media"].mean().rename("despues")))

    # ---- Sensibilidad (CREA C7) --------------------------------------------------
    sens = []
    for nombre, prob in (("27,5 % / 27,5 % (base)", PROB_TIPO), ("35 % / 20 %", (0.25, 0.20, 0.35, 0.20)),
                         ("20 % / 35 %", (0.25, 0.20, 0.20, 0.35))):
        rec = salida["punto3"]["recomendada"]
        esc = {"A_3_actual": ESCENARIOS["A_3_actual"], rec: ESCENARIOS[rec]}
        d = correr_replicas(30, semilla=SEMILLA + 7, escenarios=esc, prob=prob)
        r_s, _ = resumir(d, L)
        fila = {"reparto_lento_muylento": nombre, "rho_teorico": medias_teoricas(prob)["rho"]}
        for e in esc:
            fila[f"espera_{e}"] = r_s[r_s.escenario == e]["espera_media"].mean()
        sens.append(fila)
    salida["sensibilidad"] = sens
    pd.DataFrame(sens).to_csv(RES / "sensibilidad_reparto.csv", index=False)

    # ---- Figuras -----------------------------------------------------------------
    figuras(t_ventana, ens, mm, L, nivel, None, resA, n_req, n_final, p1, cA, p2, p3, vv, con, cajeros_ad)
    (RES / "estadisticos.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2, default=float),
                                           encoding="utf-8")
    excel(p1, p2, p3, p5, sens, salida)
    # Trazabilidad: primeros usuarios de la réplica 1 en la situación actual
    escribir_csv(RES / "traza_replica1_situacion_actual.csv", A[0][:60])
    print(json.dumps({"L_min": L, "n_requeridas": n_req, "n_final": n_final,
                      "recomendada": salida["punto3"]["recomendada"]}, ensure_ascii=False))
    return salida


CORRIDA_LARGA = {"replicas": 30, "horizonte_min": 12000.0, "descarte_min": 1440.0}


def corrida_larga(modo: str) -> dict:
    """[CREA C5] Régimen permanente largo (200 h por réplica, se descartan las primeras 24 h)."""
    R, H, D = CORRIDA_LARGA["replicas"], CORRIDA_LARGA["horizonte_min"], CORRIDA_LARGA["descarte_min"]
    wq, w, lq, ocup = [], [], [], []
    for r in range(1, R + 1):
        regs = pd.DataFrame(simular(generar_usuarios(SEMILLA + 500, r, horizonte=H, modo=modo), 3, "propio"))
        d = regs[regs["llegada"] >= D]
        wq.append(d["espera"].mean())
        w.append(d["sistema"].mean())
        lq.append(solapamiento(regs["llegada"].values, regs["inicio"].values, D, H).sum() / (H - D) / 3)
        ocup.append(solapamiento(regs["inicio"].values, regs["fin"].values, D, H).sum() / (H - D) / 3)
    return {"Wq": float(np.mean(wq)), "W": float(np.mean(w)), "Lq": float(np.mean(lq)),
            "rho": float(np.mean(ocup)), "Wq_ic": ic95(wq)}


def verificacion_validacion(n, L, teo, resA, cA) -> dict:
    out = {}
    # Verificación: motor con M/M/1 puro frente a fórmulas exactas. Se usan corridas LARGAS
    # (régimen permanente de una cola con ρ ≈ 0,77) para que la comparación sea justa.
    lam, mu = teo["lambda"], 1 / teo["E_servicio"]
    rho = lam / mu
    exacto = {"rho": rho, "Wq": lam / (mu * (mu - lam)), "W": 1 / (mu - lam), "Lq": rho**2 / (1 - rho)}
    sim = corrida_larga("mm1")
    out["verificacion_mm1"] = {k: {"teorico": exacto[k], "simulado": sim[k],
                                   "error_pct": (sim[k] - exacto[k]) / exacto[k] * 100} for k in exacto}
    out["verificacion_mm1"]["_diseno"] = dict(CORRIDA_LARGA)
    # Calibración: entradas generadas frente a la tabla del enunciado
    filas, inter = [], {t: [] for t in TIPOS}
    for r in range(1, n + 1):
        us = generar_usuarios(SEMILLA, r)
        filas += [(u.tipo, u.servicio) for u in us]
        for f in range(CAJEROS_ACTUALES):
            t_prev = 0.0
            for u in (x for x in us if x.flujo == f):
                inter[u.tipo].append(u.llegada - t_prev)
                t_prev = u.llegada
    df = pd.DataFrame(filas, columns=["tipo", "servicio"])
    conteo = df["tipo"].value_counts().reindex(TIPOS).values
    chi = stats.chisquare(conteo, np.array(PROB_TIPO) * conteo.sum())
    cal = []
    for t, p, ms, ma in zip(TIPOS, PROB_TIPO, MEDIA_SERVICIO, MEDIA_LLEGADA):
        s = df[df.tipo == t]["servicio"].values
        ks = stats.kstest(s, "expon", args=(0, ms))
        cal.append({"tipo": t, "prop_teorica": p, "prop_simulada": float((df.tipo == t).mean()),
                    "servicio_teorico": ms, "servicio_simulado": float(s.mean()), "ks_p": float(ks.pvalue),
                    "llegada_teorica": ma, "llegada_simulada": float(np.mean(inter[t]))})
    out["calibracion"] = {"tabla": cal, "chi2": float(chi.statistic), "chi2_p": float(chi.pvalue)}
    # Validación: modelo completo frente a aproximaciones analíticas y ley de Little
    wq_sim = ic95(resA["espera_media"])
    out["validacion"] = {
        "Wq_simulado": wq_sim,
        "Wq_MM1": lam / (mu * (mu - lam)),
        "Wq_PK_MG1": lam * teo["E_servicio2"] / (2 * (1 - teo["rho"])),
        "Wq_Kingman_GG1": teo["rho"] / (1 - teo["rho"]) * (teo["ca2"] + teo["cs2"]) / 2 * teo["E_servicio"],
        "rho_teorico": teo["rho"], "rho_simulado": float(cA["utilizacion"].mean()),
        "Little_Lq": float(cA["Lq"].mean()),
        "Little_lambdaWq": float((cA["lambda"] * cA["espera_media"]).mean()),
        "Wq_corrida_larga": corrida_larga("condicional")["Wq"],
    }
    out["validacion"]["Little_error_pct"] = (out["validacion"]["Little_Lq"] / out["validacion"]["Little_lambdaWq"] - 1) * 100
    return out


def figuras(t, ens, mm, L, nivel, Yp, resA, n_req, n_final, p1, cA, p2, p3, vv, con, cajeros_ad):
    # Fig 1: Welch
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(t, ens, color=GRIS, lw=0.9, alpha=0.8, label=f"Promedio de {len(resA)} réplicas por ventana de 10 min")
    ax.plot(t, mm, color=AZUL, lw=2.2, label="Media móvil de Welch (±1 h)")
    ax.axhspan(nivel * (1 - TOLERANCIA_L), nivel * (1 + TOLERANCIA_L), color=VERDE, alpha=0.12,
               label=f"Banda ±10 % del nivel estable ({nivel:.1f} min)")
    ax.axvline(L, color=ROJO, ls="--", lw=1.6)
    ax.text(L + 6, ax.get_ylim()[1] * 0.55, f"Fin del transitorio\nL = {L:.0f} min",
            color=ROJO, fontsize=9, fontweight="bold")
    ax.axvspan(0, L, color=ROJO, alpha=0.06)
    ax.set_xlabel("Minuto de la jornada (llegada del usuario)")
    ax.set_ylabel("Espera en fila (min)")
    ax.set_title("Estado estable con el método de Welch (situación actual, 3 cajeros)", fontweight="bold")
    ax.legend(loc="lower right", fontsize=8)
    guardar(fig, "fig1_welch_estado_estable.png")

    # Fig 2: técnica de la media para el número de réplicas
    fig, ax = plt.subplots(figsize=(9, 4))
    k = np.arange(1, len(resA) + 1)
    acum = resA["espera_media"].expanding().mean().values
    semi = np.array([np.nan] + [stats.t.ppf(.975, i - 1) * resA["espera_media"][:i].std(ddof=1) / math.sqrt(i)
                                for i in range(2, len(resA) + 1)])
    ax.scatter(k, resA["espera_media"], s=10, color=GRIS, alpha=0.6, label="Espera media de cada réplica")
    ax.plot(k, acum, color=AZUL, lw=2, label="Media acumulada")
    ax.fill_between(k, acum - semi, acum + semi, color=AZUL, alpha=0.15, label="IC 95 %")
    ax.axhline(acum[-1], color=AZUL, ls=":", lw=1)
    ax.axvline(10, color=NARANJA, ls="--", lw=1.4, label="Piloto (10 réplicas)")
    ax.axvline(n_req, color=ROJO, ls="--", lw=1.4, label=f"Réplicas requeridas = {n_req}")
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Número de réplicas (días simulados)")
    ax.set_ylabel("Espera en fila sin transitorio (min)")
    ax.set_title("Técnica de la media: estabilización de la espera promedio", fontweight="bold")
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    guardar(fig, "fig2_replicas_tecnica_media.png")

    # Fig 3: punto 1
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    cols = [VERDE if c == p1.loc[p1.servicio_medio.idxmin(), "cajero"] else
            ROJO if c == p1.loc[p1.servicio_medio.idxmax(), "cajero"] else GRIS for c in p1.cajero]
    axs[0].bar(p1.cajero, p1.servicio_medio, color=cols,
               yerr=[p1.servicio_medio - p1.ic_inf, p1.ic_sup - p1.servicio_medio], capsize=6)
    for i, v in enumerate(p1.servicio_medio):
        axs[0].text(i, v + 0.15, f"{v:.2f}", ha="center", fontweight="bold")
    axs[0].axhline(medias_teoricas()["E_servicio"], color=AZUL, ls="--", lw=1, label="Teórico 3,60 min")
    axs[0].set_ylabel("Tiempo promedio de atención (min)")
    axs[0].set_title("Atención por cajero (verde = menor, rojo = mayor)", fontweight="bold")
    axs[0].legend(fontsize=8)
    data = [g["servicio_medio"].values for _, g in cA.groupby("cajero")]
    axs[1].boxplot(data, tick_labels=list(p1.cajero))
    axs[1].set_ylabel("Atención media diaria (min)")
    axs[1].set_title("Variación entre réplicas", fontweight="bold")
    guardar(fig, "fig3_punto1_cajeros.png")

    # Fig 4: punto 2
    q = p2[p2.tipo != "Total"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(q))
    axs[0].bar(x - 0.2, q.promedio, 0.4, color=AZUL, yerr=[q.promedio - q.ic_inf, q.ic_sup - q.promedio],
               capsize=4, label="Simulado (IC 95 %)")
    axs[0].bar(x + 0.2, q.esperado_teorico, 0.4, color=NARANJA, label="Esperado teórico")
    for i, v in enumerate(q.promedio):
        axs[0].text(i - 0.2, v + 3, f"{v:.1f}", ha="center", fontsize=8)
    axs[0].set_xticks(x, q.tipo)
    axs[0].set_ylabel("Usuarios por día (3 cajeros)")
    axs[0].set_title("Promedio de usuarios por tipo", fontweight="bold")
    axs[0].legend(fontsize=8)
    bottom = np.zeros(3)
    for tipo, col in zip(TIPOS, [VERDE, AZUL, NARANJA, ROJO]):
        v = q[q.tipo == tipo][["C1", "C2", "C3"]].values[0]
        axs[1].bar(["C1", "C2", "C3"], v, bottom=bottom, color=col, label=tipo)
        bottom += v
    axs[1].set_ylabel("Usuarios por día")
    axs[1].set_title("Composición por cajero", fontweight="bold")
    axs[1].legend(fontsize=8, ncol=2)
    guardar(fig, "fig4_punto2_usuarios_tipo.png")

    # Fig 5: punto 3
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
    etiquetas = ["3 actual", "4 cajeros", "5 cajeros", "3 + fila\nmás corta", "4 + fila\nmás corta", "3 fila\núnica"]
    cols = [VERDE if c else ROJO for c in p3.cumple]
    axs[0].bar(etiquetas, p3.espera_media, color=cols,
               yerr=[p3.espera_media - p3.ic_inf, p3.ic_sup - p3.espera_media], capsize=4)
    axs[0].axhline(CRITERIO["espera_media_max"], color="k", ls="--", lw=1.2, label="Criterio: ≤ 5 min")
    for i, v in enumerate(p3.espera_media):
        axs[0].text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=9, fontweight="bold")
    axs[0].set_ylabel("Espera media en fila (min)")
    axs[0].set_title("Espera media por estrategia (verde = cumple)", fontweight="bold")
    axs[0].legend(fontsize=8)
    axs[0].tick_params(axis="x", labelsize=8)
    axs[1].bar(etiquetas, p3.prob_espera_10 * 100, color=cols)
    axs[1].axhline(CRITERIO["prob_espera_10_max"] * 100, color="k", ls="--", lw=1.2, label="Criterio: ≤ 10 %")
    ax2 = axs[1].twinx()
    ax2.plot(etiquetas, p3.utilizacion * 100, "o-", color=AZUL, label="Utilización")
    ax2.axhline(CRITERIO["utilizacion_max"] * 100, color=AZUL, ls=":", lw=1)
    ax2.set_ylabel("Utilización (%)", color=AZUL)
    ax2.set_ylim(0, 100)
    axs[1].set_ylabel("Usuarios que esperan > 10 min (%)")
    axs[1].set_title("Esperas largas y utilización", fontweight="bold")
    axs[1].tick_params(axis="x", labelsize=8)
    h1, l1 = axs[1].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axs[1].legend(h1 + h2, l1 + l2 + [], fontsize=8, loc="upper right")
    guardar(fig, "fig5_punto3_estrategias.png")

    # Fig 6: diagrama del proceso de verificación, calibración y validación
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axis("off")
    cajas = [("Modelo conceptual", "Enunciado + supuestos\n3 cajeros, filas\nindependientes", GRIS),
             ("1. Verificación", "¿El código hace lo\nque dice el modelo?\nPruebas + M/M/1 exacto", AZUL),
             ("2. Calibración", "¿Las entradas generadas\ncoinciden con la tabla?\nχ², KS, medias", NARANJA),
             ("3. Validación", "¿Las salidas son creíbles?\nTeoría de colas\n+ ley de Little", VERDE),
             ("Experimentación", "Estado estable, réplicas\ny estrategias", "#6A5ACD")]
    for i, (tit, txt, col) in enumerate(cajas):
        x0 = 0.01 + i * 0.2
        ax.add_patch(FancyBboxPatch((x0, 0.25), 0.17, 0.5, boxstyle="round,pad=0.01", fc=col, ec="none", alpha=0.9,
                                    transform=ax.transAxes))
        ax.text(x0 + 0.085, 0.64, tit, ha="center", va="center", color="white", fontweight="bold", fontsize=10,
                transform=ax.transAxes)
        ax.text(x0 + 0.085, 0.42, txt, ha="center", va="center", color="white", fontsize=8, transform=ax.transAxes)
        if i < 4:
            ax.annotate("", xy=(x0 + 0.2, 0.5), xytext=(x0 + 0.175, 0.5), xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5))
    ax.annotate("", xy=(0.295, 0.2), xytext=(0.695, 0.2), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=ROJO, lw=1.3, connectionstyle="arc3,rad=0.25"))
    ax.text(0.495, 0.03, "Si alguna prueba falla: se corrige el código o los parámetros y se repite",
            ha="center", color=ROJO, fontsize=9, transform=ax.transAxes)
    ax.set_title("Proceso de verificación, calibración y validación del modelo", fontweight="bold")
    guardar(fig, "fig6_proceso_vv.png")

    # Fig 7: resultados de verificación, calibración y validación
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    v = vv["verificacion_mm1"]
    k = ["Wq", "W", "Lq", "rho"]  # se ignora la clave _diseno
    nombres = ["Wq (min)", "W (min)", "Lq", "ρ"]
    axs[0].bar(np.arange(4) - 0.2, [v[i]["teorico"] for i in k], 0.4, color=GRIS, label="Fórmula exacta")
    axs[0].bar(np.arange(4) + 0.2, [v[i]["simulado"] for i in k], 0.4, color=AZUL, label="Simulación")
    for j, i in enumerate(k):
        axs[0].text(j + 0.2, v[i]["simulado"] + 0.3, f"{v[i]['error_pct']:+.1f} %", ha="center", fontsize=8)
    axs[0].set_xticks(range(4), nombres)
    axs[0].set_title("Verificación: M/M/1 puro", fontweight="bold")
    axs[0].legend(fontsize=8)
    c = vv["calibracion"]["tabla"]
    x = np.arange(4)
    axs[1].bar(x - 0.2, [i["servicio_teorico"] for i in c], 0.4, color=GRIS, label="Tabla del enunciado")
    axs[1].bar(x + 0.2, [i["servicio_simulado"] for i in c], 0.4, color=NARANJA, label="Generado")
    axs[1].plot(x, [i["llegada_teorica"] for i in c], "s", color="k", label="Llegada (tabla)")
    axs[1].plot(x, [i["llegada_simulada"] for i in c], "x", color=ROJO, ms=9, label="Llegada (generada)")
    axs[1].set_xticks(x, TIPOS)
    axs[1].set_ylabel("Minutos")
    axs[1].set_title("Calibración: medias por tipo", fontweight="bold")
    axs[1].legend(fontsize=7)
    val = vv["validacion"]
    nom = ["M/M/1\n(medias)", "M/G/1\n(P-K)", "G/G/1\n(Kingman)", "Sim.\njornada", "Sim.\n200 h"]
    vals = [val["Wq_MM1"], val["Wq_PK_MG1"], val["Wq_Kingman_GG1"], val["Wq_simulado"][0], val["Wq_corrida_larga"]]
    axs[2].bar(nom, vals, color=[GRIS, GRIS, GRIS, VERDE, VERDE])
    axs[2].tick_params(axis="x", labelsize=8)
    axs[2].errorbar(3, vals[3], yerr=[[vals[3] - val["Wq_simulado"][1]], [val["Wq_simulado"][2] - vals[3]]],
                    color="k", capsize=6)
    for i, y in enumerate(vals):
        extra = (val["Wq_simulado"][2] - y + 0.3) if i == 3 else 0.4
        axs[2].text(i, y + extra, f"{y:.1f}", ha="center", fontweight="bold")
    axs[2].set_ylabel("Espera media en fila (min)")
    axs[2].set_title("Validación: teoría de colas", fontweight="bold")
    guardar(fig, "fig7_resultados_vv.png")

    # Fig 8: antes y después de eliminar el transitorio
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.3, 1.3, 1]})
    antes = con["espera_media"].mean()
    despues = resA["espera_media"].mean()
    axs[0].plot(t, ens, color=GRIS, lw=1)
    axs[0].plot(t, mm, color=AZUL, lw=2)
    axs[0].axhline(antes, color=NARANJA, lw=2, label=f"Promedio con transitorio = {antes:.2f} min")
    axs[0].axvspan(0, L, color=ROJO, alpha=0.08, label="Transitorio")
    axs[0].set_title("ANTES: jornada completa", fontweight="bold")
    axs[0].set_xlabel("Minuto de la jornada")
    axs[0].set_ylabel("Espera en fila (min)")
    axs[0].legend(fontsize=8, loc="lower right")
    msk = t >= L
    axs[1].plot(t[msk], ens[msk], color=GRIS, lw=1)
    axs[1].plot(t[msk], mm[msk], color=AZUL, lw=2)
    axs[1].axhline(despues, color=VERDE, lw=2, label=f"Promedio sin transitorio = {despues:.2f} min")
    axs[1].set_xlim(0, HORIZONTE)
    axs[1].set_ylim(axs[0].get_ylim())
    axs[1].set_title(f"DESPUÉS: se eliminan los primeros {L:.0f} min", fontweight="bold")
    axs[1].set_xlabel("Minuto de la jornada")
    axs[1].legend(fontsize=8, loc="lower right")
    xx = np.arange(len(cajeros_ad))
    axs[2].bar(xx - 0.2, cajeros_ad["antes"], 0.4, color=NARANJA, label="Antes")
    axs[2].bar(xx + 0.2, cajeros_ad["despues"], 0.4, color=VERDE, label="Después")
    axs[2].set_xticks(xx, cajeros_ad.index)
    axs[2].set_ylabel("Espera media en fila (min)")
    axs[2].set_title("Promedio por cajero", fontweight="bold")
    axs[2].legend(fontsize=8)
    guardar(fig, "fig8_antes_despues_transitorio.png")


def excel(p1, p2, p3, p5, sens, salida):
    with pd.ExcelWriter(RES / "Resultados_parqueadero.xlsx") as w:
        pd.DataFrame([{"Parámetro": k, "Valor": v} for k, v in {
            "Periodo de calentamiento L (min)": salida["welch"]["L_min"],
            "Réplicas requeridas": salida["replicas"]["n_requeridas"],
            "Réplicas de la corrida final": salida["replicas"]["n_final"],
            "Estrategia recomendada": salida["punto3"]["recomendada"]}.items()]).to_excel(w, sheet_name="Resumen", index=False)
        p1.to_excel(w, sheet_name="Punto1_cajeros", index=False)
        p2.to_excel(w, sheet_name="Punto2_usuarios_tipo", index=False)
        p3.to_excel(w, sheet_name="Punto3_estrategias", index=False)
        pd.DataFrame(salida["punto4"]["calibracion"]["tabla"]).to_excel(w, sheet_name="Punto4_calibracion", index=False)
        pd.DataFrame([{"indicador": k, **v} for k, v in salida["punto4"]["verificacion_mm1"].items() if k != "_diseno"]).to_excel(
            w, sheet_name="Punto4_verificacion", index=False)
        pd.DataFrame(p5).to_excel(w, sheet_name="Punto5_antes_despues", index=False)
        pd.DataFrame(sens).to_excel(w, sheet_name="Sensibilidad", index=False)


if __name__ == "__main__":
    main()
