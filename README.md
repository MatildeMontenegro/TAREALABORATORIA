# ArtesaníasPlus · Gestión de pedidos

Caso práctico: una aplicación web para que una micro-pyme registre sus pedidos,
los clasifique automáticamente y vea un dashboard actualizado desde el celular o
el computador. Los pedidos entran por formulario o por un archivo Excel.

Los datos de ejemplo son ficticios.

## Funcionalidades

- Dashboard con indicadores: pedidos, monto total, completos, en proceso y por verificar.
- Clasificación automática según reglas de negocio (ver `app.py`, función `clasificar`).
- Formulario para agregar o actualizar un pedido.
- Carga masiva desde Excel (.xlsx), con plantilla descargable y validación fila por fila.
- Cambio de estado de envío con un botón.
- Historial de cambios que solo crece: cada alta, actualización y cambio de estado queda registrado.

## Requisitos

- Python 3.10 o superior
- MySQL 8 o MariaDB 10.5 o superior

## Instalación

```bash
# 1. Crear la base de datos
mysql -u root -p < schema.sql

# 2. Crear el usuario de la aplicación (ajusta la clave)
mysql -u root -p -e "CREATE USER 'artesanias'@'localhost' IDENTIFIED BY 'cambia_esta_clave';
GRANT SELECT, INSERT, UPDATE ON artesanias_plus.* TO 'artesanias'@'localhost';"

# 3. Entorno Python
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. Configuración
cp .env.example .env               # y edita DB_PASSWORD

# 5. Ejecutar
python app.py                      # abre http://localhost:5000
```

En producción usa un servidor WSGI en lugar de `python app.py`, por ejemplo:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

y pon Nginx delante como proxy inverso.

## Uso

1. Abre la página y revisa el dashboard.
2. Para un pedido nuevo, usa el formulario "Agregar un pedido".
3. Para muchos pedidos, descarga la plantilla, rellénala en Excel y súbela.
4. Para agregar el número de guía, vuelve a cargar el pedido con el mismo ID.

## Pruebas

```bash
pytest -q tests
```

Las pruebas cubren las reglas de clasificación y la validación de datos. No requieren base de datos.

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/pedidos` | Lista pedidos con su categoría |
| GET | `/api/historial` | Últimos 200 movimientos |
| POST | `/api/pedidos` | Crea o actualiza un pedido (JSON) |
| POST | `/api/pedidos/<id>/envio` | Cambia el estado de envío (`{"estado": "Enviado"}`) |
| POST | `/api/importar` | Sube un Excel (campo `archivo`) |
| GET | `/api/plantilla` | Descarga la plantilla Excel |

## Estructura

```
.
├── app.py                 # Aplicación Flask: reglas, rutas y acceso a MySQL
├── schema.sql             # Tablas pedidos e historial
├── templates/index.html   # Dashboard (HTML, CSS y JavaScript)
├── static/logo_m2ia.png   # Logo
├── tests/test_reglas.py   # Pruebas de reglas de negocio
├── requirements.txt
├── .env.example
└── INFORME_EJECUTIVO.md   # Informe ejecutivo del proyecto
```

## Limitaciones conocidas

- No tiene inicio de sesión. Debe publicarse solo dentro de la red interna o detrás de autenticación del servidor web.
- Los montos aceptan punto o coma decimal; los separadores de miles no están soportados.
- No hay copias de seguridad automáticas: configura un respaldo diario de MySQL.
