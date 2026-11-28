"""Pruebas de verificación del modelo (Actividad 2-M4).

[USA] Estructura tomada de las pruebas de la Actividad 3.
[MODIFICA M5] Adaptadas a cajeros de parqueadero y a las nuevas reglas de asignación.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulacion_parqueadero import (ESCENARIOS, HORIZONTE, Usuario, generar_usuarios,  # noqa: E402
                                    medias_teoricas, simular)


class PruebasModelo(unittest.TestCase):
    def test_reproducible_con_la_misma_semilla(self):
        self.assertEqual(generar_usuarios(20261128, 3), generar_usuarios(20261128, 3))
        self.assertNotEqual(generar_usuarios(20261128, 3), generar_usuarios(20261128, 4))

    def test_todos_los_escenarios_atienden_la_misma_demanda_en_orden_fifo(self):
        usuarios = generar_usuarios(20261128, 2)
        self.assertTrue(all(0 <= u.llegada < HORIZONTE for u in usuarios))
        for escenario, (cajeros, regla) in ESCENARIOS.items():
            with self.subTest(escenario=escenario):
                regs = simular(usuarios, cajeros, regla)
                self.assertEqual(len(regs), len(usuarios))
                for r, u in zip(regs, usuarios):
                    self.assertEqual(r["servicio"], u.servicio)
                    self.assertGreaterEqual(r["inicio"], r["llegada"])
                    self.assertAlmostEqual(r["fin"] - r["inicio"], r["servicio"])
                for c in {r["cajero"] for r in regs}:  # un cajero no atiende a dos a la vez
                    t = sorted((r for r in regs if r["cajero"] == c), key=lambda r: r["inicio"])
                    self.assertTrue(all(a["fin"] <= b["inicio"] + 1e-9 for a, b in zip(t, t[1:])))

    def test_situacion_actual_respeta_filas_independientes(self):
        regs = simular(generar_usuarios(20261128, 1), 3, "propio")
        self.assertTrue(all(r["cajero"] == f"C{r['flujo'] + 1}" for r in regs))
        with self.assertRaises(ValueError):
            simular(generar_usuarios(20261128, 1), 4, "propio")

    def test_traza_manual(self):
        """Caso calculado a mano: dos usuarios en el mismo cajero."""
        us = [Usuario(1, 0, 1.0, "Lento", 4.0), Usuario(2, 0, 2.0, "Rápido", 1.0)]
        r = simular(us, 3, "propio")
        self.assertEqual((r[0]["inicio"], r[0]["fin"], r[0]["espera"]), (1.0, 5.0, 0.0))
        self.assertEqual((r[1]["inicio"], r[1]["fin"], r[1]["espera"]), (5.0, 6.0, 3.0))

    def test_fila_unica_usa_el_primer_cajero_libre(self):
        us = [Usuario(1, 0, 0.0, "Muy lento", 6.0), Usuario(2, 1, 0.5, "Rápido", 1.0),
              Usuario(3, 2, 0.6, "Normal", 3.0), Usuario(4, 0, 0.7, "Rápido", 1.0)]
        r = simular(us, 3, "fila_unica")
        self.assertEqual(r[3]["inicio"], 1.5)  # el cajero del usuario 2 queda libre en 1,5

    def test_medias_teoricas(self):
        t = medias_teoricas()
        self.assertAlmostEqual(t["E_servicio"], 3.6)
        self.assertAlmostEqual(t["E_entrellegada"], 4.65)
        self.assertLess(t["rho"], 1)


if __name__ == "__main__":
    unittest.main()
