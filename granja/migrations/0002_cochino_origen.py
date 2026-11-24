# Generated manually for Contru hierro.
from django.db import migrations, models


def identificar_compras_anteriores(apps, schema_editor):
    Cochino = apps.get_model("granja", "Cochino")
    Cochino.objects.filter(costo_compra__gt=0).update(origen="COMPRADO")


class Migration(migrations.Migration):
    dependencies = [
        ("granja", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cochino",
            name="origen",
            field=models.CharField(
                choices=[
                    ("COMPRADO", "Comprado"),
                    ("CRIADO", "Criado en la granja"),
                    ("SIN_ESPECIFICAR", "Sin especificar"),
                ],
                default="SIN_ESPECIFICAR",
                max_length=20,
                verbose_name="origen",
            ),
        ),
        migrations.RunPython(identificar_compras_anteriores, migrations.RunPython.noop),
    ]
