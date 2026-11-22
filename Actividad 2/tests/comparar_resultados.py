"""
comparar_resultados.py - Verifica la reproducibilidad (Persona B).

Compara los archivos de resultados/ (o un CSV de datos) generados en este computador con la
versión guardada en el último commit de Git, y reporta la diferencia numérica máxima.

Uso (desde la carpeta "Actividad 2"):
    python tests/comparar_resultados.py                      # compara resultados/*.csv|json con el commit
    python tests/comparar_resultados.py --datos datos/openf1_descarga_verificacion.csv
                                                             # compara una descarga nueva con datos/openf1_secuencias_vuelta.csv
"""
import argparse, io, json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
TOL = 1e-9


def version_commit(ruta: Path) -> str:
    rel = "./" + ruta.relative_to(RAIZ).as_posix()
    return subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout


def numeros_json(x, pref=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from numeros_json(v, f"{pref}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from numeros_json(v, f"{pref}[{i}]")
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield pref, float(x)


def comparar_csv(a: pd.DataFrame, b: pd.DataFrame):
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        return f"estructura distinta {a.shape} vs {b.shape}", None
    num = a.select_dtypes("number").columns
    txt = [c for c in a.columns if c not in num]
    if txt and not a[txt].astype(str).equals(b[txt].astype(str)):
        return "columnas de texto distintas", None
    d = float(np.nanmax(np.abs(a[num].to_numpy(float) - b[num].to_numpy(float)))) if len(num) else 0.0
    return None, d


def comparar_resultados():
    filas, ok = [], True
    for f in sorted((RAIZ / "resultados").glob("*")):
        if f.suffix not in (".csv", ".json"):
            continue
        try:
            viejo = version_commit(f)
        except subprocess.CalledProcessError:
            filas.append((f.name, "NUEVO (no está en el commit)", "")); continue
        if f.suffix == ".csv":
            err, d = comparar_csv(pd.read_csv(f), pd.read_csv(io.StringIO(viejo)))
        else:
            a, b = dict(numeros_json(json.load(open(f)))), dict(numeros_json(json.loads(viejo)))
            ignorar = [k for k in a if k.startswith(".entorno")]
            claves = [k for k in a if k not in ignorar]
            err = None if set(claves) == {k for k in b if not k.startswith(".entorno")} else "claves distintas"
            d = max((abs(a[k] - b[k]) for k in claves), default=0.0) if err is None else None
        if err:
            ok = False; filas.append((f.name, "DIFERENTE", err))
        else:
            igual = d <= TOL
            ok &= igual
            filas.append((f.name, "IDÉNTICO" if igual else "DIFERENTE", f"dif. máx = {d:.3g}"))
    ancho = max(len(n) for n, _, _ in filas)
    for n, e, det in filas:
        print(f"{n:<{ancho}}  {e:<10}  {det}")
    print("\nRESULTADO:", "✅ todos los resultados se reprodujeron" if ok else "⚠️ hay diferencias (revisar arriba)")
    return ok


def comparar_datos(nuevo: Path):
    a = pd.read_csv(nuevo); b = pd.read_csv(RAIZ / "datos" / "openf1_secuencias_vuelta.csv")
    clave = ["anio", "circuito", "vuelta"]
    m = b.merge(a, on=clave, how="outer", suffixes=("_entregado", "_descargado"), indicator=True)
    solo_e = (m["_merge"] == "left_only").sum(); solo_d = (m["_merge"] == "right_only").sum()
    ambos = m[m["_merge"] == "both"]
    print(f"Vueltas entregadas: {len(b)} · descargadas: {len(a)} · en ambos: {len(ambos)}")
    print(f"Solo en el archivo entregado: {solo_e} · solo en la descarga: {solo_d}")
    for c in ["lluvia", "amarilla", "neutralizacion"]:
        dif = (ambos[f"{c}_entregado"] != ambos[f"{c}_descargado"]).sum()
        print(f"  {c:<15} vueltas distintas: {dif} ({dif / max(len(ambos), 1) * 100:.2f} %)")
    carreras = ambos.groupby(["anio", "circuito"]).apply(
        lambda g: sum((g[f"{c}_entregado"] != g[f"{c}_descargado"]).sum() for c in ["lluvia", "amarilla", "neutralizacion"]),
        include_groups=False)
    malas = carreras[carreras > 0]
    print(f"Carreras con alguna diferencia: {len(malas)} de {len(carreras)}")
    if len(malas):
        print(malas.sort_values(ascending=False).head(10).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", help="CSV descargado de nuevo para comparar con datos/openf1_secuencias_vuelta.csv")
    a = ap.parse_args()
    if a.datos:
        comparar_datos(Path(a.datos))
    else:
        sys.exit(0 if comparar_resultados() else 1)
