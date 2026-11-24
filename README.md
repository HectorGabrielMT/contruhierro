# Contru hierro

Sistema de **control de ventas y registro de cochinos**, desarrollado con Django, SQLite y HTML con clases de TailwindCSS. No se utiliza `forms.py`: los campos de los formularios están escritos directamente en las plantillas HTML y las vistas validan los datos en el servidor.

## Qué puede hacer

- Ver un panel de inicio con totales de cochinos, animales disponibles, ventas, ingresos y una gráfica de los últimos 6 meses.
- Registrar, buscar y actualizar cochinos con código, nombre, raza, sexo, fecha de nacimiento, peso, origen y notas.
- **Genealogía:** cuando el origen es «Criado en la granja», el formulario exige seleccionar la **madre** (una hembra registrada) y el **padre** (un macho registrado). Ambos se muestran en el listado. Un cochino que tiene crías registradas no puede eliminarse, para no perder la genealogía.
- Consultar el estado de cada cochino: disponible o vendido.
- Registrar clientes con datos de contacto.
- Crear una venta de uno o varios cochinos, asignarla a un cliente y definir el precio de cada animal.
- **Datos de pago:** cada venta guarda el método de pago, la referencia (obligatoria salvo en efectivo), la fecha del pago, el banco o entidad, el monto pagado y observaciones. Si el monto es menor que el total, la venta queda como «Abono parcial» con su saldo pendiente. Se puede buscar una venta por su referencia de pago.
- Calcular el total en el servidor, guardar el precio histórico de cada cochino vendido y actualizar su estado.
- Consultar y, si hace falta, imprimir el detalle de cada venta.
- Iniciar sesión y utilizar el administrador integrado de Django.

Las ventas quedan protegidas por una transacción y no se permite vender de nuevo un cochino que ya fue vendido. Los historiales de ventas no pueden eliminarse desde la interfaz para evitar que el registro comercial pierda consistencia.

## Requisitos

- Python 3.10 o superior.
- Conexión a internet para cargar TailwindCSS y la tipografía Inter desde su CDN (si la tipografía no carga, se usa la del sistema). Las imágenes e iconos de cochinos se guardan localmente.

## Instalación en Windows

1. Descomprime el archivo ZIP.
2. Abre PowerShell dentro de la carpeta `ContruHierro` (la que contiene `manage.py`).
3. Ejecuta los siguientes comandos, uno por uno:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Si PowerShell no permite activar el entorno, puedes ejecutar los comandos usando el intérprete local directamente, por ejemplo:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

## Instalación en Linux o macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Abrir el sistema

- Aplicación: <http://127.0.0.1:8000/>
- Administración de Django: <http://127.0.0.1:8000/admin/>

Durante la instalación crearás tu usuario administrador con `createsuperuser`. No hay una contraseña predeterminada incluida en el proyecto.

## Pruebas automáticas

```bash
python manage.py test granja
```

Las pruebas incluidas cubren el cálculo de una venta con varios cochinos, el cambio de estado de los animales, la prevención de ventas duplicadas, la validación de los datos de pago, la genealogía (madre y padre) y que todas las pantallas se muestren correctamente.

## Estructura

```text
ContruHierro/
├── manage.py
├── requirements.txt
├── README.md
├── contruhierro/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── granja/
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── tests.py
    ├── urls.py
    ├── views.py
    ├── migrations/
    │   ├── 0001_initial.py
    │   ├── 0002_cochino_origen.py
    │   └── 0003_pagos_y_padres.py
    ├── static/granja/img/
    │   ├── cochino-icon.svg
    │   ├── cochino-banner.jpg
    │   └── cochinos-familia.jpg
    └── templates/granja/
        ├── base.html
        ├── login.html
        ├── dashboard.html
        ├── cochinos_lista.html
        ├── cochino_form.html
        ├── clientes_lista.html
        ├── cliente_form.html
        ├── ventas_lista.html
        ├── venta_form.html
        └── venta_detalle.html
```

## Antes de publicarlo en internet

Antes de desplegarlo en producción, configura una clave secreta propia mediante variables de entorno, `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS, cookies seguras y archivos estáticos compilados. También conviene instalar y ejecutar la suite de pruebas en el entorno donde se vaya a desplegar.

## Reportes

En el menú **Reportes** encontrarás el inventario total, cochinos disponibles y vendidos, desgloses por sexo y raza, compras, animales criados en la granja, inversión en compras, ventas e ingresos por período. Puedes elegir las fechas e imprimir el reporte desde el navegador.

La ficha de cada cochino ahora incluye el campo **Origen** (comprado, criado en la granja o sin especificar). Al aplicar la migración, los registros antiguos con un costo de compra mayor que cero se marcan como **Comprado**; los demás quedan como **Sin especificar** para evitar asumir datos que no estaban guardados. Edita las fichas pendientes si conoces su origen. La fecha usada para filtrar los ingresos es la fecha en que el registro fue creado en el sistema.


## Datos de pago y genealogía en registros antiguos

La migración `0003_pagos_y_padres` no inventa información: las ventas anteriores quedan con el método «Sin especificar» y sin monto pagado (en pantalla se indica que se registraron antes de guardar los datos de pago). Los cochinos «Criados en la granja» que ya existían no tienen madre ni padre; si están disponibles, el sistema pedirá esos datos la próxima vez que se edite su ficha.
