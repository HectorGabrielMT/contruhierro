# Generated manually for Contru hierro.
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("granja", "0002_cochino_origen"),
    ]

    operations = [
        migrations.AddField(
            model_name="cochino",
            name="madre",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="crias_como_madre", to="granja.cochino",
                limit_choices_to={"sexo": "HEMBRA"}, verbose_name="madre",
            ),
        ),
        migrations.AddField(
            model_name="cochino",
            name="padre",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="crias_como_padre", to="granja.cochino",
                limit_choices_to={"sexo": "MACHO"}, verbose_name="padre",
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="metodo_pago",
            field=models.CharField(
                choices=[
                    ("EFECTIVO", "Efectivo"), ("TRANSFERENCIA", "Transferencia bancaria"),
                    ("PAGO_MOVIL", "Pago móvil"), ("PUNTO_VENTA", "Punto de venta"),
                    ("ZELLE", "Zelle / divisas"), ("CHEQUE", "Cheque"), ("OTRO", "Otro"),
                    ("SIN_ESPECIFICAR", "Sin especificar"),
                ],
                default="SIN_ESPECIFICAR", max_length=20, verbose_name="método de pago",
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="referencia_pago",
            field=models.CharField(blank=True, max_length=60, verbose_name="referencia del pago"),
        ),
        migrations.AddField(
            model_name="venta",
            name="fecha_pago",
            field=models.DateField(blank=True, null=True, verbose_name="fecha del pago"),
        ),
        migrations.AddField(
            model_name="venta",
            name="banco",
            field=models.CharField(blank=True, max_length=80, verbose_name="banco o entidad"),
        ),
        migrations.AddField(
            model_name="venta",
            name="monto_pagado",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="monto pagado",
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="notas_pago",
            field=models.CharField(blank=True, max_length=255, verbose_name="observaciones del pago"),
        ),
    ]
