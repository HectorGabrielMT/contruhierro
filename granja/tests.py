from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Cochino, DetalleVenta, Venta


PAGO = {
    "metodo_pago": "TRANSFERENCIA", "referencia_pago": "REF-998877",
    "fecha_pago": "2026-10-01", "banco": "Banesco", "notas_pago": "",
}


class FlujoVentaTests(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(username="operador", password="ClaveSegura123!")
        self.client.login(username="operador", password="ClaveSegura123!")
        self.cliente = Cliente.objects.create(nombre="Cliente de prueba")
        self.cochino_a = Cochino.objects.create(
            codigo="CH-T001", sexo=Cochino.Sexo.MACHO, peso_kg=Decimal("42.50"),
        )
        self.cochino_b = Cochino.objects.create(
            codigo="CH-T002", sexo=Cochino.Sexo.HEMBRA, peso_kg=Decimal("39.00"),
        )

    def test_venta_multiple_guarda_total_y_marca_animales_vendidos(self):
        respuesta = self.client.post(reverse("venta_crear"), {
            "cliente": str(self.cliente.pk),
            "notas": "Venta de prueba",
            "cochinos": [str(self.cochino_a.pk), str(self.cochino_b.pk)],
            f"precio_{self.cochino_a.pk}": "120.00",
            f"precio_{self.cochino_b.pk}": "135.50",
            "monto_pagado": "255.50", **PAGO,
        })
        self.assertEqual(respuesta.status_code, 302)
        venta = Venta.objects.get()
        self.assertEqual(venta.total, Decimal("255.50"))
        self.assertEqual(DetalleVenta.objects.filter(venta=venta).count(), 2)
        self.cochino_a.refresh_from_db()
        self.cochino_b.refresh_from_db()
        self.assertEqual(self.cochino_a.estado, Cochino.Estado.VENDIDO)
        self.assertEqual(self.cochino_b.estado, Cochino.Estado.VENDIDO)

    def test_precio_invalido_no_crea_venta_ni_cambia_estado(self):
        respuesta = self.client.post(reverse("venta_crear"), {
            "cliente": str(self.cliente.pk),
            "notas": "",
            "cochinos": [str(self.cochino_a.pk)],
            f"precio_{self.cochino_a.pk}": "0",
            "monto_pagado": "10.00", **PAGO,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)
        self.cochino_a.refresh_from_db()
        self.assertEqual(self.cochino_a.estado, Cochino.Estado.DISPONIBLE)

    def test_cochino_no_puede_venderse_dos_veces(self):
        self.client.post(reverse("venta_crear"), {
            "cliente": str(self.cliente.pk), "notas": "",
            "cochinos": [str(self.cochino_a.pk)], f"precio_{self.cochino_a.pk}": "120.00",
            "monto_pagado": "120.00", **PAGO,
        })
        respuesta = self.client.post(reverse("venta_crear"), {
            "cliente": str(self.cliente.pk), "notas": "",
            "cochinos": [str(self.cochino_a.pk)], f"precio_{self.cochino_a.pk}": "125.00",
            "monto_pagado": "125.00", **PAGO,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(DetalleVenta.objects.filter(cochino=self.cochino_a).count(), 1)

    def _vender(self, **extra):
        datos = {
            "cliente": str(self.cliente.pk), "notas": "",
            "cochinos": [str(self.cochino_a.pk)], f"precio_{self.cochino_a.pk}": "100.00",
            "monto_pagado": "100.00", **PAGO,
        }
        datos.update(extra)
        return self.client.post(reverse("venta_crear"), datos)

    def test_venta_guarda_datos_de_pago(self):
        self.assertEqual(self._vender().status_code, 302)
        venta = Venta.objects.get()
        self.assertEqual(venta.metodo_pago, "TRANSFERENCIA")
        self.assertEqual(venta.referencia_pago, "REF-998877")
        self.assertEqual(venta.fecha_pago.isoformat(), "2026-10-01")
        self.assertEqual(venta.banco, "Banesco")
        self.assertEqual(venta.monto_pagado, Decimal("100.00"))
        self.assertEqual(venta.estado_pago, "PAGADO")

    def test_pago_parcial_deja_saldo_pendiente(self):
        self._vender(monto_pagado="40.00")
        venta = Venta.objects.get()
        self.assertEqual(venta.estado_pago, "PARCIAL")
        self.assertEqual(venta.saldo_pendiente, Decimal("60.00"))

    def test_referencia_obligatoria_salvo_efectivo(self):
        self._vender(referencia_pago="")
        self.assertEqual(Venta.objects.count(), 0)
        self._vender(metodo_pago="EFECTIVO", referencia_pago="")
        self.assertEqual(Venta.objects.count(), 1)

    def test_monto_pagado_no_puede_superar_el_total(self):
        self._vender(monto_pagado="150.00")
        self.assertEqual(Venta.objects.count(), 0)
        self.cochino_a.refresh_from_db()
        self.assertEqual(self.cochino_a.estado, Cochino.Estado.DISPONIBLE)

    def test_fecha_de_pago_futura_se_rechaza(self):
        self._vender(fecha_pago="2999-01-01")
        self.assertEqual(Venta.objects.count(), 0)

    def test_detalle_de_venta_muestra_pago(self):
        self._vender()
        respuesta = self.client.get(reverse("venta_detalle", args=[Venta.objects.get().pk]))
        self.assertContains(respuesta, "REF-998877")
        self.assertContains(respuesta, "Banesco")

    def test_registro_de_cochino_requiere_autenticacion(self):
        self.client.logout()
        respuesta = self.client.get(reverse("cochinos_lista"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)


class ReportesTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="reportes", password="ClaveSegura123!")
        self.client.login(username="reportes", password="ClaveSegura123!")
        self.comprado = Cochino.objects.create(
            codigo="REP-001", sexo=Cochino.Sexo.MACHO, peso_kg=Decimal("50.00"),
            costo_compra=Decimal("200.00"), origen=Cochino.Origen.COMPRADO,
        )
        self.criado = Cochino.objects.create(
            codigo="REP-002", sexo=Cochino.Sexo.HEMBRA, peso_kg=Decimal("45.00"),
            origen=Cochino.Origen.CRIADO,
        )

    def test_reporte_muestra_inventario_por_sexo_y_origen(self):
        respuesta = self.client.get(reverse("reportes"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_cochinos"], 2)
        self.assertEqual(respuesta.context["total_comprados"], 1)
        self.assertEqual(respuesta.context["total_criados"], 1)
        self.assertEqual(respuesta.context["total_machos"], 1)
        self.assertEqual(respuesta.context["total_hembras"], 1)

    def test_reporte_requiere_iniciar_sesion(self):
        self.client.logout()
        respuesta = self.client.get(reverse("reportes"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)

    def test_fechas_invertidas_no_rompen_reporte(self):
        respuesta = self.client.get(reverse("reportes"), {
            "desde": "2026-10-20", "hasta": "2026-10-01",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "La fecha inicial debe ser anterior")


class PadresCochinoTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="granjero", password="ClaveSegura123!")
        self.client.login(username="granjero", password="ClaveSegura123!")
        self.madre = Cochino.objects.create(codigo="M-001", sexo=Cochino.Sexo.HEMBRA, peso_kg=Decimal("120"))
        self.padre = Cochino.objects.create(codigo="P-001", sexo=Cochino.Sexo.MACHO, peso_kg=Decimal("150"))

    def _datos(self, **extra):
        datos = {
            "codigo": "CRIA-001", "nombre": "", "raza": "CRIOLLO", "sexo": "MACHO",
            "origen": "CRIADO", "peso_kg": "5.00", "costo_compra": "0",
            "madre": str(self.madre.pk), "padre": str(self.padre.pk),
        }
        datos.update(extra)
        return datos

    def test_cria_nacida_en_la_granja_guarda_madre_y_padre(self):
        respuesta = self.client.post(reverse("cochino_crear"), self._datos())
        self.assertEqual(respuesta.status_code, 302)
        cria = Cochino.objects.get(codigo="CRIA-001")
        self.assertEqual(cria.madre, self.madre)
        self.assertEqual(cria.padre, self.padre)

    def test_cria_sin_padres_se_rechaza(self):
        respuesta = self.client.post(reverse("cochino_crear"), self._datos(madre="", padre=""))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Cochino.objects.filter(codigo="CRIA-001").exists())

    def test_madre_debe_ser_hembra_y_padre_macho(self):
        respuesta = self.client.post(reverse("cochino_crear"), self._datos(
            madre=str(self.padre.pk), padre=str(self.madre.pk)))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Cochino.objects.filter(codigo="CRIA-001").exists())

    def test_cochino_comprado_no_guarda_padres(self):
        self.client.post(reverse("cochino_crear"), self._datos(origen="COMPRADO"))
        cochino = Cochino.objects.get(codigo="CRIA-001")
        self.assertIsNone(cochino.madre)
        self.assertIsNone(cochino.padre)

    def test_no_se_elimina_un_padre_con_crias(self):
        self.client.post(reverse("cochino_crear"), self._datos())
        self.client.post(reverse("cochino_eliminar", args=[self.madre.pk]))
        self.assertTrue(Cochino.objects.filter(pk=self.madre.pk).exists())

    def test_lista_muestra_genealogia(self):
        self.client.post(reverse("cochino_crear"), self._datos())
        respuesta = self.client.get(reverse("cochinos_lista"))
        self.assertContains(respuesta, "Madre: M-001")
        self.assertContains(respuesta, "Padre: P-001")


class PaginasTests(TestCase):
    """Comprueba que todas las pantallas se muestran con datos reales."""

    def setUp(self):
        get_user_model().objects.create_user(username="visor", password="ClaveSegura123!")
        self.client.login(username="visor", password="ClaveSegura123!")
        self.cliente = Cliente.objects.create(nombre="Cliente Uno")
        self.madre = Cochino.objects.create(codigo="M-9", sexo=Cochino.Sexo.HEMBRA, peso_kg=Decimal("100"))
        self.padre = Cochino.objects.create(codigo="P-9", sexo=Cochino.Sexo.MACHO, peso_kg=Decimal("130"))
        self.cria = Cochino.objects.create(
            codigo="C-9", sexo=Cochino.Sexo.MACHO, peso_kg=Decimal("8"),
            origen=Cochino.Origen.CRIADO, madre=self.madre, padre=self.padre,
        )
        self.client.post(reverse("venta_crear"), {
            "cliente": str(self.cliente.pk), "notas": "", "cochinos": [str(self.cria.pk)],
            f"precio_{self.cria.pk}": "90.00", "metodo_pago": "EFECTIVO", "referencia_pago": "",
            "fecha_pago": "2026-10-01", "banco": "", "monto_pagado": "90.00", "notas_pago": "",
        })

    def test_todas_las_pantallas_responden(self):
        venta = Venta.objects.get()
        destinos = [
            reverse("dashboard"), reverse("reportes"), reverse("cochinos_lista"),
            reverse("cochino_crear"), reverse("cochino_editar", args=[self.madre.pk]),
            reverse("clientes_lista"), reverse("cliente_crear"),
            reverse("cliente_editar", args=[self.cliente.pk]), reverse("ventas_lista"),
            reverse("venta_crear"), reverse("venta_detalle", args=[venta.pk]),
        ]
        for url in destinos:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_editar_cria_conserva_padres_seleccionados(self):
        # La cría ya está vendida; se comprueba con una nueva cría disponible.
        nueva = Cochino.objects.create(
            codigo="C-10", sexo=Cochino.Sexo.HEMBRA, peso_kg=Decimal("7"),
            origen=Cochino.Origen.CRIADO, madre=self.madre, padre=self.padre,
        )
        respuesta = self.client.get(reverse("cochino_editar", args=[nueva.pk]))
        self.assertContains(respuesta, f'value="{self.madre.pk}" selected')
        self.assertContains(respuesta, f'value="{self.padre.pk}" selected')
