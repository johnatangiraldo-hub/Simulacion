# Guion para la sustentación del problema bancario

Duración sugerida: **4 a 5 minutos**. Grabar la pantalla del informe y del programa, con explicación propia. El video definitivo debe ser grabado y publicado por el estudiante antes de enviar la actividad.

| Tiempo | Pantalla sugerida | Qué explicar |
|:--|:--|:--|
| 0:00–0:35 | Portada y pregunta | «El banco tiene tres cajas y quiere distribuirlas entre retiros y pagos. El 70 % de clientes retira y el 30 % paga. Simulé 30 jornadas de ocho horas por configuración para comparar la espera real de los clientes». |
| 0:35–1:15 | Metodología, tablas 1 y 2 | «El tipo de operación y de usuario se sortean con las probabilidades indicadas. Los intervalos de llegada y los servicios son exponenciales con las medias de cada fila. Cada caja dispone de una cola propia, se atiende en orden de llegada y la selección busca la menor cola compatible». |
| 1:15–1:45 | Código y carpeta resultados | «Las réplicas usan semillas independientes. En una misma réplica todas las configuraciones reciben exactamente los mismos usuarios y servicios. Se aceptan llegadas hasta el minuto 480 y se termina de atender a los clientes que ya llegaron. Por ello puedo medir tanto la espera completa como los pendientes al cierre». Mostrar `python -m unittest discover -s tests -v` y `python simulacion_bancaria.py --replicas 30 --semilla 20261122 --salida resultados` si hay tiempo; evitar repetir la simulación sobre la carpeta de evidencias durante el video si no es necesario. |
| 1:45–2:20 | Tabla y figura comparativa del informe | «Las tres cajas mixtas tuvieron 0,62 minutos de espera media. Con exclusividad, una caja de retiros y dos de pagos: 5,10 minutos; dos de retiros y una de pagos: 2,72 minutos. La diferencia emparejada es de 2,38 minutos, con intervalo de confianza del 95 % entre 1,39 y 3,36». |
| 2:20–2:55 | Cajeros, demanda y anexo | «Entre las tres cajas mixtas, C3 registró el menor servicio medio, 3,13 minutos, y C1 el mayor, 3,39. Eso no significa que uno sea mejor empleado, porque todos tienen la misma distribución de servicio por clase. Llegaron en promedio 38,17 usuarios rápidos, 68,60 normales, 43,73 lentos y 52,23 muy lentos. La réplica 24 tuvo menos usuarios en total, 182». Mostrar que el Excel contiene los ocho subtipos por cada réplica. |
| 2:55–3:35 | Análisis de cuarta caja | «Con tres cajas mixtas los retiros esperaron 0,69 minutos y los pagos 0,47; no hay necesidad demostrada de una cuarta caja para el objetivo propuesto de menos de cinco minutos de espera media por operación. Cuatro mixtas bajan la espera global a 0,12, pero falta el costo para justificar la inversión. Si el banco requiere exclusividad y ese mismo objetivo, cuatro cajas repartidas dos y dos dejan 0,54 y 0,59 minutos de espera para retiros y pagos». |
| 3:35–4:15 | Conclusión y limitaciones | «Recomiendo conservar las tres cajas mixtas. Si debo elegir solo entre las dos distribuciones exclusivas de tres cajas, elijo dos para retiros y una para pagos, advirtiendo que los pagos esperan 7,92 minutos. Una caja electrónica no puede evaluarse sin datos de capacidad, servicio y costo. La mezcla de tipos impide considerar al sistema agregado una M/M/1 homogénea exacta; por eso comparé corridas simuladas y no solo fórmulas estacionarias». |

## Antes de entregar

1. Abrir el Word y el Excel, y mostrar resultados de una réplica y de las 30 jornadas.
2. Grabar con voz audible y el tiempo permitido por el docente; comprobar que el enlace del video abre para el evaluador.
3. Crear un repositorio nuevo, subir el proyecto completo y pegar su enlace en el Word y en la plataforma.
4. Sustituir el apellido en el nombre del informe si aún aparece como `Apellido`.
