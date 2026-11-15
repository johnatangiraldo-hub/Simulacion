"""
descargar_datos.py - Reproduce datos/openf1_secuencias_vuelta.csv desde la API pública OpenF1 (https://openf1.org).

Uso:  python src/descargar_datos.py --anios 2023 2024 2025
Requiere internet y `pip install requests pandas`. Respeta el límite de la API (pausas y reintentos).

Por cada carrera construye, VUELTA A VUELTA:
  lluvia          0 sin lluvia | 1 intermitente (0<fracción<1 de muestras de 1 min) | 2 continua   (endpoint /weather)
  amarilla        1 si hubo bandera amarilla o doble amarilla en la vuelta                          (endpoint /race_control)
  neutralizacion  0 ninguna | 1 VSC | 2 Safety Car | 3 bandera roja (se toma el máximo en la vuelta) (endpoint /race_control)
La ventana de la vuelta L es [inicio_L, inicio_{L+1}), con inicio_L = mínimo de date_start entre pilotos (endpoint /laps).
NOTA: los datos de esta entrega se generaron con la misma lógica implementada en JavaScript desde el navegador
(el entorno de desarrollo no podía llamar a la API desde la línea de comandos). Para verificar que este script
reproduce el CSV entregado, use --salida (si no, SOBRESCRIBE los datos entregados) y compare:
    python src/descargar_datos.py --salida datos/openf1_descarga_verificacion.csv
    python tests/comparar_resultados.py --datos datos/openf1_descarga_verificacion.csv
Resultado de la verificación: ver REPRODUCCION.md.
"""
import argparse, time, sys
from pathlib import Path
import numpy as np, pandas as pd, requests

BASE = "https://api.openf1.org/v1/"
RAIZ = Path(__file__).resolve().parent.parent


def get(endpoint, **params):
    for i in range(8):
        r = requests.get(BASE + endpoint, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"fallo {endpoint} {params}")


def ts(s):
    return pd.Timestamp(s).value / 1e6   # ms


def procesar(laps, rc, wx):
    por_vuelta = {}
    for l in laps:
        if l.get("date_start"):
            por_vuelta.setdefault(l["lap_number"], []).append(ts(l["date_start"]))
    max_lap = max(l["lap_number"] for l in laps)
    durs = sorted(l["lap_duration"] for l in laps if l.get("lap_duration") and l["lap_number"] > 1)
    med = durs[len(durs) // 2] * 1000
    inicio = {k: min(v) for k, v in por_vuelta.items()}
    if 1 not in inicio:
        inicio[1] = inicio[2] - 1.3 * med
    for L in range(2, max_lap + 1):
        inicio.setdefault(L, inicio[L - 1] + med)
    fin = inicio[max_lap] + med
    ints, vs, ss, rs = [], None, None, None
    for m in sorted(rc, key=lambda m: ts(m["date"])):
        t = ts(m["date"]); msg = (m.get("message") or "").upper().strip()
        if "VIRTUAL SAFETY CAR DEPLOYED" in msg:
            vs = t
        elif "VIRTUAL SAFETY CAR ENDING" in msg:
            if vs is not None: ints.append((vs, t, 1)); vs = None
        elif msg == "SAFETY CAR DEPLOYED":
            if vs is not None: ints.append((vs, t, 1)); vs = None
            ss = t
        elif "SAFETY CAR IN THIS LAP" in msg:
            if ss is not None: ints.append((ss, t, 2)); ss = None
        elif m.get("flag") == "RED" or msg == "RED FLAG":
            if vs is not None: ints.append((vs, t, 1)); vs = None
            if ss is not None: ints.append((ss, t, 2)); ss = None
            if rs is None: rs = t
        elif rs is not None and (msg.startswith("GREEN LIGHT") or (m.get("category") == "SessionStatus" and "STARTED" in msg)):
            ints.append((rs, t, 3)); rs = None
    for v, c in ((vs, 1), (ss, 2), (rs, 3)):
        if v is not None: ints.append((v, fin, c))
    amarillas = [ts(m["date"]) for m in rc if m.get("flag") in ("YELLOW", "DOUBLE YELLOW")]
    w = sorted(({"t": ts(x["date"]), "r": x["rainfall"]} for x in wx), key=lambda x: x["t"])
    filas = []
    for L in range(1, max_lap + 1):
        w0 = inicio[L]; w1 = inicio[L + 1] if L < max_lap else fin
        n = max([c for a, b, c in ints if a < w1 and b > w0], default=0)
        y = int(any(w0 <= t < w1 for t in amarillas))
        s = [x for x in w if w0 <= x["t"] < w1]
        if not s:
            antes = [x for x in w if x["t"] < w0]; s = [antes[-1]] if antes else [w[0]]
        f = np.mean([x["r"] for x in s])
        filas.append((L, 0 if f == 0 else (1 if f < 1 else 2), y, n))
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anios", nargs="+", type=int, default=[2023, 2024, 2025])
    ap.add_argument("--salida", default=str(RAIZ / "datos" / "openf1_secuencias_vuelta.csv"))
    a = ap.parse_args()
    filas = []
    for anio in a.anios:
        for s in get("sessions", year=anio, session_name="Race"):
            k = s["session_key"]
            try:
                laps = get("laps", session_key=k); time.sleep(1)
                rc = get("race_control", session_key=k); time.sleep(1)
                wx = get("weather", session_key=k); time.sleep(1)
                for L, ll, y, n in procesar(laps, rc, wx):
                    filas.append((k, anio, s["circuit_short_name"], s["date_start"][:10], L, ll, y, n))
                print("ok", anio, s["circuit_short_name"])
            except Exception as e:
                print("FALLO", anio, s["circuit_short_name"], e, file=sys.stderr)
    pd.DataFrame(filas, columns=["session_key", "anio", "circuito", "fecha", "vuelta", "lluvia", "amarilla", "neutralizacion"]) \
        .to_csv(a.salida, index=False)


if __name__ == "__main__":
    main()
