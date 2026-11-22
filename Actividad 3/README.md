# Problema bancario: simulación de cajas

Proyecto académico reproducible para decidir cómo asignar tres cajas a retiros y pagos durante una jornada de 480 minutos. La entrega incluye código, 30 días simulados por escenario, datos por cliente, tablas de resumen, informe y material para la sustentación.

## Pregunta y respuesta principal

El banco recibe aproximadamente 70 % de retiros y 30 % de pagos. Con los supuestos de las tablas suministradas, la comparación principal de **30 días independientes** indica que las **tres cajas mixtas** ofrecen menor espera global. Si las cajas deben ser exclusivas, la opción de **dos cajas para retiros y una para pagos** supera a la opción inversa en espera global. Para lograr esperas medias bajas en *ambas* operaciones bajo exclusividad, conviene evaluar una **cuarta caja: dos para cada operación**. No hay evidencia para recomendar una caja electrónica específica sin datos sobre su velocidad, costo y qué operaciones admite.

## Ejecutar desde la carpeta del proyecto

Requiere Python 3.10 o posterior. En Windows, sustituir `python` por `py` cuando sea necesario.

```bash
python -m venv .venv
```

Activar entorno: Windows PowerShell `.\.venv\Scripts\Activate.ps1`; macOS y Linux `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python simulacion_bancaria.py --replicas 30 --semilla 20261122 --modo condicional --salida resultados
python analisis_figuras.py --resultados resultados --figuras entrega/figuras
python generar_informe_apa.py --resultados resultados --destino entrega
```

Los CSV originales y `configuracion.json` están incluidos en `resultados/`; ejecutar con la misma semilla los reproduce. Las figuras (`entrega/figuras/`) y el informe `entrega/Grupo_15_EA3.docx` se regeneran con `analisis_figuras.py` y `generar_informe_apa.py`. El archivo `entrega/Resultados_problema_bancario.xlsx` es una vista organizada de las tablas de las corridas.

## Entradas tomadas del enunciado

| Acción | Tipo | Probabilidad condicional | Servicio medio (min) | Entrellegada media condicional (min) |
|:--|:--|--:|--:|--:|
| Retiro | Rápido | 0,23 | 1 | 1 |
| Retiro | Normal | 0,40 | 2 | 2 |
| Retiro | Lento | 0,17 | 3 | 3 |
| Retiro | Muy lento | 0,20 | 4 | 3 |
| Pago | Rápido | 0,10 | 3 | 1 |
| Pago | Normal | 0,20 | 3 | 2 |
| Pago | Lento | 0,30 | 5 | 3 |
| Pago | Muy lento | 0,40 | 7 | 4 |

Primero se sortea retiro con probabilidad 0,70 y pago con 0,30. Después se sortea el tipo según las probabilidades *dentro* de la operación. Antes de generar cada llegada se utiliza una exponencial con la media de la tabla 1 correspondiente al usuario que viene; su servicio es una exponencial con la media de esa misma fila. La media ponderada entre llegadas es 2,398 minutos y la tasa aproximada de llegadas es 1/2,398 usuarios/minuto. Las muestras exponenciales se parametrizan por **media en minutos**, no por tasa. Los cajeros tienen idénticos parámetros de servicio para una clase dada y no se agregan tiempos de desplazamiento.

### Precisión sobre M/M/1

Cada caja es un servidor con su propia cola FIFO. Las tablas no permiten afirmar que cada caja agregada cumpla **exactamente** M/M/1: al mezclar tipos, los servicios tienen varias medias exponenciales; además, en el modo principal las entrellegadas dependen del tipo del próximo usuario. Se simulan explícitamente esos datos mediante eventos por cliente, sin aplicar las fórmulas estacionarias de M/M/1 como si fueran exactas. `--modo poisson` genera llegadas Poisson de media ponderada 2,398 minutos como comprobación alternativa: mantiene las proporciones pero reemplaza las ocho medias de entrellegada condicionales por una sola media. Una M/M/1 exacta exigiría una única exponencial de servicio por caja, incompatible con los ocho servicios medios dados. Esta limitación debe comunicarse en la sustentación.

## Reglas y escenarios

| Código | Cajas | Finalidad |
|:--|:--|:--|
| A_3_mixtas | Mixta, mixta, mixta | Referencia actual |
| B_1R_2P | Retiro, pago, pago | Alternativa exclusiva 1 |
| C_2R_1P | Retiro, retiro, pago | Alternativa exclusiva 2 |
| D_4_mixtas | Cuatro mixtas | Caja adicional flexible |
| E_2R_2P | Retiro, retiro, pago, pago | Caja adicional exclusiva equilibrada |
| F_1R_3P | Retiro y tres pagos | Sensibilidad para cuatro exclusivas |
| G_3R_1P | Tres retiros y un pago | Sensibilidad para cuatro exclusivas |

Una llegada se asigna a la caja compatible con menor cantidad de trabajos pendientes. Si hay empate, se usa el final de su agenda y un desempate rotativo. Las colas son **independientes**; no se cambia de caja después de entrar. Cada escenario recibe exactamente los mismos clientes y tiempos de servicio dentro de cada réplica (números aleatorios comunes). Las 30 réplicas usan semillas distintas. Se reciben clientes hasta el minuto 480; los que ya llegaron terminan después del cierre. Así se miden la espera completa y las tareas pendientes al cierre sin abandonar arbitrariamente clientes. La primera llegada se produce tras un intervalo, con el sistema vacío al abrir; los días se reinician vacíos.

## Métricas y archivos

`espera = inicio − llegada`; `servicio = fin − inicio`; `sistema = fin − llegada`. Todas las medias de espera se calculan **sobre los usuarios llegados antes del cierre**, incluidos los que terminan después. `pendientes_al_cierre` cuenta los que no terminaron antes de 480. `utilizacion_horario` cuenta solo el tiempo de servicio transcurrido entre 0 y 480, dividido por 480. `Lq_durante_horario` es el área bajo la cantidad de personas en espera dentro de la jornada, dividida por 480; los tiempos de espera fuera del horario no están en su numerador. `espera_p95` es el percentil 95 de espera por cliente dentro de una réplica. Los promedios finales son promedios entre réplicas, y los IC del 95 % se obtienen de los 30 valores diarios usando t de Student; las diferencias entre escenarios usan las diferencias emparejadas de un mismo día.

- `resultados/demanda_por_replica.csv`: ocho combinaciones y cuatro tipos agregados para cada día.
- `resultados/escenarios_por_replica.csv`: indicadores de los siete escenarios en cada réplica.
- `resultados/cajeros_por_replica.csv`: carga, tiempo de servicio, espera y ocupación de cada caja.
- `resultados/tipos_por_replica.csv`: desglose por operación y tipo.
- `resultados/clientes_detalle.csv`: trazabilidad de las operaciones y tiempos por cliente y caja.
- `resultados/configuracion.json`: parámetros de la corrida entregada.
- `entrega/`: informe Word `Grupo_15_EA3.docx`, figuras (`entrega/figuras/`), Excel de resultados y guion de sustentación.

Los conteos de llegadas por tipo son iguales en todos los escenarios comparados de una misma réplica. Menos llegadas no indica mejor servicio: por esa razón el informe identifica los mínimos *por réplica* y compara los modelos con esperas y pendientes, no con demanda artificialmente reducida.

## Módulos de la entrega

- `simulacion_bancaria.py`: modelo de eventos discretos, réplicas y CSV de resultados.
- `analisis_figuras.py`: estadísticos (IC 95 %, diferencias emparejadas, ANOVA entre cajas, ρ teórica y observada, ley de Little, réplicas necesarias, lectura alternativa del punto 3) y las 8 figuras.
- `generar_informe_apa.py`: informe Word en formato APA 7.ª edición del Grupo 15.
- `tests/test_simulacion.py`: pruebas unitarias (`python -m unittest discover -s tests -v`).
