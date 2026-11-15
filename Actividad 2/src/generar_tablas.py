"""generar_tablas.py - Convierte resultados/*.csv|json en tablas LaTeX (articulo/tablas/*.tex). Evita transcribir cifras a mano."""
import json
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES, OUT = RAIZ / "resultados", RAIZ / "articulo" / "tablas"; OUT.mkdir(parents=True, exist_ok=True)
f = lambda x, d=3: f"{x:.{d}f}".replace(".", ",") if pd.notna(x) else "--"


def tabla_escenarios():
    r = pd.read_csv(RES / "estadisticos_escenarios.csv")
    nombres = {"acc_viterbi": "Exactitud Viterbi", "acc_filtrado": "Exactitud filtrado", "acc_mayoritaria": "Exactitud trivial (siempre S0)", "f1_neutral": "F1 neutralización (S2)",
               "ll_por_obs": "Log-verosim. por obs.", "err_A": r"Error $\|\hat A-A\|_F$", "err_B": r"Error $\|\hat B-B\|_F$", "iter_bw": "Iteraciones Baum-Welch"}
    L = [r"\begin{tabular}{llrrrrr}", r"\toprule", r"Escenario & Métrica & Media & D.E. & Mín. & Máx. & IC95\,\% \\", r"\midrule"]
    for esc, g in r.groupby("escenario", sort=True):
        for i, (_, w) in enumerate(g.iterrows()):
            dd = 1 if w.metrica == "iter_bw" else 3
            L.append(f"{esc.replace('_', ' ') if i == 0 else ''} & {nombres[w.metrica]} & {f(w.media, dd)} & {f(w.desv_est, dd)} & {f(w.minimo, dd)} & {f(w.maximo, dd)} & [{f(w.ic95_inf, dd)}; {f(w.ic95_sup, dd)}] \\\\")
        L.append(r"\midrule")
    L[-1] = r"\bottomrule"; L.append(r"\end{tabular}")
    (OUT / "tabla_escenarios.tex").write_text("\n".join(L), encoding="utf-8")


def tabla_comparaciones():
    c = pd.read_csv(RES / "comparaciones_escenarios.csv")
    L = [r"\begin{tabular}{llrrr}", r"\toprule", r"Métrica & Comparación & Dif. medias & $d$ de Cohen & $p$ (Holm) \\", r"\midrule"]
    for _, w in c.iterrows():
        p = "<0,001" if w.p_holm_welch < 0.001 else f(w.p_holm_welch, 3)
        L.append(f"{w.metrica.replace('_', ' ')} & {w.A.split('_')[0]} vs {w.B.split('_')[0]} & {f(w.dif_medias)} & {f(w.d_cohen, 2)} & {p} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tabla_comparaciones.tex").write_text("\n".join(L), encoding="utf-8")


def tabla_prediccion():
    m = pd.read_csv(RES / "metricas_prediccion.csv")
    L = [r"\begin{tabular}{lcccc}", r"\toprule", r"Modelo & AUC & Precisión prom. & Brier & BSS \\", r"\midrule"]
    for nom, g in m.groupby("modelo", sort=False):
        cel = []
        for k in ["AUC", "AP", "Brier", "BSS"]:
            w = g[g.metrica == k].iloc[0]
            d = 4 if k in ("Brier",) else 3
            cel.append(f"{f(w.valor, d)} [{f(w.ic95_inf, d)}; {f(w.ic95_sup, d)}]" if pd.notna(w.ic95_inf) else f(w.valor, d))
        L.append(f"{nom} & " + " & ".join(cel) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tabla_prediccion.tex").write_text("\n".join(L), encoding="utf-8")


def tabla_descriptiva():
    d = pd.read_csv(RES / "descriptivo_carreras.csv")
    L = [r"\begin{tabular}{lrrrrr}", r"\toprule", r"Año & Carreras & Vueltas & Vueltas con lluvia & Vueltas neutralizadas & Inicios de neutralización \\", r"\midrule"]
    for a, g in d.groupby("anio"):
        L.append(f"{a} & {len(g)} & {g.vueltas.sum()} & {g.vueltas_lluvia.sum()} & {g.vueltas_neutralizadas.sum()} & {g.inicios.sum()} \\\\")
    L += [r"\midrule", f"Total & {len(d)} & {d.vueltas.sum()} & {d.vueltas_lluvia.sum()} & {d.vueltas_neutralizadas.sum()} & {d.inicios.sum()} \\\\", r"\bottomrule", r"\end{tabular}"]
    (OUT / "tabla_descriptiva.tex").write_text("\n".join(L), encoding="utf-8")


def tabla_matrices():
    d = json.load(open(RES / "parametros_estimados.json"))
    A, B, pi = np.array(d["A"]), np.array(d["B"]), np.array(d["pi"])
    L = [r"\begin{tabular}{l" + "r" * 3 + "r}", r"\toprule", r" & S0 & S1 & S2 & $\pi$ \\", r"\midrule"]
    for i, n in enumerate(["S0", "S1", "S2"]):
        L.append(f"{n} & " + " & ".join(f(x) for x in A[i]) + f" & {f(pi[i])} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tabla_A_pi.tex").write_text("\n".join(L), encoding="utf-8")
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule", r" & 0/0 & 0/1 & 1/0 & 1/1 & 2/0 & 2/1 \\", r"\midrule"]
    for i, n in enumerate(["S0", "S1", "S2"]):
        L.append(f"{n} & " + " & ".join(f(x) for x in B[i]) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tabla_B.tex").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    for fn in (tabla_descriptiva, tabla_matrices, tabla_escenarios, tabla_comparaciones, tabla_prediccion):
        try: fn(); print("ok", fn.__name__)
        except FileNotFoundError as e: print("falta", fn.__name__, e)
