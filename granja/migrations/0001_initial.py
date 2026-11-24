# Generated manually for the educational Contru hierro project.
import decimal
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150, verbose_name="nombre o razón social")),
                ("documento", models.CharField(blank=True, max_length=30, verbose_name="documento / RIF")),
                ("telefono", models.CharField(blank=True, max_length=30, verbose_name="teléfono")),
                ("correo", models.EmailField(blank=True, max_length=254, verbose_name="correo electrónico")),
                ("direccion", models.CharField(blank=True, max_length=255, verbose_name="dirección")),
                ("creado_en", models.DateTimeField(auto_now_add=True, verbose_name="registrado el")),
            ],
            options={"verbose_name": "cliente", "verbose_name_plural": "clientes", "ordering": ["nombre"]},
        ),
        migrations.CreateModel(
            name="Cochino",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=30, unique=True, verbose_name="código identificador")),
                ("nombre", models.CharField(blank=True, max_length=80, verbose_name="nombre")),
                ("raza", models.CharField(choices=[("LANDRACE", "Landrace"), ("YORKSHIRE", "Yorkshire"), ("DUROC", "Duroc"), ("PIETRAIN", "Pietrain"), ("CRIOLLO", "Criollo"), ("OTRO", "Otro")], default="CRIOLLO", max_length=20, verbose_name="raza")),
                ("sexo", models.CharField(choices=[("MACHO", "Macho"), ("HEMBRA", "Hembra")], max_length=10, verbose_name="sexo")),
                ("fecha_nacimiento", models.DateField(blank=True, null=True, verbose_name="fecha de nacimiento")),
                ("peso_kg", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))], verbose_name="peso (kg)")),
                ("costo_compra", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.00"))], verbose_name="costo de compra")),
                ("estado", models.CharField(choices=[("DISPONIBLE", "Disponible"), ("VENDIDO", "Vendido")], default="DISPONIBLE", max_length=12, verbose_name="estado")),
                ("notas", models.TextField(blank=True, verbose_name="notas")),
                ("creado_en", models.DateTimeField(auto_now_add=True, verbose_name="registrado el")),
            ],
            options={"verbose_name": "cochino", "verbose_name_plural": "cochinos", "ordering": ["codigo"]},
        ),
        migrations.CreateModel(
            name="Venta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True, verbose_name="fecha de venta")),
                ("total", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12, verbose_name="total")),
                ("notas", models.TextField(blank=True, verbose_name="notas")),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ventas", to="granja.cliente", verbose_name="cliente")),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ventas_porcinas", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
            ],
            options={"verbose_name": "venta", "verbose_name_plural": "ventas", "ordering": ["-fecha", "-id"]},
        ),
        migrations.CreateModel(
            name="DetalleVenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("precio_venta", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))], verbose_name="precio de venta")),
                ("cochino", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="detalle_venta", to="granja.cochino", verbose_name="cochino vendido")),
                ("venta", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="granja.venta", verbose_name="venta")),
            ],
            options={"verbose_name": "detalle de venta", "verbose_name_plural": "detalles de venta", "ordering": ["id"]},
        ),
    ]
