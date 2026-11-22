"""Comprobaciones de la lógica de cola y de la comparación entre modelos."""

import unittest

from simulacion_bancaria import (CIERRE, ESCENARIOS, Cliente, generar_clientes,
                                simular_escenario)


class PruebasSimulacion(unittest.TestCase):
    def test_clientes_identicos_al_repetir_semilla(self):
        self.assertEqual(generar_clientes(20261122, 4), generar_clientes(20261122, 4))
        self.assertNotEqual(generar_clientes(20261122, 4), generar_clientes(20261122, 5))

    def test_todas_las_configuraciones_atienden_misma_demanda_y_respetan_colas(self):
        clientes = generar_clientes(20261122, 3)
        self.assertTrue(all(0 <= c.llegada < CIERRE for c in clientes))
        for escenario, capacidades in ESCENARIOS.items():
            with self.subTest(escenario=escenario):
                registros = simular_escenario(clientes, capacidades)
                self.assertEqual(len(clientes), len(registros))
                self.assertEqual({c.numero for c in clientes},
                                 {r["numero"] for r in registros})
                for registro, cliente in zip(registros, clientes):
                    self.assertEqual(registro["servicio"], cliente.servicio)
                    self.assertGreaterEqual(registro["inicio"], registro["llegada"])
                    self.assertAlmostEqual(registro["fin"] - registro["inicio"],
                                           registro["servicio"])
                    self.assertIn(registro["capacidad"], ("Mixto", registro["accion"]))
                for caja in {r["caja"] for r in registros}:
                    trabajos = sorted((r for r in registros if r["caja"] == caja),
                                      key=lambda r: r["inicio"])
                    self.assertTrue(all(a["fin"] <= b["inicio"] + 1e-10
                                        for a, b in zip(trabajos, trabajos[1:])))

    def test_cierre_vacio_y_trabajo_posterior(self):
        self.assertEqual(simular_escenario([], ("Mixto",)), [])
        clientes = [Cliente(1, 479.0, "Pago", "Muy lento", 10.0),
                    Cliente(2, 479.5, "Pago", "Normal", 3.0)]
        registros = simular_escenario(clientes, ("Pago",))
        self.assertEqual(registros[0]["fin"], 489.0)
        self.assertEqual(registros[1]["inicio"], 489.0)
        self.assertEqual(registros[1]["espera"], 9.5)
        self.assertEqual(sum(r["finalizado_al_cierre"] for r in registros), 0)

    def test_configuracion_incompatible(self):
        cliente = Cliente(1, 2.0, "Pago", "Rápido", 3.0)
        with self.assertRaises(ValueError):
            simular_escenario([cliente], ("Retiro",))


if __name__ == "__main__":
    unittest.main()
