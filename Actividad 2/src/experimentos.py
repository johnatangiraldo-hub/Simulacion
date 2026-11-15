"""
experimentos.py - Simulación Monte Carlo del HMM en 3 escenarios + análisis de sensibilidad y reproducibilidad.

Diseño (semillas): una SeedSequence maestra (42) genera una semilla INDEPENDIENTE por (escenario, réplica).
Réplica = un "campeonato sintético" de K=20 carreras de T=60 vueltas (1200 observaciones).
Métricas por réplica:
  acc_viterbi   exactitud de la decodificación de Viterbi contra los estados simulados (conocidos en simulación)
  acc_filtrado  exactitud del estado más probable del filtrado (Forward)
  acc_mayoritaria exactitud de un predictor trivial que siempre dice el estado más frecuente (referencia)
  f1_neutral    F1 de detectar S2 con Viterbi
  ll_por_obs    log-verosimilitud por observación bajo los parámetros verdaderos (Forward)
  err_A, err_B  error de Frobenius tras Baum-Welch (con mejor permutación de estados)
  iter_bw       iteraciones de Baum-Welch
"""
import itertools, json, hashlib, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
from hmm import HMM
from modelo_f1 import hmm_inicial, A0, B0, PI0, ESTADOS, SIMBOLOS

RAIZ = Path(__file__).resolve().parent.parent
SEMILLA_MAESTRA = 42
N_REP, K_CARRERAS, T_VUELTAS = 100, 20, 60


def mezclar(P, eps):
    """(1-eps)*P + eps*uniforme (filas). Mantiene filas estocásticas."""
    return (1 - eps) * P + eps / P.shape[1]


def modelo_nominal():
    f = RAIZ / "resultados" / "parametros_estimados.json"
    if f.exists():
        d = json.load(open(f))
        return HMM(d["A"], d["B"], d["pi"], ESTADOS, SIMBOLOS), "estimado con datos reales OpenF1"
    return HMM(A0, B0, PI0, ESTADOS, SIMBOLOS), "supuesto del equipo (no hay datos estimados)"


def escenarios():
    nom, origen = modelo_nominal()
    # E2 carrera lluviosa: arranque con riesgo alto; S1 más persistente y con más salida a neutralización
    A2 = nom.A.copy(); A2[1, 2] = min(A2[1, 2] * 2.5, 0.5); A2[1, 0] *= 0.5
    A2[1] /= A2[1].sum()
    E2 = HMM(A2, nom.B, np.array([0.15, 0.75, 0.10]), ESTADOS, SIMBOLOS)
    # E3 ruido de calibración: 25 % de masa uniforme en A y B (señales menos informativas)
    E3 = HMM(mezclar(nom.A, 0.25), mezclar(nom.B, 0.25), nom.pi, ESTADOS, SIMBOLOS)
    return {"E1_nominal": nom, "E2_lluviosa": E2, "E3_ruidoso": E3}, origen


def mejor_permutacion(M_hat, M, ejes):
    """Alinea estados estimados con los verdaderos (identificabilidad hasta permutación)."""
    mejor, perm_b = np.inf, None
    for p in itertools.permutations(range(M.shape[0])):
        p = list(p)
        if ejes == "A":
            e = np.linalg.norm(M_hat[np.ix_(p, p)] - M)
        else:
            e = np.linalg.norm(M_hat[p] - M)
        if e < mejor:
            mejor, perm_b = e, p
    return mejor, perm_b


def f1(y, p, clase=2):
    tp = ((y == clase) & (p == clase)).sum(); fp = ((y != clase) & (p == clase)).sum(); fn = ((y == clase) & (p != clase)).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else np.nan


def replica(modelo, rng, K=K_CARRERAS, T=T_VUELTAS, ajustar=True):
    datos = [modelo.muestrear(T, rng) for _ in range(K)]
    q = np.concatenate([d[0] for d in datos])
    v = np.concatenate([modelo.viterbi(d[1])[0] for d in datos])
    f = np.concatenate([modelo.forward(d[1])[0].argmax(axis=1) for d in datos])
    ll = sum(modelo.loglik(d[1]) for d in datos) / (K * T)
    out = dict(acc_viterbi=(q == v).mean(), acc_filtrado=(q == f).mean(), acc_mayoritaria=np.bincount(q, minlength=3).max() / len(q),
               f1_neutral=f1(q, v), ll_por_obs=ll)
    if ajustar:
        init = hmm_inicial(True)
        init.A = mezclar(modelo.A, 0.3)[np.argsort(rng.random(3))]     # arranque perturbado
        init.A = init.A / init.A.sum(1, keepdims=True)
        init.B = mezclar(modelo.B, 0.3); init.pi = np.full(3, 1 / 3)
        m, hist = init.baum_welch([d[1] for d in datos], n_iter=200, tol=1e-6)
        eA, pA = mejor_permutacion(m.A, modelo.A, "A"); eB, _ = mejor_permutacion(m.B, modelo.B, "B")
        out.update(err_A=eA, err_B=eB, iter_bw=len(hist))
    return out


def correr_escenarios(sem=SEMILLA_MAESTRA, n_rep=N_REP, ajustar=True):
    escs, origen = escenarios()
    hijos = np.random.SeedSequence(sem).spawn(len(escs) * n_rep)
    filas = []
    for i, (nombre, mod) in enumerate(escs.items()):
        for r in range(n_rep):
            rng = np.random.default_rng(hijos[i * n_rep + r])
            filas.append(dict(escenario=nombre, replica=r, **replica(mod, rng, ajustar=ajustar)))
    return pd.DataFrame(filas), escs, origen


def resumen(df, metricas):
    filas = []
    for esc, g in df.groupby("escenario"):
        for m in metricas:
            x = g[m].dropna().values; n = len(x)
            mu, sd = x.mean(), x.std(ddof=1); h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
            filas.append(dict(escenario=esc, metrica=m, n=n, media=mu, desv_est=sd, minimo=x.min(), maximo=x.max(),
                              ic95_inf=mu - h, ic95_sup=mu + h))
    return pd.DataFrame(filas)


def comparaciones(df, metricas):
    """Welch t + d de Cohen + Mann-Whitney, con corrección de Holm por métrica."""
    filas = []
    pares = list(itertools.combinations(sorted(df.escenario.unique()), 2))
    for m in metricas:
        ps = []
        tmp = []
        for a, b in pares:
            x, y = df[df.escenario == a][m].dropna(), df[df.escenario == b][m].dropna()
            t, p = stats.ttest_ind(x, y, equal_var=False)
            sp = np.sqrt((x.var(ddof=1) + y.var(ddof=1)) / 2); d = (x.mean() - y.mean()) / sp if sp > 0 else np.nan
            u, pu = stats.mannwhitneyu(x, y, alternative="two-sided")
            tmp.append(dict(metrica=m, A=a, B=b, dif_medias=x.mean() - y.mean(), d_cohen=d, p_welch=p, p_mannwhitney=pu)); ps.append(p)
        orden = np.argsort(ps); k = len(ps); holm = np.empty(k); mx = 0
        for r, j in enumerate(orden):
            mx = max(mx, (k - r) * ps[j]); holm[j] = min(1, mx)
        for j, row in enumerate(tmp):
            row["p_holm_welch"] = holm[j]; filas.append(row)
    return pd.DataFrame(filas)


def sensibilidad(nom, sem=SEMILLA_MAESTRA, n_rep=50, n_rep_long=30):
    """P3: modelo verdadero = nominal; el decodificador usa parámetros desajustados."""
    ruta = []
    epsilons = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    hijos = np.random.SeedSequence([sem, 7]).spawn(len(epsilons) * n_rep)
    for i, eps in enumerate(epsilons):
        for r in range(n_rep):
            rng = np.random.default_rng(hijos[i * n_rep + r])
            datos = [nom.muestrear(T_VUELTAS, rng) for _ in range(K_CARRERAS)]
            q = np.concatenate([d[0] for d in datos])
            for tipo in ["A", "B", "pi"]:
                dec = nom.copia()
                if tipo == "A": dec.A = mezclar(nom.A, eps)
                elif tipo == "B": dec.B = mezclar(nom.B, eps)
                else: dec.pi = mezclar(nom.pi[None, :], eps)[0]
                v = np.concatenate([dec.viterbi(d[1])[0] for d in datos])
                ruta.append(dict(parametro=tipo, eps=eps, replica=r, acc_viterbi=(q == v).mean(), f1_neutral=f1(q, v)))
    # sensibilidad a la longitud de la carrera y de la muestra para Baum-Welch
    long = []
    for T in [20, 40, 60, 90]:
        hijos = np.random.SeedSequence([sem, 8, T]).spawn(n_rep_long)
        for r in range(n_rep_long):
            rng = np.random.default_rng(hijos[r])
            o = replica(nom, rng, K=K_CARRERAS, T=T)
            long.append(dict(T=T, replica=r, err_A=o["err_A"], err_B=o["err_B"], acc_viterbi=o["acc_viterbi"]))
    return pd.DataFrame(ruta), pd.DataFrame(long)


def reproducibilidad():
    """Misma semilla -> resultados idénticos (hash); semilla distinta -> distribución de la métrica."""
    d1, *_ = correr_escenarios(SEMILLA_MAESTRA, n_rep=10)
    d2, *_ = correr_escenarios(SEMILLA_MAESTRA, n_rep=10)
    h = lambda d: hashlib.sha256(d.round(12).to_csv(index=False).encode()).hexdigest()
    otras = []
    for s in [1, 2, 3, 4, 5]:
        d, *_ = correr_escenarios(s, n_rep=20, ajustar=False)
        otras.append(d[d.escenario == "E1_nominal"].acc_viterbi.mean())
    return dict(sha256_corrida1=h(d1), sha256_corrida2=h(d2), identicas=h(d1) == h(d2),
                acc_viterbi_E1_otras_semillas=otras, sd_entre_semillas=float(np.std(otras, ddof=1)))


def main():
    out = RAIZ / "resultados"; out.mkdir(exist_ok=True)
    df, escs, origen = correr_escenarios()
    df.to_csv(out / "resultados_crudos_escenarios.csv", index=False)
    mets = ["acc_viterbi", "acc_filtrado", "acc_mayoritaria", "f1_neutral", "ll_por_obs", "err_A", "err_B", "iter_bw"]
    r = resumen(df, mets); r.to_csv(out / "estadisticos_escenarios.csv", index=False)
    c = comparaciones(df, ["acc_viterbi", "f1_neutral", "err_A"]); c.to_csv(out / "comparaciones_escenarios.csv", index=False)
    s, l = sensibilidad(escs["E1_nominal"])
    s.to_csv(out / "sensibilidad_desajuste.csv", index=False); l.to_csv(out / "sensibilidad_longitud.csv", index=False)
    rep = reproducibilidad(); rep["origen_parametros_nominales"] = origen
    import platform, numpy, scipy, pandas, matplotlib
    rep["entorno"] = dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__,
                          pandas=pandas.__version__, matplotlib=matplotlib.__version__)
    json.dump(rep, open(out / "reproducibilidad.json", "w"), indent=2)
    for nm, m in escs.items():
        json.dump(dict(A=m.A.tolist(), B=m.B.tolist(), pi=m.pi.tolist()), open(out / f"parametros_{nm}.json", "w"), indent=1)
    print(r.round(4).to_string()); print(c.round(4).to_string()); print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
