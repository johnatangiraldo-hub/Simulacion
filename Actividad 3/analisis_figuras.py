"""Análisis estadístico adicional y gráficas del problema bancario.

Lee los CSV generados por simulacion_bancaria.py y produce:
  * las tablas de estadísticos que usa el informe (diccionario devuelto);
  * ocho figuras PNG (carpeta de figuras).

Uso:  python analisis_figuras.py --resultados resultados --figuras entrega/figuras
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from simulacion_bancaria import (MEDIA_SERVICIO, PROB_ACCION, PROB_TIPO,
                                 media_global_llegada)

ETIQ = {"A_3_mixtas": "3 mixtas", "B_1R_2P": "1R + 2P", "C_2R_1P": "2R + 1P",
        "D_4_mixtas": "4 mixtas", "E_2R_2P": "2R + 2P", "F_1R_3P": "1R + 3P",
        "G_3R_1P": "3R + 1P"}
TIPOS = ["Rápido", "Normal", "Lento", "Muy lento"]

# Paleta de referencia (validada para barras/líneas adyacentes) y rampa azul.
AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#6b6a66"
RAMPA = ["#c6dbf5", "#8db8ec", "#4f93e0", "#1f5fae"]  # rápido -> muy lento
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": ["Liberation Sans", "DejaVu Sans"], "font.size": 9,
    "axes.edgecolor": "#9d9c97", "axes.labelcolor": TINTA2, "text.color": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "figure.dpi": 100, "savefig.dpi": 200,
})


def tcrit(n: int) -> float:
    return float(student_t.ppf(0.975, n - 1))


def ic(x) -> tuple[float, float, float, float]:
    """Media, desviación estándar, límite inferior y superior del IC 95 %."""
    a = np.asarray(x, dtype=float)
    m, s = a.mean(), a.std(ddof=1)
    h = tcrit(len(a)) * s / np.sqrt(len(a))
    return float(m), float(s), float(m - h), float(m + h)


def n_necesario(s: float, h: float, n0: int = 2) -> int:
    """Menor n tal que t(n-1)·s/√n <= h (IC 95 %), con s estimada en un piloto."""
    for n in range(2, 100000):
        if tcrit(n) * s / np.sqrt(n) <= h:
            return n
    return 100000


def _guardar(fig, ruta: Path):
    fig.savefig(ruta, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _rejilla(ax, eje="y"):
    ax.grid(axis=eje, color=REJILLA, linewidth=.8)
    ax.set_axisbelow(True)


def calcular(resultados: Path, figuras: Path) -> dict:
    figuras.mkdir(parents=True, exist_ok=True)
    lee = lambda n: pd.read_csv(resultados / f"{n}.csv", encoding="utf-8-sig")
    dem, cor, caj = lee("demanda_por_replica"), lee("escenarios_por_replica"), lee("cajeros_por_replica")
    tip, det = lee("tipos_por_replica"), lee("clientes_detalle")
    R: dict = {}
    reps = sorted(cor.replica.unique())
    R["n_replicas"] = len(reps)

    # ---------------- Validación del generador ----------------
    a = det[det.escenario == "A_3_mixtas"].sort_values(["replica", "llegada"])
    inter = a.groupby("replica").llegada.diff().fillna(a.llegada)  # primer intervalo desde 0
    R["validacion"] = {
        "interllegada_obs": float(inter.mean()), "interllegada_teo": media_global_llegada(),
        "servicio_obs": float(a.servicio.mean()),
        "servicio_teo": sum(PROB_ACCION[k] * sum(p * m for p, m in zip(PROB_TIPO[k], MEDIA_SERVICIO[k]))
                            for k in PROB_ACCION),
        "retiros_obs": float((a.accion == "Retiro").mean()), "retiros_teo": PROB_ACCION["Retiro"],
        "llegadas_dia_obs": float(dem.total.mean()),
        "llegadas_dia_teo": 480 / media_global_llegada(),
    }

    # ---------------- Punto 2 y 3: demanda ----------------
    filas = []
    for t in TIPOS:
        col = dem[f"Todos_{t}"]
        r = int(col.idxmin())
        filas.append(dict(tipo=t, media=col.mean(), de=col.std(ddof=1), minimo=int(col.min()),
                          replica_min=int(dem.loc[r, "replica"]), maximo=int(col.max()),
                          retiro=dem[f"Retiro_{t}"].mean(), pago=dem[f"Pago_{t}"].mean()))
    R["demanda_tipo"] = filas
    R["demanda_total"] = dict(media=dem.total.mean(), de=dem.total.std(ddof=1),
                              retiros=dem.Retiro.mean(), pagos=dem.Pago.mean(),
                              minimo=int(dem.total.min()),
                              replica_min=int(dem.loc[dem.total.idxmin(), "replica"]),
                              ret_min=int(dem.loc[dem.total.idxmin(), "Retiro"]),
                              pag_min=int(dem.loc[dem.total.idxmin(), "Pago"]))
    R["demanda_subtipo"] = [dict(accion=ac, tipo=t, media=dem[f"{ac}_{t}"].mean(),
                                 minimo=int(dem[f"{ac}_{t}"].min()),
                                 replica_min=int(dem.loc[dem[f"{ac}_{t}"].idxmin(), "replica"]))
                            for ac in ("Retiro", "Pago") for t in TIPOS]

    # Lectura alternativa del punto 3: usuarios de cada tipo que quedan sin atender al cierre
    tip["pendientes"] = tip.llegados - tip.finalizados_al_cierre
    pen = tip.groupby(["escenario", "tipo"]).pendientes.sum().unstack("tipo") / len(reps)
    esp_t = (tip.assign(w=tip.espera_media * tip.llegados).groupby(["escenario", "tipo"]).w.sum()
             / tip.groupby(["escenario", "tipo"]).llegados.sum()).unstack("tipo")
    R["pendientes_tipo"] = {e: {t: float(pen.loc[e, t]) for t in TIPOS} for e in ETIQ}
    R["espera_tipo"] = {e: {t: float(esp_t.loc[e, t]) for t in TIPOS} for e in ETIQ}
    R["menor_pendientes"] = {t: ETIQ[pen[t].idxmin()] for t in TIPOS}

    # ---------------- Punto 1: cajeros ----------------
    sis = det.groupby(["replica", "escenario", "caja"]).sistema.mean().rename("sistema_medio").reset_index()
    caj = caj.merge(sis, on=["replica", "escenario", "caja"])
    tabla_caj = []
    for e in ETIQ:
        for c, g in caj[caj.escenario == e].groupby("caja"):
            m, s, lo, hi = ic(g.servicio_medio)
            tabla_caj.append(dict(escenario=e, caja=c, capacidad=g.capacidad.iloc[0], clientes=g.clientes.mean(),
                                  servicio=m, servicio_de=s, servicio_lo=lo, servicio_hi=hi,
                                  espera=g.espera_media.mean(), sistema=g.sistema_medio.mean(),
                                  util=g.utilizacion_horario.mean()))
    R["cajas"] = tabla_caj
    A = caj[caj.escenario == "A_3_mixtas"].pivot(index="replica", columns="caja", values="servicio_medio")
    R["dif_cajas"] = {}
    for x, y in (("C1", "C3"), ("C1", "C2"), ("C2", "C3")):
        R["dif_cajas"][f"{x}-{y}"] = ic(A[x] - A[y])
    # ANOVA de un factor sobre servicio medio diario (comprobación de homogeneidad)
    from scipy.stats import f_oneway
    R["anova_cajas"] = float(f_oneway(A.C1, A.C2, A.C3).pvalue)

    # ---------------- Escenarios ----------------
    g = cor.groupby("escenario")
    piv = lambda c: cor.pivot(index="replica", columns="escenario", values=c)
    esc = []
    for e in ETIQ:
        x = cor[cor.escenario == e]
        m, s, lo, hi = ic(x.espera_media)
        sub = det[det.escenario == e]
        esc.append(dict(escenario=e, cajas=int(x.cajas.iloc[0]), espera=m, de=s, lo=lo, hi=hi,
                        retiro=x.espera_Retiro.mean(), pago=x.espera_Pago.mean(),
                        p95=x.espera_p95.mean(), pend=x.pendientes_al_cierre.mean(),
                        util=x.utilizacion_media.mean(), fuera=x.atencion_fuera_horario.mean(),
                        sin_espera=float((sub.espera <= 1e-9).mean()),
                        mayor5=float((sub.espera > 5).mean()), mayor10=float((sub.espera > 10).mean()),
                        Lq=x.Lq_durante_horario.mean(), llegados=x.llegados.mean()))
    R["escenarios"] = esc
    pe = piv("espera_media")
    R["diferencias"] = {k: ic(pe[a_] - pe[b_]) for k, (a_, b_) in {
        "B-C": ("B_1R_2P", "C_2R_1P"), "C-A": ("C_2R_1P", "A_3_mixtas"), "B-A": ("B_1R_2P", "A_3_mixtas"),
        "A-D": ("A_3_mixtas", "D_4_mixtas"), "A-E": ("A_3_mixtas", "E_2R_2P"),
        "E-D": ("E_2R_2P", "D_4_mixtas")}.items()}
    # IC emparejado para la espera por operación en A y E (decisión de cuarta caja)
    R["ic_op"] = {e: {"Retiro": ic(cor[cor.escenario == e].espera_Retiro),
                      "Pago": ic(cor[cor.escenario == e].espera_Pago)} for e in ETIQ}

    # ---------------- Little y utilización teórica ----------------
    lam = 1 / media_global_llegada()
    ES = {a_: sum(p * m for p, m in zip(PROB_TIPO[a_], MEDIA_SERVICIO[a_])) for a_ in PROB_TIPO}
    carga = {"Retiro": lam * PROB_ACCION["Retiro"] * ES["Retiro"], "Pago": lam * PROB_ACCION["Pago"] * ES["Pago"]}
    R["carga"] = dict(lam=lam, ES=ES, erlangs=carga, total=sum(carga.values()))
    rho = []
    from simulacion_bancaria import ESCENARIOS
    for e, caps in ESCENARIOS.items():
        for grupo in ("Mixto", "Retiro", "Pago"):
            n = sum(c == grupo for c in caps)
            if not n:
                continue
            if grupo == "Mixto":
                teo = (carga["Retiro"] + carga["Pago"]) / n
            else:
                teo = carga[grupo] / n
            obs = caj[(caj.escenario == e) & (caj.capacidad == grupo)].utilizacion_horario.mean()
            rho.append(dict(escenario=e, grupo=grupo, n=n, teo=teo, obs=float(obs)))
    R["rho"] = rho
    R["little"] = [dict(escenario=r["escenario"], Lq=r["Lq"], little=r["llegados"] / 480 * r["espera"])
                   for r in esc]

    # ---------------- Réplicas necesarias ----------------
    rep = []
    for e in ETIQ:
        x = pe[e].values
        s10, s30 = x[:10].std(ddof=1), x.std(ddof=1)
        h10 = tcrit(10) * s10 / np.sqrt(10)
        h30 = tcrit(30) * s30 / np.sqrt(30)
        rep.append(dict(escenario=e, s10=s10, s30=s30, h10=h10, h30=h30,
                        n_025=n_necesario(s10, .25, 10), n_050=n_necesario(s10, .50, 10),
                        n_050_30=n_necesario(s30, .50, 30)))
    R["replicas"] = rep
    pares = {"B-C": ("B_1R_2P", "C_2R_1P"), "C-A": ("C_2R_1P", "A_3_mixtas"), "A-D": ("A_3_mixtas", "D_4_mixtas")}
    R["replicas_pares"] = {}
    for k, (a_, b_) in pares.items():
        d = (pe[a_] - pe[b_]).values
        R["replicas_pares"][k] = dict(ic10=ic(d[:10]), ic30=ic(d),
                                      excluye0_10=bool(ic(d[:10])[2] > 0 or ic(d[:10])[3] < 0),
                                      excluye0_30=bool(ic(d)[2] > 0 or ic(d)[3] < 0))

    # =============================== FIGURAS ===============================
    # F1 Usuarios por tipo (apilado retiro/pago, barras de error = DE del total)
    fig, ax = plt.subplots(figsize=(6.3, 3.3))
    x = np.arange(4)
    ret = [f["retiro"] for f in filas]; pag = [f["pago"] for f in filas]
    ax.bar(x, ret, .55, color=AZUL, label="Retiros")
    ax.bar(x, pag, .55, bottom=ret, color=NARANJA, label="Pagos", linewidth=0,
           edgecolor="white")
    ax.errorbar(x, [f["media"] for f in filas], yerr=[f["de"] for f in filas], fmt="none",
                ecolor=TINTA2, capsize=3, linewidth=1)
    for i, f in enumerate(filas):
        ax.text(i, f["media"] + f["de"] + 1.5, f"{f['media']:.1f}".replace(".", ","),
                ha="center", color=TINTA, fontsize=8.5)
    ax.set_xticks(x, TIPOS); ax.set_ylabel("Usuarios por día (promedio de 30 réplicas)")
    ax.legend(frameon=False, ncol=2, loc="upper right"); _rejilla(ax)
    ax.set_ylim(0, 90)
    _guardar(fig, figuras / "fig3_usuarios_por_tipo.png")

    # F2 Heatmap réplica x tipo
    M = np.array([[dem.loc[dem.replica == r, f"Todos_{t}"].iloc[0] for t in TIPOS] for r in reps])
    fig, ax = plt.subplots(figsize=(6.3, 5.6))
    im = ax.imshow(M, aspect="auto", cmap=matplotlib.colors.LinearSegmentedColormap.from_list("az", ["#eaf2fc", "#1f5fae"]))
    ax.set_xticks(range(4), TIPOS); ax.set_yticks(range(0, 30, 2), [str(r) for r in reps[::2]])
    ax.set_ylabel("Réplica (jornada simulada)"); ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    for i in range(30):
        for j in range(4):
            claro = M[i, j] < M.max() * .72
            ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=6.5,
                    color=TINTA if claro else "white")
    for j in range(4):
        i = int(np.argmin(M[:, j]))
        ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=NARANJA, linewidth=2))
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.02); cb.set_label("Usuarios por jornada")
    cb.outline.set_visible(False)
    _guardar(fig, figuras / "fig4_usuarios_por_replica.png")

    # F3 Cajeros (3 mixtas)
    cA = [r for r in tabla_caj if r["escenario"] == "A_3_mixtas"]
    fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.0))
    xs = np.arange(3)
    axs[0].bar(xs, [r["servicio"] for r in cA], .5, color=AZUL,
               yerr=[[r["servicio"] - r["servicio_lo"] for r in cA], [r["servicio_hi"] - r["servicio"] for r in cA]],
               ecolor=TINTA2, capsize=3)
    for i, r in enumerate(cA):
        axs[0].text(i, r["servicio_hi"] + .08, f"{r['servicio']:.2f}".replace(".", ","), ha="center", fontsize=8.5)
    axs[0].set_title("Servicio medio por usuario"); axs[0].set_ylim(0, 4.4)
    axs[1].bar(xs, [r["espera"] for r in cA], .5, color=NARANJA)
    for i, r in enumerate(cA):
        axs[1].text(i, r["espera"] + .015, f"{r['espera']:.2f}".replace(".", ","), ha="center", fontsize=8.5)
    axs[1].set_title("Espera media en cola"); axs[1].set_ylim(0, .85)
    for a_ in axs:
        a_.set_xticks(xs, [r["caja"] for r in cA]); a_.set_ylabel("Minutos"); _rejilla(a_)
    fig.tight_layout()
    _guardar(fig, figuras / "fig2_cajeros.png")

    # F4 Convergencia / réplicas
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 3.1))
    xa = pe["A_3_mixtas"].values
    n = np.arange(4, 31)
    med = np.array([xa[:k].mean() for k in n])
    hw = np.array([tcrit(k) * xa[:k].std(ddof=1) / np.sqrt(k) for k in n])
    axs[0].fill_between(n, med - hw, med + hw, color=AZUL, alpha=.18, linewidth=0)
    axs[0].plot(n, med, color=AZUL, linewidth=2)
    axs[0].axvline(10, color=GRIS, linestyle=":", linewidth=1)
    axs[0].set_ylim(0, 1.3)
    axs[0].text(10.4, 1.2, "mínimo exigido (10)", fontsize=7.5, color=TINTA2)
    axs[0].set_title("Espera media (3 mixtas)"); axs[0].set_xlabel("Réplicas acumuladas")
    axs[0].set_ylabel("Minutos (media e IC 95 %)")
    for e, col, lab in (("A_3_mixtas", AZUL, "3 mixtas"), ("E_2R_2P", "#1baf7a", "2R + 2P"),
                        ("C_2R_1P", NARANJA, "2R + 1P")):
        v = pe[e].values
        h = [tcrit(k) * v[:k].std(ddof=1) / np.sqrt(k) for k in n]
        axs[1].plot(n, h, color=col, linewidth=2, label=lab)
    axs[1].axvline(10, color=GRIS, linestyle=":", linewidth=1)
    axs[1].set_title("Semiancho del IC 95 %"); axs[1].set_xlabel("Réplicas acumuladas")
    axs[1].set_ylabel("Minutos"); axs[1].set_xlim(4, 30)
    axs[1].legend(frameon=False, fontsize=8, loc="upper right")
    for a_ in axs:
        _rejilla(a_)
    fig.tight_layout()
    _guardar(fig, figuras / "fig1_convergencia_replicas.png")

    # F5 Boxplot espera media diaria por escenario
    fig, ax = plt.subplots(figsize=(6.5, 3.3))
    datos = [pe[e].values for e in ETIQ]
    bp = ax.boxplot(datos, widths=.5, patch_artist=True, showfliers=True,
                    medianprops=dict(color=TINTA, linewidth=1.5),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor="none", markeredgecolor=TINTA2))
    for p_, e in zip(bp["boxes"], ETIQ):
        p_.set(facecolor="#b9d3f3" if "mixtas" in ETIQ[e] else ("#f6c3ac" if e in ("B_1R_2P", "C_2R_1P", "F_1R_3P", "G_3R_1P") else "#d9d8d3"),
               edgecolor=TINTA2)
    ax.set_xticks(range(1, 8), list(ETIQ.values())); ax.set_ylabel("Espera media diaria (min)"); _rejilla(ax)
    _guardar(fig, figuras / "fig5_distribucion_espera.png")

    # F6 Utilización teórica vs observada
    fig, ax = plt.subplots(figsize=(6.5, 3.3))
    etiquetas = [f"{ETIQ[r['escenario']]}\n({r['grupo'].lower()}{'s' if r['n'] > 1 else ''})" for r in rho]
    xs = np.arange(len(rho))
    ax.bar(xs - .2, [r["teo"] for r in rho], .38, color="#b9d3f3", label="Teórica (λ·E[S]/c)")
    ax.bar(xs + .2, [r["obs"] for r in rho], .38, color=AZUL, label="Observada (simulación)")
    ax.axhline(1, color=GRIS, linestyle="--", linewidth=1)
    ax.text(len(rho) - .5, 1.02, "límite de estabilidad ρ = 1", ha="right", fontsize=7.5, color=TINTA2)
    ax.set_xticks(xs, etiquetas, fontsize=6.3); ax.set_ylabel("Utilización por caja (ρ)")
    ax.set_ylim(0, 1.12); ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=8); _rejilla(ax)
    _guardar(fig, figuras / "fig6_utilizacion.png")

    # F7 P(espera > t)
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    tt = np.linspace(0, 30, 301)
    estilos = {"A_3_mixtas": (AZUL, "-"), "D_4_mixtas": ("#1baf7a", "-"), "E_2R_2P": ("#6250d6", "-"),
               "C_2R_1P": (NARANJA, "-"), "B_1R_2P": (NARANJA, "--")}
    for e, (col, ls) in estilos.items():
        w = np.sort(det[det.escenario == e].espera.values)
        s_ = 1 - np.searchsorted(w, tt, side="right") / len(w)
        ax.plot(tt, s_ * 100, color=col, linestyle=ls, linewidth=2, label=ETIQ[e])
    ax.axvline(5, color=GRIS, linestyle=":", linewidth=1)
    ax.text(5.3, 92, "5 min", fontsize=7.5, color=TINTA2)
    ax.set_xlabel("Espera t (minutos)"); ax.set_ylabel("% de usuarios que esperan más de t")
    ax.set_ylim(0, 100); ax.set_xlim(0, 30); ax.legend(frameon=False, fontsize=8); _rejilla(ax)
    _guardar(fig, figuras / "fig7_cola_espera.png")

    # F8 Compromiso retiro vs pago
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.add_patch(plt.Rectangle((0, 0), 5, 5, color="#e6f2ea", linewidth=0, zorder=0))
    ax.text(.15, 4.55, "Ambas esperas < 5 min", fontsize=7.5, color="#2f6b46")
    pos = {"D_4_mixtas": (1.4, -.75), "A_3_mixtas": (2.2, .8), "E_2R_2P": (1.4, 1.9),
           "C_2R_1P": (1.5, 7.2), "G_3R_1P": (.0, 8.75), "B_1R_2P": (7.0, 1.7), "F_1R_3P": (7.0, -.75)}
    for r in esc:
        col = AZUL if (r["cajas"] == 3 and "mix" in ETIQ[r["escenario"]]) else (GRIS if r["cajas"] == 4 else NARANJA)
        ax.scatter(r["retiro"], r["pago"], s=55, color=col, zorder=3, edgecolor="white", linewidth=1.2)
        ax.annotate(ETIQ[r["escenario"]], (r["retiro"], r["pago"]), xytext=pos[r["escenario"]], fontsize=8,
                    arrowprops=dict(arrowstyle="-", color="#9d9c97", linewidth=.8), va="center")
    ax.set_xlabel("Espera media de retiros (min)"); ax.set_ylabel("Espera media de pagos (min)")
    ax.set_xlim(-.3, 8.6); ax.set_ylim(-1.2, 9.4); _rejilla(ax, "both")
    _guardar(fig, figuras / "fig8_compromiso_operaciones.png")

    (figuras / "estadisticos.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float),
                                               encoding="utf-8")
    return R


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resultados", type=Path, default=Path("resultados"))
    p.add_argument("--figuras", type=Path, default=Path("entrega/figuras"))
    a = p.parse_args()
    calcular(a.resultados, a.figuras)
    print("Figuras y estadísticos en", a.figuras)
