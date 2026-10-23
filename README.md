# Simulación

Repositorio de las actividades de la materia **Simulación**.
**Autor:** Johnatan Giraldo Cardona

| Actividad | Tema | Carpeta |
|---|---|---|
| Actividad didáctica 2-M1 | Yahtzee con el método de Montecarlo | [`Actividad 1/`](Actividad%201/) |

Cada entrega se trabaja en su propia rama (`feature/ActividadM1`, …).

---

# 🎲 Actividad 2-M1: Yahtzee con el método de Montecarlo

Simulación del **Yahtzee clásico con 2 jugadores**: hasta 3 lanzamientos de 5 dados por turno, bloqueo de dados entre lanzamientos y 13 categorías de puntuación. Cada dado sigue una **distribución uniforme discreta**, P(X = k) = 1/6.

El trabajo parte del **notebook guía del profesor** y sigue la metodología **USA → MODIFICA → CREA**:

| Etapa | Qué se hizo |
|---|---|
| **USA** | Se ejecutó la guía y se encontraron 3 errores que invalidaban los resultados. |
| **MODIFICA** | Se corrigieron los errores y se mejoró el rendimiento y la robustez. El puntaje promedio pasó de **129,4 a 207,9** puntos. |
| **CREA** | Se agregaron experimentos que demuestran la **Ley de los Grandes Números**. |

El detalle de cada cambio está en [`MODIFICACIONES.md`](Actividad%201/MODIFICACIONES.md).

## 📁 Contenido

```
Actividad 1/
├── simulacion_01.ipynb              # Notebook guía original (sin cambios)
├── simulacion_01_mejorado.ipynb     # Versión mejorada, ejecutada con sus salidas
├── MODIFICACIONES.md                # Cambios y aportes, uno por uno
├── Giraldo_Johnatan_Montecarlo.docx # Documento técnico
├── requirements.txt
└── resultados/                      # Gráficos y datos generados por el notebook
```

## ▶️ Cómo ejecutar

```bash
cd "Actividad 1"
pip3 install -r requirements.txt
jupyter notebook simulacion_01_mejorado.ipynb
```

Luego **Run All**. La ejecución completa tarda unos 3–5 minutos.

- **Semilla:** `SEED = 42` hace que los resultados sean reproducibles.
- **Graphviz (opcional):** para el diagrama de flujo, instálalo con `brew install graphviz`. Sin él, el notebook avisa y continúa.

## 🧠 Cómo funciona

- **Dados:** `random.randint(1, 6)` → uniforme discreta, E[X] = 3,5, Var(X) = 35/12.
- **Decisión con Montecarlo:** antes de cada relanzamiento se evalúan las 32 formas de conservar dados. Para cada una se simula `SIMS_PER_MASK` veces el resto del turno y se elige la de mayor valor esperado, `EV ≈ (1/N)·Σ puntajeᵢ`.
- **Estructuras:** `PlayerState` (hoja de 13 categorías), `GameStats` (dados lanzados y frecuencia por cara), `GameState` (turno, dados, bloqueos, lanzamientos restantes).

## 📊 Resultados principales

| Experimento | Resultado |
|---|---|
| Corrección de errores (30 partidas) | Puntaje promedio 129,4 → **207,9** (+61 %) |
| 1.000.000 de dados | Promedio 3,5006 (teórico 3,5) · error máximo 0,064 puntos % · χ² = 5,84 (p = 0,32) |
| Combinaciones (100.000 lanzamientos) | 9 de 9 dentro del IC 95 % de su probabilidad exacta |
| Valor esperado de una decisión | 17,761 estimado vs **17,775 exacto** con 100.000 iteraciones |
| 200 partidas | Promedio 201,5 ± 3,2 pts · victorias J1 47 % (≈ 50 % esperado) |

### Ley de los Grandes Números

![Ley de los Grandes Números en los dados](Actividad%201/resultados/lln_dados.png)

![Montecarlo de partidas](Actividad%201/resultados/montecarlo_partidas.png)

A medida que aumentan las repeticiones, las frecuencias se acercan a 1/6, el promedio a 3,5 y los resultados del juego se estabilizan. El error disminuye en proporción a **1/√n**.

## 📚 Referencias

- Ross, S. M. (2013). *Simulation* (5.ª ed.). Academic Press.
- Law, A. M. (2015). *Simulation Modeling and Analysis* (5.ª ed.). McGraw-Hill.
- Hasbro Gaming. *Yahtzee: reglas oficiales*.
