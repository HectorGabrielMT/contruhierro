"""Modelos de registro de animales, clientes y ventas."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cochino(models.Model):
    class Raza(models.TextChoices):
        LANDRACE = "LANDRACE", "Landrace"
        YORKSHIRE = "YORKSHIRE", "Yorkshire"
        DUROC = "DUROC", "Duroc"
        PIETRAIN = "PIETRAIN", "Pietrain"
        CRIOLLO = "CRIOLLO", "Criollo"
        OTRO = "OTRO", "Otro"

    class Sexo(models.TextChoices):
        MACHO = "MACHO", "Macho"
        HEMBRA = "HEMBRA", "Hembra"

    class Estado(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        VENDIDO = "VENDIDO", "Vendido"

    class Origen(models.TextChoices):
        COMPRADO = "COMPRADO", "Comprado"
        CRIADO = "CRIADO", "Criado en la granja"
        SIN_ESPECIFICAR = "SIN_ESPECIFICAR", "Sin especificar"

    codigo = models.CharField("código identificador", max_length=30, unique=True)
    nombre = models.CharField("nombre", max_length=80, blank=True)
    raza = models.CharField("raza", max_length=20, choices=Raza.choices, default=Raza.CRIOLLO)
    sexo = models.CharField("sexo", max_length=10, choices=Sexo.choices)
    fecha_nacimiento = models.DateField("fecha de nacimiento", blank=True, null=True)
    peso_kg = models.DecimalField(
        "peso (kg)", max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    costo_compra = models.DecimalField(
        "costo de compra", max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.DISPONIBLE,
    )
    origen = models.CharField(
        "origen", max_length=20, choices=Origen.choices,
        default=Origen.SIN_ESPECIFICAR,
    )
    madre = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="crias_como_madre", verbose_name="madre",
        limit_choices_to={"sexo": "HEMBRA"},
    )
    padre = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="crias_como_padre", verbose_name="padre",
        limit_choices_to={"sexo": "MACHO"},
    )
    notas = models.TextField("notas", blank=True)
    creado_en = models.DateTimeField("registrado el", auto_now_add=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "cochino"
        verbose_name_plural = "cochinos"

    def __str__(self):
        return f"{self.codigo} — {self.nombre or self.get_raza_display()}"


class Cliente(models.Model):
    nombre = models.CharField("nombre o razón social", max_length=150)
    documento = models.CharField("documento / RIF", max_length=30, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    correo = models.EmailField("correo electrónico", blank=True)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    creado_en = models.DateTimeField("registrado el", auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria"
        PAGO_MOVIL = "PAGO_MOVIL", "Pago móvil"
        PUNTO_VENTA = "PUNTO_VENTA", "Punto de venta"
        ZELLE = "ZELLE", "Zelle / divisas"
        CHEQUE = "CHEQUE", "Cheque"
        OTRO = "OTRO", "Otro"
        SIN_ESPECIFICAR = "SIN_ESPECIFICAR", "Sin especificar"

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ventas", verbose_name="cliente",
    )
    fecha = models.DateTimeField("fecha de venta", auto_now_add=True)
    total = models.DecimalField(
        "total", max_digits=12, decimal_places=2, default=Decimal("0.00"),
    )
    notas = models.TextField("notas", blank=True)
    metodo_pago = models.CharField(
        "método de pago", max_length=20, choices=MetodoPago.choices,
        default=MetodoPago.SIN_ESPECIFICAR,
    )
    referencia_pago = models.CharField("referencia del pago", max_length=60, blank=True)
    fecha_pago = models.DateField("fecha del pago", null=True, blank=True)
    banco = models.CharField("banco o entidad", max_length=80, blank=True)
    monto_pagado = models.DecimalField(
        "monto pagado", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    notas_pago = models.CharField("observaciones del pago", max_length=255, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ventas_porcinas", verbose_name="registrado por",
    )

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "venta"
        verbose_name_plural = "ventas"

    def __str__(self):
        return f"Venta CH-{self.pk:06d}" if self.pk else "Venta nueva"

    @property
    def saldo_pendiente(self):
        """Diferencia entre el total y lo pagado; None si no hay pago registrado."""
        if self.monto_pagado is None:
            return None
        return max(self.total - self.monto_pagado, Decimal("0.00"))

    @property
    def estado_pago(self):
        if self.monto_pagado is None:
            return "SIN_REGISTRAR"
        return "PAGADO" if self.monto_pagado >= self.total else "PARCIAL"

    @property
    def estado_pago_texto(self):
        return {"SIN_REGISTRAR": "Sin registrar", "PAGADO": "Pagado", "PARCIAL": "Abono parcial"}[self.estado_pago]


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name="detalles", verbose_name="venta",
    )
    cochino = models.OneToOneField(
        Cochino, on_delete=models.PROTECT, related_name="detalle_venta",
        verbose_name="cochino vendido",
    )
    precio_venta = models.DecimalField(
        "precio de venta", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"

    def __str__(self):
        return f"{self.cochino.codigo} — {self.precio_venta}"
