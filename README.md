# Simulación

Repositorio de las actividades de la materia **Simulación**.
Autor: **Johnatan Giraldo Cardona**

| Actividad | Tema | Carpeta |
|---|---|---|
| Actividad didáctica 2-M1 | Yahtzee con el método de Montecarlo | [`Actividad 1/`](Actividad%201/) |

Cada entrega se trabaja en su propia rama (`feature/ActividadM1`, `feature/ActividadM2`, …) y se integra a `main` con un Pull Request.

---

# 🎲 Actividad 2-M1: Yahtzee con el método de Montecarlo

Programa en Python que simula el juego **Yahtzee clásico con 2 jugadores** y usa el **método de Montecarlo** para:

1. Generar los lanzamientos de los dados con **distribución uniforme discreta**.
2. Validar estadísticamente el generador y las probabilidades de cada combinación.
3. Tomar decisiones de juego: un jugador elige qué dados conservar simulando cientos de futuros posibles.
4. Simular miles de partidas y analizar los resultados con tablas y gráficos.

## 📁 Estructura

```
Actividad 1/
├── yahtzee_montecarlo.py            # Código fuente (único archivo, comentado)
├── requirements.txt                 # Dependencia opcional: matplotlib
├── Giraldo_Johnatan_Montecarlo.docx # Documento: introducción, metodología, resultados y conclusiones
├── simulacion_01.ipynb              # Notebook original de referencia
└── resultados/                      # Generados por el programa (semilla 2026)
    ├── salida_consola.txt
    ├── partidas.csv                 # 1.000 partidas: puntos, ganador, Yahtzees
    ├── probabilidades_combinaciones.csv / .png
    ├── distribucion_caras.png
    ├── convergencia_yahtzee.csv / .png
    ├── promedio_categorias.csv / .png
    ├── puntajes_partidas.png
    ├── victorias.png
    └── sensibilidad_sims.csv / .png
```

## ⚙️ Requisitos

- Python 3.9 o superior.
- `matplotlib` para los gráficos (opcional: sin él el programa funciona y omite los PNG).

```bash
pip3 install -r "Actividad 1/requirements.txt"
```

## ▶️ Cómo ejecutar

Desde la carpeta `Actividad 1`:

```bash
cd "Actividad 1"
```

| Comando | Qué hace |
|---|---|
| `python3 yahtzee_montecarlo.py` | Menú interactivo con todas las opciones |
| `python3 yahtzee_montecarlo.py interactivo` | Partida entre **2 personas** por consola |
| `python3 yahtzee_montecarlo.py interactivo --rival ia` | Persona vs IA Montecarlo |
| `python3 yahtzee_montecarlo.py partida` | Una partida narrada IA Montecarlo vs Heurística |
| `python3 yahtzee_montecarlo.py simulacion -n 1000` | 1.000 partidas + estadísticas y gráficos |
| `python3 yahtzee_montecarlo.py probabilidades -n 200000` | Probabilidades simuladas vs teóricas |
| `python3 yahtzee_montecarlo.py convergencia -n 100000` | Convergencia (Ley de los Grandes Números) |
| `python3 yahtzee_montecarlo.py sensibilidad` | Efecto del número de simulaciones por máscara |
| `python3 yahtzee_montecarlo.py todo --semilla 2026` | Reproduce **todos** los resultados del documento (~5 min) |

Opciones: `--semilla N` (reproducibilidad), `--sims N` (simulaciones por máscara de la IA, por defecto 100).

En el modo interactivo se indica qué dados conservar por posición (ej. `1 3 5`), `Enter` para relanzar todos o `p` para plantarse, y luego el número de la categoría donde anotar.

## 🧠 Diseño de la solución

**Variable aleatoria:** valor de un dado, `X ~ Uniforme{1,…,6}`.

```
P(X = k) = 1/6      E[X] = 3,5      Var(X) = 35/12 ≈ 2,917
X = floor(6·U) + 1,   U ~ Uniforme[0, 1)
```

**Reglas:** 13 rondas, hasta 3 lanzamientos por turno, bloqueo de dados entre lanzamientos y 13 categorías (Unos a Seises, Trío, Póker, Full House 25, Escalera Menor 30, Escalera Mayor 40, Yahtzee 50, Chance).

**Estructuras de datos:**

| Estructura | Contenido |
|---|---|
| Dados | 5 valores + 5 indicadores de bloqueo |
| `Jugador` | nombre, estrategia y hoja con 13 categorías |
| `Estadisticas` | dados lanzados, frecuencia por cara, lanzamientos, turnos, Yahtzees |
| `TABLA_PUNTAJES` | puntaje precalculado de las 252 combinaciones posibles |

**Jugadores:**

- **Jugador 1 – Montecarlo:** para cada una de las 32 formas de conservar dados simula N veces el resto del turno y elige la de mayor valor esperado: `EV ≈ (1/N)·Σ puntajeᵢ`.
- **Jugador 2 – Heurística:** conserva el valor más repetido (línea base).
- **Humano:** decide por consola.

## 📊 Resultados principales (semilla 2026)

| Experimento | Resultado |
|---|---|
| Uniformidad (1.000.000 dados) | Media 3,4972 · Varianza 2,9165 · χ² = 4,59 < 11,07 → no se rechaza la uniformidad |
| Combinaciones (200.000 lanzamientos) | Error máximo 0,062 puntos frente a la probabilidad exacta |
| P(Yahtzee en un turno), 100.000 turnos | 4,587 % ± 0,130 % (teórico 4,603 %) |
| 1.000 partidas | Montecarlo 201,97 pts vs Heurística 162,34 pts · Montecarlo gana el 79,5 % |
| Sims por máscara | 5 → 177 pts · 20 → 189 · 100 → 207 · 300 → 207,5 (3× más lento) |

| | |
|---|---|
| ![Distribución de caras](Actividad%201/resultados/distribucion_caras.png) | ![Combinaciones](Actividad%201/resultados/probabilidades_combinaciones.png) |
| ![Convergencia](Actividad%201/resultados/convergencia_yahtzee.png) | ![Puntajes](Actividad%201/resultados/puntajes_partidas.png) |

## ✅ Conclusiones

- La distribución uniforme discreta modela correctamente los dados y el generador pasa la prueba chi-cuadrado.
- La simulación reproduce las probabilidades exactas de cada combinación dentro del intervalo de confianza del 95 %.
- El error de una estimación Montecarlo disminuye en proporción a 1/√n.
- La estrategia influye tanto como el azar: decidir con Montecarlo sube el promedio en ~40 puntos.
- Por encima de ~100 simulaciones por máscara la mejora es despreciable y el tiempo crece linealmente.

## 📚 Referencias

- Hasbro Gaming. *Yahtzee: reglas oficiales*.
- Ross, S. M. (2013). *Simulation* (5.ª ed.). Academic Press.
- Law, A. M. (2015). *Simulation Modeling and Analysis* (5.ª ed.).
