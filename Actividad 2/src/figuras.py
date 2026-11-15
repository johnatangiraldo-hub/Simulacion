"""figuras.py - Genera las figuras del artículo (300 dpi) a partir de resultados/*.csv|json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
from hmm import HMM
from modelo_f1 import ESTADOS, SIMBOLOS
import validacion_real as vr

RAIZ = Path(__file__).resolve().parent.parent
RES, FIG = RAIZ / "resultados", RAIZ / "figuras"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100,
                     "axes.titleweight": "bold", "axes.titlesize": 10})
COL = {"E1_nominal": "#1f4e79", "E2_lluviosa": "#2a9d8f", "E3_ruidoso": "#c1666b"}
ETQ = {"E1_nominal": "E1 nominal", "E2_lluviosa": "E2 lluviosa", "E3_ruidoso": "E3 ruidoso"}


def ic(x):
    x = np.asarray(x); n = len(x); h = stats.t.ppf(.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean(), h


def fig_escenarios():
    df = pd.read_csv(RES / "resultados_crudos_escenarios.csv")
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.9))
    for a, (m, t) in zip(ax, [("acc_viterbi", "Exactitud de Viterbi"), ("f1_neutral", "F1 de neutralización (S2)"), ("err_A", "Error de A tras Baum-Welch")]):
        datos = [df[df.escenario == e][m].values for e in COL]
        bp = a.boxplot(datos, tick_labels=[ETQ[e].replace(" ", "\n") for e in COL], patch_artist=True, widths=.55,
                       medianprops=dict(color="black"), flierprops=dict(markersize=2))
        for p, e in zip(bp["boxes"], COL): p.set_facecolor(COL[e]); p.set_alpha(.75)
        for i, d in enumerate(datos, 1):
            mu, h = ic(d); a.errorbar(i, mu, yerr=h, fmt="D", color="white", mec="black", ecolor="black", ms=4, capsize=3, zorder=5)
        a.set_title(t)
    fig.tight_layout(); fig.savefig(FIG / "fig1_escenarios.png", dpi=300, bbox_inches="tight"); plt.close(fig)


def fig_sensibilidad():
    s = pd.read_csv(RES / "sensibilidad_desajuste.csv")
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for p, c, nm in [("A", "#1f4e79", "A (transición)"), ("B", "#c1666b", "B (emisión)"), ("pi", "#2a9d8f", "π (inicial)")]:
        g = s[s.parametro == p].groupby("eps").acc_viterbi
        mu = g.mean(); h = g.apply(lambda x: ic(x)[1])
        ax.plot(mu.index, mu.values, "-o", color=c, ms=3, label=nm); ax.fill_between(mu.index, mu - h, mu + h, color=c, alpha=.2)
    ax.set_xlabel("ε: mezcla uniforme en los parámetros del decodificador"); ax.set_ylabel("Exactitud de Viterbi")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "fig2_sensibilidad.png", dpi=300); plt.close(fig)


def fig_matrices():
    d = json.load(open(RES / "parametros_estimados.json"))
    A, B = np.array(d["A"]), np.array(d["B"])
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw={"width_ratios": [1, 1.7]})
    for a, M, t, cols in [(ax[0], A, "A (transición)", ["S0", "S1", "S2"]), (ax[1], B, "B (emisión)", ["ll0\nA0", "ll0\nA1", "ll1\nA0", "ll1\nA1", "ll2\nA0", "ll2\nA1"])]:
        im = a.imshow(M, cmap="Blues", vmin=0, vmax=1)
        a.set_xticks(range(M.shape[1]), cols); a.set_yticks(range(3), ["S0", "S1", "S2"]); a.set_title(t)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                a.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", color="white" if M[i, j] > .55 else "black", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig3_matrices_estimadas.png", dpi=300, bbox_inches="tight"); plt.close(fig)


def fig_prediccion():
    m = pd.read_csv(RES / "metricas_prediccion.csv")
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.7))
    for a, k, t in zip(ax, ["AUC", "AP", "BSS"], ["AUC", "Precisión promedio", "Brier skill score (vs tasa base)"]):
        g = m[m.metrica == k]
        y = np.arange(len(g))[::-1]
        a.errorbar(g.valor, y, xerr=[g.valor - g.ic95_inf, g.ic95_sup - g.valor], fmt="o", color="#1f4e79", capsize=3)
        a.set_yticks(y, g.modelo.str.replace(" ", "\n", n=1) if k == "AUC" else [""] * len(g)); a.set_title(t)
        if k == "AUC": a.axvline(.5, color="gray", ls=":")
        if k == "BSS": a.axvline(0, color="gray", ls=":")
    fig.tight_layout(); fig.savefig(FIG / "fig4_prediccion_real.png", dpi=300, bbox_inches="tight"); plt.close(fig)


def fig_lluvia():
    d = json.load(open(RES / "descriptivo_lluvia.json"))["lluvia_vs_inicio"]
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    for i, (k, nm, c) in enumerate([("sin_lluvia", "Sin lluvia", "#8d99ae"), ("con_lluvia", "Con lluvia", "#1f4e79")]):
        t, lo, hi = d[k]["tasa"] * 100, d[k]["ic95"][0] * 100, d[k]["ic95"][1] * 100
        ax.bar(i, t, color=c, width=.55); ax.errorbar(i, t, yerr=[[t - lo], [hi - t]], color="black", capsize=4)
        ax.text(i, hi + .2, f"{d[k]['inicios']}/{d[k]['vueltas']}", ha="center", fontsize=8)
    ax.set_xticks([0, 1], ["Sin lluvia", "Con lluvia"]); ax.set_ylabel("Inicio de neutralización por vuelta (%)")
    pass
    fig.tight_layout(); fig.savefig(FIG / "fig5_lluvia_vs_inicio.png", dpi=300); plt.close(fig)


def fig_carrera(circuito="Interlagos", anio=2024):
    carreras = vr.cargar()
    c = next((x for x in carreras if x["circuito"] == circuito and x["anio"] == anio), None)
    if c is None: return
    ent = [x for x in carreras if x is not c]
    m, _ = vr.ajustar(ent, "completo")
    post = m.posterior(c["obs"]); h = np.r_[vr.hazard(m, c["obs"]), np.nan]
    T = len(c["obs"]); x = np.arange(1, T + 1)
    fig, ax = plt.subplots(3, 1, figsize=(7.2, 4.2), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1.4]})
    ax[0].imshow((c["obs"] // 2)[None, :], aspect="auto", cmap="Blues", vmin=0, vmax=2, extent=[.5, T + .5, 0, 1])
    ax[0].plot(x[c["obs"] % 2 == 1], np.full((c["obs"] % 2 == 1).sum(), .5), "v", color="#e9c46a", ms=5, mec="black", mew=.4)
    ax[0].set_yticks([]); ax[0].set_title(f"{circuito} {anio}", fontsize=9)
    ax[0].set_ylabel("Lluvia\n(▼ amarilla)", rotation=0, ha="right", va="center")
    ax[1].fill_between(x, 0, c["neutral"], step="mid", color="#c1666b", alpha=.8); ax[1].set_yticks([]); ax[1].set_ylabel("Neutraliz.\nreal", rotation=0, ha="right", va="center")
    ax[2].plot(x, post[:, 2], color="#c1666b", label="P(S2 | toda la carrera)  suavizado")
    ax[2].plot(x, h, color="#1f4e79", label="Riesgo de inicio en t+1 (solo pasado)")
    ax[2].set_ylim(0, 1); ax[2].set_xlabel("Vuelta"); ax[2].legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout(); fig.savefig(FIG / "fig6_ejemplo_carrera.png", dpi=300); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_escenarios, fig_sensibilidad, fig_matrices, fig_prediccion, fig_lluvia, fig_carrera):
        try: f(); print("ok", f.__name__)
        except FileNotFoundError as e: print("falta", f.__name__, e)
