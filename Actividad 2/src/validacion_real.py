"""
validacion_real.py - Ajuste y validación del HMM con datos reales de OpenF1 (2023-2025).

* Ajuste: Baum-Welch con etiquetas parciales. En cada vuelta se conoce (race_control) si hubo neutralización;
  la máscara obliga a S2 en vueltas neutralizadas y lo prohíbe en las demás. La separación S0/S1 es latente
  y se aprende de lluvia + banderas amarillas.
* Tarea de predicción (hazard): P(inicio de neutralización en la vuelta t+1 | observaciones 1..t, vuelta t no neutralizada).
* Validación cruzada por carreras (K pliegues) -> el modelo nunca ve la carrera que predice.
* Comparación: M0 tasa base | M1 tabla por observación actual | M2 HMM sin lluvia | M3 HMM con lluvia.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
from hmm import HMM
from modelo_f1 import hmm_inicial, simbolo, transformar_obs, ESTADOS, SIMBOLOS

RAIZ = Path(__file__).resolve().parent.parent
SEMILLA = 42


def cargar(path=RAIZ / "datos" / "openf1_secuencias_vuelta.csv"):
    df = pd.read_csv(path)
    carreras = []
    for key, g in df.groupby("session_key", sort=True):
        g = g.sort_values("vuelta")
        carreras.append(dict(key=int(key), circuito=g.circuito.iloc[0], anio=int(g.anio.iloc[0]),
                             obs=simbolo(g.lluvia.values, g.amarilla.values).astype(int),
                             neutral=(g.neutralizacion.values > 0).astype(int)))
    return carreras


def mascara(neutral):
    m = np.ones((len(neutral), 3))
    m[neutral == 1, :2] = 0.0   # neutralizada -> solo S2
    m[neutral == 0, 2] = 0.0    # no neutralizada -> solo S0/S1
    return m


def ajustar(carreras, modo="completo", n_iter=200):
    if modo is True: modo = "completo"
    if modo is False: modo = "solo_amarilla"
    seqs = [transformar_obs(c["obs"], modo) for c in carreras]
    masks = [mascara(c["neutral"]) for c in carreras]
    m, hist = hmm_inicial(modo).baum_welch(seqs, n_iter=n_iter, tol=1e-7, mascaras=masks)
    return m, hist


def hazard(modelo, obs):
    """P(q_{t+1}=S2 | q_t != S2, o_1..o_t) para t=0..T-2 (filtrado de Forward)."""
    a, _, _ = modelo.forward(obs)
    ns = a[:, :2]
    return (ns * modelo.A[:2, 2]).sum(axis=1)[:-1] / ns.sum(axis=1)[:-1]


# ---------------------------------------------------------------- métricas
def auc(y, p):
    y = np.asarray(y); p = np.asarray(p)
    if y.sum() == 0 or y.sum() == len(y):
        return np.nan
    r = stats.rankdata(p)
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def ap(y, p):
    y = np.asarray(y); o = np.argsort(-p, kind="stable"); y = y[o]
    tp = np.cumsum(y); prec = tp / np.arange(1, len(y) + 1)
    return float((prec * y).sum() / max(y.sum(), 1))


def brier(y, p):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def metricas(y, p, p_base, es_base=False):
    """es_base=True: predictor constante por definicion -> AUC=0.5 y AP=prevalencia (evita artefacto de pliegues)."""
    b, b0 = brier(y, p), brier(y, p_base)
    if es_base:
        return dict(AUC=0.5, AP=float(np.mean(y)), Brier=b, BSS=0.0)
    return dict(AUC=auc(y, p), AP=ap(y, p), Brier=b, BSS=1 - b / b0 if b0 > 0 else np.nan)


# ---------------------------------------------------------------- validación cruzada
def tabla_obs(carreras_ent, M=6):
    n1 = np.ones(M); n = 2 * np.ones(M)   # Laplace
    for c in carreras_ent:
        idx = np.where(c["neutral"][:-1] == 0)[0]
        for t in idx:
            n[c["obs"][t]] += 1; n1[c["obs"][t]] += c["neutral"][t + 1]
    return n1 / n


def tasa_base(carreras_ent):
    n = n1 = 0
    for c in carreras_ent:
        idx = np.where(c["neutral"][:-1] == 0)[0]
        n += len(idx); n1 += c["neutral"][idx + 1].sum()
    return (n1 + 1) / (n + 2)


def cv_predicciones(carreras, k=10, semilla=SEMILLA):
    rng = np.random.default_rng(semilla)
    orden = rng.permutation(len(carreras))
    pliegues = np.array_split(orden, k)
    filas = []
    for f, test_idx in enumerate(pliegues):
        test = [carreras[i] for i in test_idx]
        ent = [carreras[i] for i in orden if i not in set(test_idx)]
        base = tasa_base(ent); tabla = tabla_obs(ent)
        m3, _ = ajustar(ent, "completo"); m2, _ = ajustar(ent, "solo_amarilla"); m4, _ = ajustar(ent, "lluvia_binaria")
        for c in test:
            idx = np.where(c["neutral"][:-1] == 0)[0]
            y = c["neutral"][idx + 1]
            h3 = hazard(m3, c["obs"])[idx]; h2 = hazard(m2, transformar_obs(c["obs"], "solo_amarilla"))[idx]
            h4 = hazard(m4, transformar_obs(c["obs"], "lluvia_binaria"))[idx]
            h1 = tabla[c["obs"][idx]]
            for j, t in enumerate(idx):
                filas.append((c["key"], c["circuito"], c["anio"], t + 1, y[j], base, h1[j], h2[j], h3[j], h4[j],
                              int((c["obs"][t] // 2) > 0)))
    return pd.DataFrame(filas, columns=["key", "circuito", "anio", "vuelta", "y", "M0", "M1", "M2", "M3", "M4", "lluvia_t"])


def bootstrap_por_carrera(df, B=1000, semilla=SEMILLA):
    rng = np.random.default_rng(semilla)
    keys = df.key.unique(); grupos = {k: df[df.key == k] for k in keys}
    res = {m: {"AUC": [], "AP": [], "Brier": [], "BSS": []} for m in ["M0", "M1", "M2", "M3", "M4"]}
    for _ in range(B):
        d = pd.concat([grupos[k] for k in rng.choice(keys, len(keys))])
        for m in res:
            mm = metricas(d.y.values, d[m].values, d.M0.values, es_base=(m == "M0"))
            for kk, v in mm.items():
                res[m][kk].append(v)
    return res


def main():
    carreras = cargar()
    out = RAIZ / "resultados"; out.mkdir(exist_ok=True)
    # --- descriptivo
    desc = []
    for c in carreras:
        idx = np.where(c["neutral"][:-1] == 0)[0]
        desc.append(dict(key=c["key"], circuito=c["circuito"], anio=c["anio"], vueltas=len(c["obs"]),
                         vueltas_lluvia=int((c["obs"] // 2 > 0).sum()), vueltas_amarilla=int((c["obs"] % 2).sum()),
                         vueltas_neutralizadas=int(c["neutral"].sum()),
                         inicios=int(c["neutral"][idx + 1].sum())))
    desc = pd.DataFrame(desc); desc.to_csv(out / "descriptivo_carreras.csv", index=False)
    # tasa de inicio con/sin lluvia (todas las vueltas no neutralizadas)
    n = {0: [0, 0], 1: [0, 0]}
    for c in carreras:
        idx = np.where(c["neutral"][:-1] == 0)[0]
        for t in idx:
            r = int(c["obs"][t] // 2 > 0); n[r][0] += 1; n[r][1] += c["neutral"][t + 1]
    tab = np.array([[n[0][1], n[0][0] - n[0][1]], [n[1][1], n[1][0] - n[1][1]]])
    orr, pf = stats.fisher_exact(tab)
    # IC de Wilson
    def wilson(x, n_, z=1.96):
        p = x / n_; d = 1 + z * z / n_
        c0 = (p + z * z / (2 * n_)) / d; h = z * np.sqrt(p * (1 - p) / n_ + z * z / (4 * n_ * n_)) / d
        return c0 - h, c0 + h
    lluvia_tab = dict(sin_lluvia=dict(vueltas=n[0][0], inicios=n[0][1], tasa=n[0][1] / n[0][0], ic95=wilson(n[0][1], n[0][0])),
                      con_lluvia=dict(vueltas=n[1][0], inicios=n[1][1], tasa=n[1][1] / n[1][0], ic95=wilson(n[1][1], n[1][0])),
                      odds_ratio=orr, p_fisher=pf)
    # --- ajuste con todos los datos (parámetros nominales para las simulaciones)
    m3, hist = ajustar(carreras, "completo")
    json.dump(dict(A=m3.A.tolist(), B=m3.B.tolist(), pi=m3.pi.tolist(), estados=ESTADOS, simbolos=SIMBOLOS,
                   iteraciones=len(hist), loglik=hist[-1], n_carreras=len(carreras),
                   n_vueltas=int(sum(len(c["obs"]) for c in carreras))),
              open(out / "parametros_estimados.json", "w"), indent=2)
    # --- validación cruzada: semilla principal + estabilidad frente a la partición
    df = cv_predicciones(carreras, k=10, semilla=SEMILLA)
    df.to_csv(out / "predicciones_cv.csv", index=False)
    boot = bootstrap_por_carrera(df)
    filas = []
    for m, nombre in [("M0", "Tasa base"), ("M1", "Tabla por observacion"), ("M2", "HMM sin lluvia"), ("M3", "HMM con lluvia (3 niveles)"), ("M4", "HMM lluvia binaria (exploratorio)")]:
        pt = metricas(df.y.values, df[m].values, df.M0.values, es_base=(m == "M0"))
        for kk, v in pt.items():
            b = np.array(boot[m][kk]); b = b[~np.isnan(b)]
            filas.append(dict(modelo=nombre, metrica=kk, valor=v, ic95_inf=np.percentile(b, 2.5) if len(b) else np.nan,
                              ic95_sup=np.percentile(b, 97.5) if len(b) else np.nan))
    pd.DataFrame(filas).to_csv(out / "metricas_prediccion.csv", index=False)
    estab = []
    for s in range(5):
        d = cv_predicciones(carreras, k=10, semilla=1000 + s)
        for m in ["M1", "M2", "M3", "M4"]:
            estab.append(dict(semilla_particion=1000 + s, modelo=m, **metricas(d.y.values, d[m].values, d.M0.values)))
    pd.DataFrame(estab).to_csv(out / "estabilidad_particiones.csv", index=False)
    json.dump(dict(lluvia_vs_inicio=lluvia_tab, n_obs_hazard=int(len(df)), n_inicios=int(df.y.sum())),
              open(out / "descriptivo_lluvia.json", "w"), indent=2, default=float)
    print(pd.DataFrame(filas).round(3).to_string())
    print(json.dumps(lluvia_tab, indent=1, default=float))


if __name__ == "__main__":
    main()
