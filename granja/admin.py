"""Administración de catálogos desde el administrador integrado de Django."""
from django.contrib import admin

from .models import Cliente, Cochino, DetalleVenta, Venta


@admin.register(Cochino)
class CochinoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "raza", "sexo", "origen", "madre", "padre", "peso_kg", "estado", "creado_en")
    list_filter = ("estado", "origen", "raza", "sexo")
    search_fields = ("codigo", "nombre")
    readonly_fields = ("estado", "creado_en")
    ordering = ("codigo",)
    list_per_page = 25


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "telefono", "correo", "creado_en")
    search_fields = ("nombre", "documento", "telefono", "correo")
    ordering = ("nombre",)
    list_per_page = 25


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    fields = ("cochino", "precio_venta")
    readonly_fields = ("cochino", "precio_venta")
    extra = 0
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "total", "metodo_pago", "referencia_pago", "monto_pagado", "creado_por")
    list_filter = ("fecha", "metodo_pago")
    search_fields = ("cliente__nombre", "referencia_pago")
    readonly_fields = (
        "cliente", "fecha", "total", "notas", "metodo_pago", "referencia_pago",
        "fecha_pago", "banco", "monto_pagado", "notas_pago", "creado_por",
    )
    inlines = (DetalleVentaInline,)
    ordering = ("-fecha",)
    list_per_page = 25

    def has_add_permission(self, request):
        # Las ventas deben entrar por el flujo transaccional del sistema.
        return False

    def has_delete_permission(self, request, obj=None):
        # Preserva el historial y evita desincronizar las existencias.
        return False


admin.site.site_header = "Contru hierro · Administración"
admin.site.site_title = "Contru hierro"
admin.site.index_title = "Administración"
