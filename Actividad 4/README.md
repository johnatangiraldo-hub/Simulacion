# Actividad 2-M4 · Solución de un problema de parqueaderos (simulación de colas)

**Grupo 15:** Luis Miguel Vargas Guevara · Johnatan Giraldo Cardona · Nicolas Mateo Chavez Garcia
**Docente:** Julian Andres Loaiza Lopez · Simulación (PREICA2602B020045) · IU Digital de Antioquia

## Problema

En cada salida del centro comercial **Supercentro** hay **3 cajeros de pago** del parqueadero, cada uno con su propia fila, sin cambio de fila ni abandono. El cajero responde de inmediato; lo que varía es lo que tarda cada usuario en digitar la placa y pagar:

| Tipo | Proporción | Uso del servicio (media, min) | Llegada (media, min) |
|---|---|---|---|
| Rápido | 25 % | 1 | 3 |
| Normal | 20 % | 3 | 3 |
| Lento | 27,5 %* | 4 | 5 |
| Muy lento | 27,5 %* | 6 | 7 |

\* El enunciado solo indica que el 55 % restante son lentos o muy lentos. El grupo lo repartió por partes iguales y verificó que la decisión no cambia con 35/20 ni con 20/35.

**Pregunta:** ¿bastan 3 cajeros o hay que instalar más?

## Respuesta corta

- **Con 3 cajeros no basta:** cada cajero está ocupado el **77 %** del tiempo y, en estado estable, un usuario espera **13,9 min** en promedio. El **45 %** espera más de 10 minutos.
- **Recomendación:** pasar a **4 cajeros con una pantalla que indique la fila más corta**. La espera baja a **1,2 min** y solo el **3,4 %** espera más de 10 minutos.
- **Mejora sin inversión:** si no se pueden instalar cajeros todavía, la **pantalla de fila más corta** o una **fila única** bajan la espera a **4,7 min** y **3,8 min** respectivamente, pero no cumplen el criterio completo del grupo.

## Metodología USA → MODIFICA → CREA

El modelo **reutiliza (USA)** el simulador de colas de la Actividad 3, lo **adapta (MODIFICA)** al parqueadero y **agrega (CREA)** el análisis de estado estable, la verificación y validación, y las estrategias. Detalle completo en [`MODIFICACIONES.md`](MODIFICACIONES.md).

## Estructura

```
Actividad 4/
├── simulacion_parqueadero.py   # Modelo: usuarios, cajeros, reglas de asignación y réplicas
├── analisis_parqueadero.py     # Welch, réplicas, puntos 1-5, verificación/validación, figuras, Excel
├── tests/test_simulacion.py    # Pruebas de verificación (6 pruebas)
├── requirements.txt
├── MODIFICACIONES.md           # USA → MODIFICA → CREA
├── resultados/                 # CSV, estadisticos.json, Resultados_parqueadero.xlsx, traza
├── figuras/                    # 8 figuras (fig1 … fig8)
└── entrega/                    # Documento, presentación
```

## Cómo ejecutarlo (Python ≥ 3.9)

```bash
cd "Actividad 4"
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v     # 6 pruebas → OK
python analisis_parqueadero.py              # ~15 s: genera resultados/ y figuras/
```

Todo es reproducible con la semilla `20261128`. Al ejecutarlo de nuevo se obtienen exactamente los mismos números.

## Resultados por punto del enunciado

| Punto | Resultado | Evidencia |
|---|---|---|
| Estado estable | Con el método de Welch (100 réplicas, ventanas de 10 min, media móvil de ±1 h), el transitorio termina en el **minuto 220** | `figuras/fig1_welch_estado_estable.png` |
| Réplicas | La técnica de la media con un piloto de 10 réplicas pide **44**; se usaron **100** (IC 95 % de ±8 % de la media) | `fig2_replicas_tecnica_media.png` |
| 1. Cajeros | **C3** tiene el menor tiempo de atención (**3,58 min**) y **C1** el mayor (**3,60 min**). La diferencia **no es significativa** (ANOVA p = 0,94; Kruskal-Wallis p = 0,86) | `fig3_punto1_cajeros.png`, `resultados/punto1_cajeros.csv` |
| 2. Usuarios por tipo | Por día, entre los 3 cajeros: **116,2 rápidos, 92,1 normales, 127,7 lentos y 128,0 muy lentos** (463,9 en total, frente a 464,5 teóricos) | `fig4_punto2_usuarios_tipo.png` |
| 3. Estrategia | Criterio del grupo: espera media ≤ 5 min, ≤ 10 % esperando más de 10 min y utilización ≤ 80 %. Solo lo cumple **4 cajeros + fila más corta** | `fig5_punto3_estrategias.png` |
| 4. Verificación, calibración y validación | Verificación con M/M/1 puro: error **< 1 %**. Calibración: χ² p = 0,87 y KS p > 0,05 en los 4 tipos. Validación: corrida larga **15,7 min**, frente a 15,6 de Pollaczek-Khinchine; ley de Little con error de 1 % | `fig6_proceso_vv.png`, `fig7_resultados_vv.png` |
| 5. Transitorio | Al eliminar los primeros 220 min, la espera media pasa de **12,8** a **13,9 min**: el arranque vacío subestimaba la espera un 8 % | `fig8_antes_despues_transitorio.png` |

## Supuestos y limitaciones

- Jornada de 12 h (720 min) que inicia sin usuarios. Se estudia el estado estable dentro de la jornada.
- Las llegadas usan la media del tipo del usuario que llega, igual que en la Actividad 3. Por eso cada cajero no es un M/M/1 exacto: el M/M/1 puro se usa para verificar el motor.
- No se consideran costos de los cajeros ni variación de la demanda por hora.
- En corridas muy largas (200 h), la espera estable es mayor (15,7 min) que dentro de la jornada (13,9 min), porque una cola tan cargada tarda en llegar a su régimen permanente. La conclusión no cambia.

## Declaración de uso de IA

El código, el análisis y los borradores se elaboraron con asistencia de Claude (Anthropic). El equipo revisó los supuestos, ejecutó el código y es responsable de las decisiones y conclusiones.
