# USA → MODIFICA → CREA · Actividad 2-M4 (problema de parqueaderos)

Esta actividad **no parte de cero**. Toma como base el modelo de colas de la **Actividad 3** (`Actividad 3/simulacion_bancaria.py`, problema bancario) y las lecciones de las Actividades 1 y 2. En el código, cada línea relevante está marcada con `[USA]`, `[MODIFICA Mx]` o `[CREA Cx]`.

## USA: lo que se reutilizó

| De dónde | Qué se reutilizó | Dónde quedó |
|---|---|---|
| Actividad 3 · `simulacion_bancaria.py` | Clase de cliente (`Cliente` → `Usuario`) | `simulacion_parqueadero.py` |
| Actividad 3 | Generación de llegadas **condicionadas al tipo**: el intervalo usa la media del tipo del usuario que llega | `generar_usuarios()` |
| Actividad 3 | Semillas independientes por réplica y flujo (`SeedSequence`) | `generar_usuarios()` |
| Actividad 3 | **Números aleatorios comunes**: todos los escenarios reciben los mismos usuarios | `correr_replicas()` |
| Actividad 3 | Cola FIFO por cajero e instante de liberación del servidor | `simular()` |
| Actividad 3 | IC 95 % con t de Student, ANOVA entre cajeros, ley de Little | `analisis_parqueadero.py` |
| Actividad 3 | Estructura de pruebas unitarias | `tests/test_simulacion.py` |
| Actividad 1 | Ley de los Grandes Números: el error baja como 1/√n | Técnica de la media (número de réplicas) |
| Actividad 2 | Comparar contra un valor teórico conocido, no contra la propia simulación | Verificación y validación |

## MODIFICA: lo que se adaptó al parqueadero

| Id | Antes (banco) | Ahora (parqueadero) | Por qué |
|---|---|---|---|
| M1 | Jornada de 480 min | Jornada de **720 min** (10:00–22:00) | Horario típico de un centro comercial |
| M2 | Dos operaciones (retiro 70 %, pago 30 %) con 8 combinaciones | **Una operación** (pago) y **4 tipos**: 25 % rápidos, 20 % normales, **27,5 % lentos, 27,5 % muy lentos** | El enunciado no reparte el 55 % restante; el grupo asumió partes iguales y lo prueba con sensibilidad (C7) |
| M3 | Media ponderada de llegadas | También **ρ** y segundos momentos E[S²] y E[A²] | Para validar con Pollaczek-Khinchine y Kingman |
| M4 | Un flujo de clientes que elige la caja con menos fila | **Un flujo independiente por cajero** | El enunciado pide filas independientes y cajeros M/M/1 |
| M5 | Pruebas del banco | Pruebas del parqueadero (traza manual, fila única, filas independientes) | Verificación del nuevo modelo |
| M6 | Interés en usuarios pendientes al cierre | Interés en el **estado estable** | Lo exige el enunciado |

## CREA: lo nuevo de esta actividad

| Id | Aporte | Punto del enunciado |
|---|---|---|
| C1 | Estrategias: **más cajeros**, **pantalla de fila más corta**, **fila única**, con un criterio de decisión del grupo | Punto 3 |
| C2 | Modo **M/M/1 puro** para verificar el motor contra fórmulas exactas | Punto 4 |
| C3 | **Método de Welch**: promedio por ventana de 10 min en 100 réplicas, media móvil de ±1 h y regla automática para el fin del transitorio (banda de ±10 %) | Estado estable |
| C4 | **Técnica de la media**: media acumulada, IC 95 % y réplicas requeridas desde un piloto de 10 | Número de réplicas |
| C5 | Módulo de **verificación, calibración y validación**, con su diagrama y corridas largas de 200 h | Punto 4 |
| C6 | Algoritmo que **elimina el transitorio** y comparación antes / después | Punto 5 |
| C7 | **Sensibilidad** al reparto de lentos y muy lentos (35/20 y 20/35) | Robustez de la decisión |
| C8 | Excel de resultados y traza de los primeros usuarios | Evidencias |

## Resultado de las modificaciones

| Indicador | Valor |
|---|---|
| Fin del estado transitorio (Welch) | **220 min** |
| Réplicas requeridas / usadas | 44 / **100** (precisión lograda: 8 %) |
| Espera media actual, 3 cajeros (sin transitorio) | **13,9 min** |
| Verificación M/M/1 (error frente a la fórmula exacta) | **< 1 %** |
| Estrategia recomendada | **4 cajeros + pantalla de fila más corta → 1,2 min** |
