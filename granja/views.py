"""Vistas sencillas: la validación de los formularios se hace aquí, sin forms.py."""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models.deletion import ProtectedError

from .models import Cliente, Cochino, DetalleVenta, Venta


# ---------------------------------------------------------------------------
# Autenticación y panel
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    destino = request.GET.get("next", "")
    if request.method == "POST":
        usuario = request.POST.get("username", "").strip()
        clave = request.POST.get("password", "")
        destino = request.POST.get("next", "")
        usuario_autenticado = authenticate(request, username=usuario, password=clave)
        if usuario_autenticado is not None:
            login(request, usuario_autenticado)
            if destino and url_has_allowed_host_and_scheme(
                destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(destino)
            return redirect("dashboard")
        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "granja/login.html", {"next": destino})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    ventas = Venta.objects.select_related("cliente").prefetch_related("detalles__cochino")

    # Ingresos de los últimos 6 meses para la gráfica del panel.
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(6):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    meses.reverse()
    nombres_mes = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    grafica = []
    for anio, mes in meses:
        importe = Venta.objects.filter(fecha__year=anio, fecha__month=mes).aggregate(
            total=Sum("total"))["total"] or Decimal("0.00")
        grafica.append({"etiqueta": nombres_mes[mes - 1], "importe": importe})
    maximo = max((m["importe"] for m in grafica), default=Decimal("0")) or Decimal("1")
    for m in grafica:
        m["porcentaje"] = int((m["importe"] / maximo) * 100) if m["importe"] else 0

    total_cochinos = Cochino.objects.count()
    disponibles = Cochino.objects.filter(estado=Cochino.Estado.DISPONIBLE).count()
    return render(request, "granja/dashboard.html", {
        "grafica_ventas": grafica,
        "porcentaje_disponibles": int(disponibles * 100 / total_cochinos) if total_cochinos else 0,
        "criados_total": Cochino.objects.filter(origen=Cochino.Origen.CRIADO).count(),
        "comprados_total": Cochino.objects.filter(origen=Cochino.Origen.COMPRADO).count(),
        "total_cochinos": Cochino.objects.count(),
        "cochinos_disponibles": Cochino.objects.filter(estado=Cochino.Estado.DISPONIBLE).count(),
        "cochinos_vendidos": Cochino.objects.filter(estado=Cochino.Estado.VENDIDO).count(),
        "total_clientes": Cliente.objects.count(),
        "total_ventas": Venta.objects.count(),
        "ingresos_totales": Venta.objects.aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
        "ingresos_mes": Venta.objects.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
        "ventas_recientes": ventas[:6],
    })


# ---------------------------------------------------------------------------
# Reportes de inventario y ventas
# ---------------------------------------------------------------------------
@login_required
def reportes(request):
    """Muestra cifras del inventario y movimientos entre dos fechas."""
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    desde_texto = request.GET.get("desde", inicio_mes.isoformat())
    hasta_texto = request.GET.get("hasta", hoy.isoformat())
    desde = parse_date(desde_texto)
    hasta = parse_date(hasta_texto)

    if desde is None or hasta is None:
        messages.error(request, "Las fechas no son válidas. Se muestra el período de este mes.")
        desde, hasta = inicio_mes, hoy
        desde_texto, hasta_texto = desde.isoformat(), hasta.isoformat()
    elif desde > hasta:
        messages.error(request, "La fecha inicial debe ser anterior o igual a la fecha final.")
        desde, hasta = inicio_mes, hoy
        desde_texto, hasta_texto = desde.isoformat(), hasta.isoformat()

    todos_los_cochinos = Cochino.objects.all()
    cochinos_periodo = todos_los_cochinos.filter(creado_en__date__range=(desde, hasta))
    ventas_periodo = Venta.objects.filter(fecha__date__range=(desde, hasta))
    resumen_compras = cochinos_periodo.filter(origen=Cochino.Origen.COMPRADO)
    resumen_criados = cochinos_periodo.filter(origen=Cochino.Origen.CRIADO)
    resumen_sin_origen = cochinos_periodo.filter(origen=Cochino.Origen.SIN_ESPECIFICAR)

    resumen_sexo = []
    for valor, etiqueta in Cochino.Sexo.choices:
        grupo = todos_los_cochinos.filter(sexo=valor)
        resumen_sexo.append({
            "sexo": etiqueta,
            "total": grupo.count(),
            "disponibles": grupo.filter(estado=Cochino.Estado.DISPONIBLE).count(),
            "vendidos": grupo.filter(estado=Cochino.Estado.VENDIDO).count(),
            "comprados": grupo.filter(origen=Cochino.Origen.COMPRADO).count(),
            "criados": grupo.filter(origen=Cochino.Origen.CRIADO).count(),
            "sin_origen": grupo.filter(origen=Cochino.Origen.SIN_ESPECIFICAR).count(),
        })

    resumen_razas = []
    for valor, etiqueta in Cochino.Raza.choices:
        grupo = todos_los_cochinos.filter(raza=valor)
        resumen_razas.append({
            "raza": etiqueta,
            "total": grupo.count(),
            "disponibles": grupo.filter(estado=Cochino.Estado.DISPONIBLE).count(),
            "vendidos": grupo.filter(estado=Cochino.Estado.VENDIDO).count(),
            "comprados": grupo.filter(origen=Cochino.Origen.COMPRADO).count(),
            "sin_origen": grupo.filter(origen=Cochino.Origen.SIN_ESPECIFICAR).count(),
        })

    ventas_por_cliente = list(
        ventas_periodo.values("cliente__nombre")
        .annotate(cantidad=Count("id"), importe=Sum("total"))
        .order_by("-importe", "cliente__nombre")[:10]
    )
    ventas_recientes = ventas_periodo.select_related("cliente").prefetch_related(
        "detalles__cochino"
    ).order_by("-fecha", "-id")[:10]
    cochinos_recientes = cochinos_periodo.order_by("-creado_en", "-id")[:10]

    return render(request, "granja/reportes.html", {
        "desde": desde_texto,
        "hasta": hasta_texto,
        "desde_fecha": desde,
        "hasta_fecha": hasta,
        "total_cochinos": todos_los_cochinos.count(),
        "cochinos_disponibles": todos_los_cochinos.filter(estado=Cochino.Estado.DISPONIBLE).count(),
        "cochinos_vendidos": todos_los_cochinos.filter(estado=Cochino.Estado.VENDIDO).count(),
        "total_comprados": todos_los_cochinos.filter(origen=Cochino.Origen.COMPRADO).count(),
        "total_criados": todos_los_cochinos.filter(origen=Cochino.Origen.CRIADO).count(),
        "total_sin_origen": todos_los_cochinos.filter(origen=Cochino.Origen.SIN_ESPECIFICAR).count(),
        "total_machos": todos_los_cochinos.filter(sexo=Cochino.Sexo.MACHO).count(),
        "total_hembras": todos_los_cochinos.filter(sexo=Cochino.Sexo.HEMBRA).count(),
        "total_peso": todos_los_cochinos.aggregate(total=Sum("peso_kg"))["total"] or Decimal("0.00"),
        "comprados_periodo": resumen_compras.count(),
        "criados_periodo": resumen_criados.count(),
        "sin_origen_periodo": resumen_sin_origen.count(),
        "ingresados_periodo": cochinos_periodo.count(),
        "inversion_periodo": resumen_compras.aggregate(total=Sum("costo_compra"))["total"] or Decimal("0.00"),
        "ventas_periodo": ventas_periodo.count(),
        "ingresos_periodo": ventas_periodo.aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
        "cobrado_periodo": ventas_periodo.aggregate(total=Sum("monto_pagado"))["total"] or Decimal("0.00"),
        "resumen_sexo": resumen_sexo,
        "resumen_razas": resumen_razas,
        "ventas_por_cliente": ventas_por_cliente,
        "ventas_recientes": ventas_recientes,
        "cochinos_recientes": cochinos_recientes,
    })


# ---------------------------------------------------------------------------
# Registro de cochinos
# ---------------------------------------------------------------------------
def _datos_cochino(cochino=None):
    if cochino is None:
        return {"codigo": "", "nombre": "", "raza": Cochino.Raza.CRIOLLO,
                "sexo": Cochino.Sexo.MACHO, "fecha_nacimiento": "", "peso_kg": "",
                "costo_compra": "0.00", "origen": Cochino.Origen.COMPRADO, "notas": "",
                "madre": "", "padre": ""}
    return {
        "codigo": cochino.codigo,
        "nombre": cochino.nombre,
        "raza": cochino.raza,
        "sexo": cochino.sexo,
        "fecha_nacimiento": cochino.fecha_nacimiento.isoformat() if cochino.fecha_nacimiento else "",
        "peso_kg": cochino.peso_kg,
        "costo_compra": cochino.costo_compra,
        "origen": cochino.origen,
        "madre": cochino.madre_id or "",
        "padre": cochino.padre_id or "",
        "notas": cochino.notas,
    }


def _contexto_cochino_form(titulo, datos, errores, cochino=None):
    """Datos comunes del formulario de cochinos, incluidos los posibles padres."""
    otros = Cochino.objects.all()
    if cochino is not None:
        otros = otros.exclude(pk=cochino.pk)
    return {
        "titulo": titulo, "datos": datos, "errores": errores, "cochino": cochino,
        "razas": Cochino.Raza.choices, "sexos": Cochino.Sexo.choices,
        "origenes": Cochino.Origen.choices,
        "madres": otros.filter(sexo=Cochino.Sexo.HEMBRA),
        "padres": otros.filter(sexo=Cochino.Sexo.MACHO),
    }


def _validar_guardar_cochino(request, cochino=None):
    datos = request.POST
    errores = {}
    codigo = datos.get("codigo", "").strip()
    nombre = datos.get("nombre", "").strip()
    raza = datos.get("raza", Cochino.Raza.CRIOLLO)
    sexo = datos.get("sexo", "")
    origen = datos.get("origen", Cochino.Origen.COMPRADO)
    fecha_texto = datos.get("fecha_nacimiento", "").strip()
    notas = datos.get("notas", "").strip()

    if not codigo:
        errores["codigo"] = "El código es obligatorio."
    elif len(codigo) > 30:
        errores["codigo"] = "El código no puede superar los 30 caracteres."
    else:
        duplicado = Cochino.objects.filter(codigo=codigo)
        if cochino:
            duplicado = duplicado.exclude(pk=cochino.pk)
        if duplicado.exists():
            errores["codigo"] = "Ya existe un cochino con ese código."
    if len(nombre) > 80:
        errores["nombre"] = "El nombre no puede superar los 80 caracteres."

    if raza not in Cochino.Raza.values:
        errores["raza"] = "Selecciona una raza válida."
    if sexo not in Cochino.Sexo.values:
        errores["sexo"] = "Selecciona el sexo."
    if origen not in Cochino.Origen.values:
        errores["origen"] = "Selecciona cómo llegó el cochino a la granja."

    # Madre y padre: obligatorios si nació en la granja; se descartan en otro caso.
    madre = padre = None
    if origen == Cochino.Origen.CRIADO:
        otros = Cochino.objects.all()
        if cochino:
            otros = otros.exclude(pk=cochino.pk)
        madre_id, padre_id = datos.get("madre", "").strip(), datos.get("padre", "").strip()
        if not madre_id:
            errores["madre"] = "Indica la madre del cochino."
        else:
            madre = otros.filter(pk=madre_id, sexo=Cochino.Sexo.HEMBRA).first() if madre_id.isdigit() else None
            if madre is None:
                errores["madre"] = "Selecciona una madre válida (debe ser una hembra registrada)."
        if not padre_id:
            errores["padre"] = "Indica el padre del cochino."
        else:
            padre = otros.filter(pk=padre_id, sexo=Cochino.Sexo.MACHO).first() if padre_id.isdigit() else None
            if padre is None:
                errores["padre"] = "Selecciona un padre válido (debe ser un macho registrado)."

    peso = _leer_decimal(datos.get("peso_kg", ""), "peso", errores, minimo=Decimal("0.01"))
    costo = _leer_decimal(datos.get("costo_compra") or "0", "costo_compra", errores, minimo=Decimal("0"))
    fecha_nacimiento = None
    if fecha_texto:
        try:
            fecha_nacimiento = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
            if fecha_nacimiento > timezone.localdate():
                errores["fecha_nacimiento"] = "La fecha de nacimiento no puede estar en el futuro."
        except ValueError:
            errores["fecha_nacimiento"] = "Introduce una fecha válida."

    if errores:
        return datos, errores

    if cochino is None:
        cochino = Cochino()
    cochino.codigo = codigo
    cochino.nombre = nombre
    cochino.raza = raza
    cochino.sexo = sexo
    cochino.fecha_nacimiento = fecha_nacimiento
    cochino.peso_kg = peso
    cochino.costo_compra = costo
    cochino.origen = origen
    cochino.madre = madre
    cochino.padre = padre
    cochino.notas = notas
    # El estado solo cambia desde el flujo de venta, no desde el formulario.
    if not cochino.pk:
        cochino.estado = Cochino.Estado.DISPONIBLE
    try:
        cochino.save()
    except IntegrityError:
        return datos, {"codigo": "No fue posible guardar ese código. Intenta con otro."}
    return None, {}


def _leer_decimal(valor, campo, errores, minimo=None, maximo=Decimal("9999999999.99")):
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        errores[campo] = "Este campo es obligatorio."
        return None
    try:
        numero = Decimal(texto)
        if not numero.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        errores[campo] = "Introduce una cantidad numérica válida."
        return None
    if minimo is not None and numero < minimo:
        errores[campo] = f"El valor debe ser igual o mayor que {minimo}."
        return None
    if maximo is not None and numero > maximo:
        errores[campo] = "La cantidad es demasiado grande."
        return None
    try:
        return numero.quantize(Decimal("0.01"))
    except InvalidOperation:
        errores[campo] = "La cantidad es demasiado grande o tiene demasiados decimales."
        return None


@login_required
def lista_cochinos(request):
    cochinos = Cochino.objects.select_related("madre", "padre")
    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    if busqueda:
        cochinos = cochinos.filter(
            Q(codigo__icontains=busqueda) | Q(nombre__icontains=busqueda) | Q(raza__icontains=busqueda)
        )
    if estado in Cochino.Estado.values:
        cochinos = cochinos.filter(estado=estado)
    return render(request, "granja/cochinos_lista.html", {
        "cochinos": cochinos,
        "q": busqueda,
        "estado_filtro": estado,
    })


@login_required
@require_http_methods(["GET", "POST"])
def crear_cochino(request):
    if request.method == "POST":
        datos, errores = _validar_guardar_cochino(request)
        if not errores:
            messages.success(request, "El cochino se registró correctamente.")
            return redirect("cochinos_lista")
        return render(request, "granja/cochino_form.html",
                      _contexto_cochino_form("Registrar cochino", datos, errores))
    return render(request, "granja/cochino_form.html",
                  _contexto_cochino_form("Registrar cochino", _datos_cochino(), {}))


@login_required
@require_http_methods(["GET", "POST"])
def editar_cochino(request, pk):
    cochino = get_object_or_404(Cochino, pk=pk)
    if cochino.estado == Cochino.Estado.VENDIDO:
        messages.error(request, "No se puede editar un cochino que ya fue vendido.")
        return redirect("cochinos_lista")
    if request.method == "POST":
        datos, errores = _validar_guardar_cochino(request, cochino)
        if not errores:
            messages.success(request, "Los datos del cochino se actualizaron.")
            return redirect("cochinos_lista")
    else:
        datos, errores = _datos_cochino(cochino), {}
    return render(request, "granja/cochino_form.html",
                  _contexto_cochino_form("Editar cochino", datos, errores, cochino))


@login_required
@require_POST
def eliminar_cochino(request, pk):
    cochino = get_object_or_404(Cochino, pk=pk)
    if cochino.estado == Cochino.Estado.VENDIDO:
        messages.error(request, "No se puede eliminar un cochino vendido; conserva el historial de ventas.")
    else:
        try:
            cochino.delete()
            messages.success(request, "El cochino se eliminó correctamente.")
        except ProtectedError:
            messages.error(request, "Este cochino tiene registros relacionados y no puede eliminarse.")
    return redirect("cochinos_lista")


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
def _datos_cliente(cliente=None):
    if cliente is None:
        return {"nombre": "", "documento": "", "telefono": "", "correo": "", "direccion": ""}
    return {"nombre": cliente.nombre, "documento": cliente.documento, "telefono": cliente.telefono,
            "correo": cliente.correo, "direccion": cliente.direccion}


def _validar_guardar_cliente(request, cliente=None):
    datos = request.POST
    errores = {}
    nombre = datos.get("nombre", "").strip()
    documento = datos.get("documento", "").strip()
    telefono = datos.get("telefono", "").strip()
    correo = datos.get("correo", "").strip()
    direccion = datos.get("direccion", "").strip()
    if not nombre:
        errores["nombre"] = "El nombre es obligatorio."
    elif len(nombre) > 150:
        errores["nombre"] = "El nombre no puede superar los 150 caracteres."
    if len(documento) > 30:
        errores["documento"] = "El documento no puede superar los 30 caracteres."
    if len(telefono) > 30:
        errores["telefono"] = "El teléfono no puede superar los 30 caracteres."
    if len(correo) > 254:
        errores["correo"] = "El correo no puede superar los 254 caracteres."
    elif correo:
        try:
            validate_email(correo)
        except ValidationError:
            errores["correo"] = "Introduce un correo electrónico válido."
    if len(direccion) > 255:
        errores["direccion"] = "La dirección no puede superar los 255 caracteres."
    if errores:
        return datos, errores
    if cliente is None:
        cliente = Cliente()
    cliente.nombre = nombre
    cliente.documento = documento
    cliente.telefono = telefono
    cliente.correo = correo
    cliente.direccion = direccion
    cliente.save()
    return None, {}


@login_required
def lista_clientes(request):
    clientes = Cliente.objects.all()
    busqueda = request.GET.get("q", "").strip()
    if busqueda:
        clientes = clientes.filter(
            Q(nombre__icontains=busqueda) | Q(documento__icontains=busqueda) | Q(telefono__icontains=busqueda)
        )
    return render(request, "granja/clientes_lista.html", {"clientes": clientes, "q": busqueda})


@login_required
@require_http_methods(["GET", "POST"])
def crear_cliente(request):
    if request.method == "POST":
        datos, errores = _validar_guardar_cliente(request)
        if not errores:
            messages.success(request, "El cliente se registró correctamente.")
            return redirect("clientes_lista")
    else:
        datos, errores = _datos_cliente(), {}
    return render(request, "granja/cliente_form.html", {
        "titulo": "Registrar cliente", "datos": datos, "errores": errores,
    })


@login_required
@require_http_methods(["GET", "POST"])
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        datos, errores = _validar_guardar_cliente(request, cliente)
        if not errores:
            messages.success(request, "Los datos del cliente se actualizaron.")
            return redirect("clientes_lista")
    else:
        datos, errores = _datos_cliente(cliente), {}
    return render(request, "granja/cliente_form.html", {
        "titulo": "Editar cliente", "datos": datos, "errores": errores,
    })


@login_required
@require_POST
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    try:
        cliente.delete()
        messages.success(request, "El cliente se eliminó correctamente.")
    except ProtectedError:
        messages.error(request, "No se puede eliminar un cliente que tiene ventas registradas.")
    return redirect("clientes_lista")


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------
def _clientes_para_form(clientes, seleccionado=""):
    """Marca el cliente elegido para volver a mostrarlo si hay errores."""
    clientes = list(clientes)
    for cliente in clientes:
        cliente.esta_seleccionado = str(cliente.pk) == str(seleccionado)
    return clientes


def _filas_venta(cochinos, ids_seleccionados=None, datos=None):
    ids_seleccionados = set(ids_seleccionados or [])
    filas = []
    for cochino in cochinos:
        filas.append({
            "cochino": cochino,
            "seleccionado": str(cochino.pk) in ids_seleccionados,
            "precio": (datos or {}).get(f"precio_{cochino.pk}", ""),
        })
    return filas


def _metodos_pago():
    """Métodos que se pueden elegir al vender (sin la opción para registros antiguos)."""
    return [m for m in Venta.MetodoPago.choices if m[0] != Venta.MetodoPago.SIN_ESPECIFICAR]


def _validar_pago(valores, errores):
    """Valida los datos de pago de una venta y agrega los problemas a `errores`."""
    metodo = valores["metodo_pago"]
    if metodo not in dict(_metodos_pago()):
        errores.append("Selecciona el método de pago.")
    if metodo != Venta.MetodoPago.EFECTIVO and not valores["referencia_pago"]:
        errores.append("Indica la referencia del pago (no es necesaria solo para pagos en efectivo).")
    if len(valores["referencia_pago"]) > 60:
        errores.append("La referencia del pago no puede superar los 60 caracteres.")
    if len(valores["banco"]) > 80:
        errores.append("El banco no puede superar los 80 caracteres.")
    if len(valores["notas_pago"]) > 255:
        errores.append("Las observaciones del pago no pueden superar los 255 caracteres.")

    fecha = None
    try:
        fecha = datetime.strptime(valores["fecha_pago"], "%Y-%m-%d").date()
        if fecha > timezone.localdate():
            errores.append("La fecha del pago no puede estar en el futuro.")
    except ValueError:
        errores.append("Indica una fecha de pago válida.")

    errores_monto = {}
    monto = _leer_decimal(valores["monto_pagado"], "monto", errores_monto, minimo=Decimal("0.01"))
    if monto is None:
        errores.append("Indica un monto pagado válido, mayor que cero.")
    return {"fecha": fecha, "monto": monto}


@login_required
@require_http_methods(["GET", "POST"])
def crear_venta(request):
    clientes = Cliente.objects.all()
    disponibles = Cochino.objects.filter(estado=Cochino.Estado.DISPONIBLE)
    errores = []
    ids_seleccionados = []
    valores = {"cliente": "", "notas": "", "metodo_pago": Venta.MetodoPago.EFECTIVO,
               "referencia_pago": "", "fecha_pago": timezone.localdate().isoformat(),
               "banco": "", "monto_pagado": "", "notas_pago": ""}

    if request.method == "GET":
        return render(request, "granja/venta_form.html", {
            "clientes": _clientes_para_form(clientes), "filas": _filas_venta(disponibles),
            "errores": errores, "valores": valores,
            "hay_disponibles": disponibles.exists(),
            "metodos_pago": _metodos_pago(),
        })

    valores = {
        "cliente": request.POST.get("cliente", ""),
        "notas": request.POST.get("notas", "").strip(),
        "metodo_pago": request.POST.get("metodo_pago", ""),
        "referencia_pago": request.POST.get("referencia_pago", "").strip(),
        "fecha_pago": request.POST.get("fecha_pago", "").strip(),
        "banco": request.POST.get("banco", "").strip(),
        "monto_pagado": request.POST.get("monto_pagado", "").strip(),
        "notas_pago": request.POST.get("notas_pago", "").strip(),
    }
    pago = _validar_pago(valores, errores)
    ids_seleccionados = request.POST.getlist("cochinos")
    if not valores["cliente"]:
        errores.append("Selecciona un cliente.")
    try:
        cliente = Cliente.objects.get(pk=int(valores["cliente"]))
    except (ValueError, TypeError, Cliente.DoesNotExist):
        cliente = None
        if "Selecciona un cliente." not in errores:
            errores.append("El cliente seleccionado no existe.")

    if not ids_seleccionados:
        errores.append("Selecciona al menos un cochino para la venta.")
    if len(set(ids_seleccionados)) != len(ids_seleccionados):
        errores.append("Hay cochinos repetidos en la selección.")

    ids_enteros = []
    try:
        ids_enteros = [int(identificador) for identificador in ids_seleccionados]
    except (TypeError, ValueError):
        errores.append("La selección contiene un identificador inválido.")

    precios = {}
    for identificador in ids_seleccionados:
        precio = _leer_decimal(
            request.POST.get(f"precio_{identificador}", ""),
            f"precio_{identificador}", {}, minimo=Decimal("0.01"),
        )
        if precio is None:
            errores.append(f"Indica un precio válido mayor que cero para el cochino {identificador}.")
        else:
            try:
                precios[str(int(identificador))] = precio
            except ValueError:
                # El identificador inválido ya fue añadido a los errores.
                pass

    # El monto pagado no puede superar el total de la venta.
    if pago["monto"] is not None and len(precios) == len(ids_seleccionados) and ids_seleccionados:
        total_previsto = sum(precios.values(), Decimal("0.00"))
        if pago["monto"] > total_previsto:
            errores.append("El monto pagado no puede ser mayor que el total de la venta.")

    if not errores and cliente is not None:
        try:
            with transaction.atomic():
                cochinos = list(Cochino.objects.select_for_update().filter(pk__in=ids_enteros).order_by("pk"))
                if len(cochinos) != len(ids_enteros):
                    errores.append("Uno o más cochinos ya no existen.")
                elif any(c.estado != Cochino.Estado.DISPONIBLE for c in cochinos):
                    errores.append("Uno o más cochinos ya fueron vendidos. Actualiza la página e inténtalo de nuevo.")
                elif DetalleVenta.objects.filter(cochino_id__in=ids_enteros).exists():
                    errores.append("Uno o más cochinos ya tienen una venta registrada.")

                if not errores:
                    total = sum((precios[str(c.pk)] for c in cochinos), Decimal("0.00"))
                    venta = Venta.objects.create(
                        cliente=cliente, total=total, notas=valores["notas"], creado_por=request.user,
                        metodo_pago=valores["metodo_pago"], referencia_pago=valores["referencia_pago"],
                        fecha_pago=pago["fecha"], banco=valores["banco"],
                        monto_pagado=pago["monto"], notas_pago=valores["notas_pago"],
                    )
                    DetalleVenta.objects.bulk_create([
                        DetalleVenta(venta=venta, cochino=c, precio_venta=precios[str(c.pk)])
                        for c in cochinos
                    ])
                    Cochino.objects.filter(pk__in=ids_enteros).update(estado=Cochino.Estado.VENDIDO)
                    messages.success(request, f"Venta CH-{venta.pk:06d} registrada correctamente.")
                    return redirect("venta_detalle", pk=venta.pk)
        except IntegrityError:
            errores.append("No se pudo registrar la venta porque uno de los cochinos ya está asociado a otra venta.")

    disponibles = Cochino.objects.filter(estado=Cochino.Estado.DISPONIBLE)
    return render(request, "granja/venta_form.html", {
        "clientes": _clientes_para_form(clientes, valores["cliente"]),
        "filas": _filas_venta(disponibles, ids_seleccionados, request.POST),
        "errores": errores, "valores": valores,
        "hay_disponibles": disponibles.exists(),
        "metodos_pago": _metodos_pago(),
    })


@login_required
def lista_ventas(request):
    ventas = Venta.objects.select_related("cliente", "creado_por").prefetch_related("detalles__cochino")
    busqueda = request.GET.get("q", "").strip()
    if busqueda:
        filtro = Q(cliente__nombre__icontains=busqueda) | Q(referencia_pago__icontains=busqueda)
        numero_venta = busqueda.upper().removeprefix("CH-").lstrip("0")
        if numero_venta.isdigit():
            filtro |= Q(pk=int(numero_venta))
        ventas = ventas.filter(filtro)
    return render(request, "granja/ventas_lista.html", {"ventas": ventas, "q": busqueda})


@login_required
def venta_detalle(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "creado_por").prefetch_related("detalles__cochino"), pk=pk,
    )
    return render(request, "granja/venta_detalle.html", {"venta": venta})
