from django.urls import path
from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reportes/", views.reportes, name="reportes"),
    path("login/", views.login_view, name="login"),
    path("salir/", views.logout_view, name="logout"),
    path("cochinos/", views.lista_cochinos, name="cochinos_lista"),
    path("cochinos/nuevo/", views.crear_cochino, name="cochino_crear"),
    path("cochinos/<int:pk>/editar/", views.editar_cochino, name="cochino_editar"),
    path("cochinos/<int:pk>/eliminar/", views.eliminar_cochino, name="cochino_eliminar"),
    path("clientes/", views.lista_clientes, name="clientes_lista"),
    path("clientes/nuevo/", views.crear_cliente, name="cliente_crear"),
    path("clientes/<int:pk>/editar/", views.editar_cliente, name="cliente_editar"),
    path("clientes/<int:pk>/eliminar/", views.eliminar_cliente, name="cliente_eliminar"),
    path("ventas/", views.lista_ventas, name="ventas_lista"),
    path("ventas/nueva/", views.crear_venta, name="venta_crear"),
    path("ventas/<int:pk>/", views.venta_detalle, name="venta_detalle"),
]
