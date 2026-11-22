# Actividad didáctica 2 (M2) — HMM: neutralizaciones de carrera y lluvia en la Fórmula 1

Grupo 15 · Simulación (PREICA2602B020045) · IU Digital de Antioquia · Docente: Julián Andrés Loaiza López

Modelo Oculto de Markov (HMM) con tres estados (S0 seco estable, S1 régimen de lluvia, S2 neutralización) y seis observaciones
(lluvia 0/1/2 × bandera amarilla 0/1), calibrado y validado con datos reales de OpenF1 (2023-2025) y explorado con simulación Monte Carlo.

> **Declaración de uso de IA.** El código, los análisis y el borrador del artículo de esta carpeta fueron generados con Claude
> (Anthropic) en una conversación previa, **sin la skill `articulo-hmm` cargada**. Las decisiones científicas deben ser revisadas y
> aprobadas por el equipo.

## Estructura
| Ruta | Contenido |
|---|---|
| `src/hmm.py` | Clase HMM propia (NumPy): muestreo, Forward/Backward escalados, Viterbi, Baum-Welch con máscaras |
| `src/modelo_f1.py` | Especificación del modelo (S, V, A₀, B₀, π₀ de arranque) |
| `src/descargar_datos.py` | Reconstruye `datos/openf1_secuencias_vuelta.csv` desde la API OpenF1 |
| `src/validacion_real.py` | Ajuste y validación cruzada por carreras con datos reales |
| `src/experimentos.py` | 3 escenarios Monte Carlo, estadísticos, sensibilidad y reproducibilidad |
| `src/figuras.py`, `src/generar_tablas.py` | Figuras (300 dpi) y tablas LaTeX desde los resultados |
| `tests/contraste_hmmlearn.py` | Contraste de la implementación propia con `hmmlearn` |
| `tests/comparar_resultados.py` | Compara resultados/descarga con la versión entregada (reproducibilidad) |
| `datos/` | Secuencias vuelta a vuelta (70 carreras 2023-2025) |
| `resultados/`, `figuras/` | Salidas crudas y figuras |
| `articulo/` | Artículo en LaTeX (Overleaf) |
| `REPRODUCCION.md` | Verificación de reproducibilidad en un segundo computador y de la descarga de datos |

## Ejecución (Python ≥ 3.9; desarrollado con 3.13)
```bash
python -m venv .venv && source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python tests/contraste_hmmlearn.py          # (opcional) valida la implementación
python src/validacion_real.py               # ~5 min: parámetros estimados + validación cruzada
python src/experimentos.py                  # ~10-15 min: escenarios, sensibilidad, reproducibilidad
python src/figuras.py && python src/generar_tablas.py
```
Opcional: `python src/descargar_datos.py --salida datos/openf1_descarga_verificacion.csv` vuelve a descargar los datos (necesita internet).
⚠️ Sin `--salida` **sobrescribe** `datos/openf1_secuencias_vuelta.csv`. Para compararlos: `python tests/comparar_resultados.py --datos datos/openf1_descarga_verificacion.csv`.
Verificación de reproducibilidad en otro computador: ver [`REPRODUCCION.md`](REPRODUCCION.md).

## Reproducibilidad
- Semilla maestra 42; `numpy.random.SeedSequence.spawn` genera una semilla **independiente por réplica** (no se reutiliza la misma).
- `resultados/reproducibilidad.json`: mismo seed ⇒ mismo hash SHA-256 de resultados; entorno y versiones registrados.
- La partición de la validación cruzada por carreras usa semilla 42 y se repite con 5 semillas más (`estabilidad_particiones.csv`).

## Datos y límites
- Fuente: OpenF1 (https://openf1.org), endpoints `weather`, `race_control`, `laps`. Verifiquen términos de uso antes de redistribuir.
- Imola 2023 se canceló (sin datos). Las neutralizaciones se derivan de mensajes de control de carrera; ver artículo (limitaciones).
