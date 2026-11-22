# Informe de reproducción

**Responsable:** Johnatan Giraldo Cardona · **Fecha:** 15 de noviembre de 2026 · **Rama:** `feature/ActividadM2`

**Objetivo:** ejecutar los comandos del `README.md` en un computador distinto al de desarrollo, comparar los resultados con los entregados y verificar `src/descargar_datos.py`.

> **Uso de IA.** La comparación numérica, el script `tests/comparar_resultados.py` y la redacción de este informe se hicieron con asistencia de Claude (Anthropic). Las ejecuciones en macOS las hizo el integrante en su computador.

## 1. Entornos

| | Entorno de desarrollo (entrega) | Reproducción en Mac (este informe) | Verificación adicional |
|---|---|---|---|
| Sistema | — | macOS, Intel x86_64 | Linux (contenedor) |
| Python | 3.13.18 | **3.9** (el README pide ≥ 3.10) | 3.13.16 |
| NumPy / SciPy | 2.5.3 / 1.18.1 | 2.0.2 / 1.13.1 | 2.5.3 / 1.18.1 |
| pandas / matplotlib | 3.0.5 / 3.11.2 | 2.3.3 / 3.9.4 | 3.0.5 / 3.11.2 |
| hmmlearn | — | 0.3.3 | 0.3.3 |

El código **funciona con Python 3.9**: no usa sintaxis exclusiva de 3.10+. Solo aparece una advertencia inofensiva de `urllib3` sobre LibreSSL al descargar datos.

## 2. Resultados de la reproducción

| Paso del README | Mac (Python 3.9) | Verificación adicional (Linux, Python 3.13) |
|---|---|---|
| `tests/contraste_hmmlearn.py` | ✅ "OK: la implementación propia coincide con hmmlearn" | ✅ OK |
| `src/validacion_real.py` | ✅ 8 min 09 s · 7 archivos: 3 idénticos, 4 equivalentes (ver abajo) | ✅ 7 min 22 s · 7 archivos idénticos byte a byte |
| `src/experimentos.py` | No se repitió en Mac (≈13–20 min) | ✅ 12 min 54 s · 10 archivos idénticos byte a byte; mismo hash SHA-256 `6d5daf53…` |
| `src/figuras.py`, `src/generar_tablas.py` | ✅ Las 6 tablas LaTeX generadas con los resultados del Mac son **idénticas** | ✅ 6 tablas idénticas |

**Diferencias en Mac (`validacion_real.py`).** Con NumPy 2.0.2 aparecen diferencias de redondeo de punto flotante:

| Archivo | Diferencia máxima | Efecto |
|---|---|---|
| `parametros_estimados.json` | 1,1 × 10⁻¹⁶ | Ninguno (precisión de máquina) |
| `predicciones_cv.csv` | 1,7 × 10⁻¹⁶ | Ninguno |
| `metricas_prediccion.csv` | 3,8 × 10⁻⁵ (AUC 0,62756 vs 0,62752) | Ninguno a 3 decimales |
| `estabilidad_particiones.csv` | 2,9 × 10⁻⁴ | Ninguno a 3 decimales |

El log impreso (`log_validacion_real.txt`, a 3 decimales) y las 6 tablas del artículo son **idénticos**.

**Conclusión:** los resultados del artículo **se reproducen** en un computador y un entorno distintos. Con las mismas versiones de librerías, la reproducción es exacta bit a bit. Con versiones anteriores, solo cambian cifras más allá del tercer decimal.

## 3. Verificación de `src/descargar_datos.py` (API OpenF1)

Comando ejecutado (con `--salida` para **no sobrescribir** los datos entregados):

```bash
python src/descargar_datos.py --salida datos/openf1_descarga_verificacion.csv   # 8 min 15 s
python tests/comparar_resultados.py --datos datos/openf1_descarga_verificacion.csv
```

- **Carreras descargadas:** 68 de 70.
  - *Imola 2023* falla, y es esperado: la carrera se canceló.
  - *Miami 2025* falla con `KeyError: 2` en `procesar()`: la API no trae `date_start` para las vueltas 1 y 2, y el script no contempla ese caso.
- **Comparación** (4.173 vueltas en común):

| Variable | Vueltas distintas |
|---|---|
| `lluvia` | **0** (0,00 %) |
| `amarilla` | 4 (0,10 %) |
| `neutralizacion` | 2 (0,05 %) |

- **66 carreras coinciden exactamente.** Las diferencias se concentran en 3 carreras de 2025:

| Carrera | Archivo entregado | Descarga en Python | Observación |
|---|---|---|---|
| Imola 2025 | 64 vueltas | 63 vueltas | La carrera real tuvo 63. Desfase de una vuelta en el periodo de Safety Car (vueltas 46–54): 6 celdas distintas |
| Abu Dhabi 2025 | 75 vueltas | 58 vueltas | La carrera real tuvo 58. El archivo entregado tiene **17 vueltas de más** |
| Miami 2025 | 57 vueltas | — | No se pudo descargar (error del script) |

**Conclusión:** el script en Python reproduce la lógica de la versión en JavaScript. En 2 carreras de 2025 produce un número de vueltas **más consistente con la duración real** que el archivo entregado. Las 18 vueltas sobrantes son el 0,4 % de las 4.248 vueltas.

## 4. Recomendaciones para el equipo

1. Revisar Imola y Abu Dhabi 2025 en `datos/openf1_secuencias_vuelta.csv`. Estimamos que el impacto en los resultados es bajo (0,4 % de las vueltas), pero no se recalculó.
2. Hacer `procesar()` robusto cuando faltan los tiempos de las primeras vueltas (Miami 2025).
3. Documentación corregida en este commit:
   - El README advertía mal sobre la descarga: ejecutarla sin `--salida` sobrescribe los datos entregados.
   - El script mencionaba una opción `--comparar` que no existe.
4. Ajustar el requisito de Python en el README: el código funciona desde 3.9.

## 5. Archivos agregados en esta verificación

- `tests/comparar_resultados.py`: compara `resultados/` con el último commit y una descarga nueva con los datos entregados. Distingue IDÉNTICO (< 1e-9) de EQUIVALENTE (< 1e-3).
- `datos/openf1_descarga_verificacion.csv`: evidencia de la descarga hecha en esta verificación.
- `REPRODUCCION.md`: este informe.
