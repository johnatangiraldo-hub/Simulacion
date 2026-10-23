# Modificaciones y aportes sobre el notebook guía

- **Base:** `simulacion_01.ipynb` (notebook entregado por el profesor, sin cambios).
- **Versión mejorada:** `simulacion_01_mejorado.ipynb`.

Cada cambio está marcado en el código con `# [MODIFICA Mx]` o `# [CREA Cx]`.

## USA: lo que se encontró al ejecutar la guía

| # | Problema | Evidencia |
|---|---|---|
| 1 | `SIMS_PER_MASK` no se aplicaba: el valor por defecto quedaba fijo en 300 al definir la función. | La tabla de la guía muestra ~5 s para 10, 1.000 y 100.000 simulaciones. |
| 2 | En el último lanzamiento la simulación usaba 0 tiradas, todas las máscaras valían igual y se elegía la que no conserva nada. | En 30 partidas la IA relanzó los 5 dados en **732 de 732** últimos lanzamientos. |
| 3 | `GameStats` sumaba los 5 dados en cada lanzamiento, incluidos los bloqueados. | La guía registra ~374 dados por partida (5 por cada lanzamiento); la versión corregida registra ~255, que son los realmente lanzados. |
| 4 | El diagrama tenía una arista hacia un nodo inexistente (`mejor_mask_decision`). | Aparecía un nodo suelto. |
| 5 | La convergencia se comparaba contra la última estimación. | No demuestra convergencia hacia un valor real. |
| 6 | La celda de análisis volvía a copiar todo el motor del juego. | ~200 líneas duplicadas. |

## MODIFICA: correcciones

| Id | Cambio |
|---|---|
| M1, M4 | `roll_dice` devuelve los dados lanzados y `GameStats` solo cuenta esos. |
| M2 | Caché (`lru_cache`) del puntaje: solo existen 252 combinaciones distintas de 5 dados. |
| M5 | `sims_per_mask=None` → se usa el `SIMS_PER_MASK` vigente al decidir. |
| M6 | La simulación incluye el lanzamiento que se va a hacer (antes `rolls_remaining - 1`). Los lanzamientos posteriores conservan el valor más repetido. |
| M7 | Las máscaras que conservan los mismos valores se evalúan una sola vez. |
| M8 | `play_game(quiet=True)` para simular muchas partidas sin imprimir. |
| M9 | Escenarios 10, 100 y 1.000 (100.000 tardaría horas), con 10 partidas por escenario. |
| M10 | `sns.barplot(..., hue=..., legend=False)` para quitar la advertencia de seaborn. |
| M11 | Diagrama sin la arista errónea; si Graphviz no está instalado, el notebook continúa. |
| M12 | La convergencia se compara contra el valor exacto. |
| M13 | El análisis reutiliza el motor de la sección 1 (sin código duplicado). |

## CREA: aportes nuevos

| Id | Aporte |
|---|---|
| C0 | Todos los gráficos se guardan en `resultados/`. |
| C1 | Puntaje promedio con IC 95 % por escenario de `SIMS_PER_MASK`. |
| C2 | Valor esperado exacto por enumeración y gráfico del error frente a 1/√n. |
| C3 | Ley de los Grandes Números con 1.000.000 de dados: frecuencias, promedio, error y chi-cuadrado (también repetido en 200 muestras). |
| C4 | Probabilidad de cada combinación: simulada vs exacta (7.776 casos). |
| C5 | 200 partidas completas: distribución de puntajes, promedio acumulado y porcentaje de victorias acumulado. |

## Impacto (30 partidas, semilla 42, 300 simulaciones por máscara)

| Indicador | Guía | Mejorado |
|---|---|---|
| Puntaje promedio por jugador | 129,4 ± 8,0 | **207,9 ± 8,5** |
| Último lanzamiento con los 5 dados relanzados | 100 % | 2 % |
| Tiempo por partida | 2,88 s | 1,60 s |
