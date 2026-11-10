"""ArtesaníasPlus - Gestión de pedidos (caso práctico).

Aplicación Flask que:
  * registra pedidos desde un formulario o desde un archivo Excel;
  * clasifica cada pedido en Completo, En proceso o Por verificar;
  * guarda los pedidos en MySQL y deja un historial de cambios que nunca se borra.
"""
import io
import os
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pymysql
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook, load_workbook

load_dotenv()
app = Flask(__name__)

ESTADOS_PAGO = ["Pagado", "Pendiente"]
ESTADOS_ENVIO = ["Pendiente", "Enviado", "Entregado"]
COLUMNAS = ["ID pedido", "Cliente", "Producto", "Monto (USD)", "Estado pago",
            "Estado envío", "Número de guía", "Notas", "Fecha"]
# Nombres de columna aceptados (sin acentos ni espacios) -> campo interno
ALIAS = {
    "idpedido": "id", "id": "id", "cliente": "cliente", "producto": "producto",
    "montousd": "monto", "monto": "monto", "estadopago": "estado_pago", "pago": "estado_pago",
    "estadoenvio": "estado_envio", "envio": "estado_envio", "numerodeguia": "guia",
    "guia": "guia", "notas": "notas", "fecha": "fecha",
}
CAMPOS = ["cliente", "producto", "monto", "estado_pago", "estado_envio", "guia", "notas", "fecha"]


# ---------------------------------------------------------------- utilidades
def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "artesanias_plus"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def sin_acentos(valor):
    texto = unicodedata.normalize("NFD", str(valor or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def opcion(valor, opciones):
    """Devuelve la opción que coincide (ignorando mayúsculas y acentos) o None."""
    buscado = sin_acentos(valor)
    for o in opciones:
        if sin_acentos(o) == buscado:
            return o
    return None


def parse_fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return datetime.strptime(valor.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


# ------------------------------------------------------- reglas de negocio
def clasificar(p):
    """Criterios del caso: Completo, En proceso o Por verificar."""
    guia = p.get("guia") or ""
    falta = (not p.get("cliente") or not p.get("producto") or p.get("monto") is None
             or not p.get("estado_pago") or not p.get("estado_envio")
             or (p.get("estado_envio") == "Entregado" and not guia))
    if falta:
        return "Por verificar"
    if p["estado_pago"] == "Pendiente" and p["estado_envio"] != "Pendiente":
        return "Por verificar"  # contradictorio: enviado sin pagar
    if p["estado_pago"] == "Pagado" and p["estado_envio"] == "Entregado":
        return "Completo"
    return "En proceso"


def normalizar(o):
    """Valida un pedido crudo (formulario o fila de Excel). Devuelve (pedido, error)."""
    pedido = {
        "id": str(o.get("id") or "").strip(),
        "cliente": str(o.get("cliente") or "").strip(),
        "producto": str(o.get("producto") or "").strip(),
        "monto": None,
        "estado_pago": opcion(o.get("estado_pago"), ESTADOS_PAGO),
        "estado_envio": opcion(o.get("estado_envio"), ESTADOS_ENVIO),
        "guia": str(o.get("guia") or "").strip(),
        "notas": str(o.get("notas") or "").strip(),
        "fecha": parse_fecha(o.get("fecha")),
    }
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", pedido["id"]):
        return None, "el ID es obligatorio (solo letras, números, guion o guion bajo)"
    if not pedido["cliente"]:
        return None, "falta el cliente"
    if not pedido["producto"]:
        return None, "falta el producto"
    try:
        texto = str(o.get("monto") or "").replace("USD", "").replace("$", "").replace(",", ".").strip()
        pedido["monto"] = Decimal(texto)
    except (InvalidOperation, ValueError):
        return None, "el monto debe ser un número"
    if pedido["estado_pago"] is None:
        return None, "el estado de pago debe ser Pagado o Pendiente"
    if pedido["estado_envio"] is None:
        return None, "el estado de envío debe ser Pendiente, Enviado o Entregado"
    return pedido, None


def registrar(cur, pedido_id, tipo, detalle, origen, ahora):
    cur.execute(
        "INSERT INTO historial (pedido_id, fecha, tipo, detalle, origen) VALUES (%s,%s,%s,%s,%s)",
        (pedido_id, ahora, tipo, detalle, origen),
    )


def guardar(pedidos, origen):
    """Alta o actualización de pedidos en una sola transacción, con historial."""
    resumen = {"nuevos": 0, "cambiados": 0, "sin_cambios": 0}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for p in pedidos:
                ahora = datetime.now()
                cur.execute("SELECT * FROM pedidos WHERE id=%s FOR UPDATE", (p["id"],))
                prev = cur.fetchone()
                if prev is None:
                    cur.execute(
                        "INSERT INTO pedidos (id, cliente, producto, monto, estado_pago, estado_envio,"
                        " guia, notas, fecha, actualizado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (p["id"], p["cliente"], p["producto"], p["monto"], p["estado_pago"],
                         p["estado_envio"], p["guia"], p["notas"], p["fecha"], ahora),
                    )
                    registrar(cur, p["id"], "Alta",
                              f'{p["cliente"]}, {p["producto"]}, USD {p["monto"]}, '
                              f'pago {p["estado_pago"]}, envío {p["estado_envio"]}', origen, ahora)
                    resumen["nuevos"] += 1
                    continue
                cambios = [c for c in CAMPOS if str(prev[c] or "") != str(p[c] or "")]
                if not cambios:
                    resumen["sin_cambios"] += 1
                    continue
                cur.execute(
                    "UPDATE pedidos SET cliente=%s, producto=%s, monto=%s, estado_pago=%s,"
                    " estado_envio=%s, guia=%s, notas=%s, fecha=%s, actualizado=%s WHERE id=%s",
                    (p["cliente"], p["producto"], p["monto"], p["estado_pago"], p["estado_envio"],
                     p["guia"], p["notas"], p["fecha"], ahora, p["id"]),
                )
                detalle = "; ".join(f"{c}: {prev[c] or '—'} → {p[c] or '—'}" for c in cambios)
                registrar(cur, p["id"], "Cambio", detalle, origen, ahora)
                resumen["cambiados"] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return resumen


# ------------------------------------------------------------------ rutas
@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/pedidos")
def listar_pedidos():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pedidos ORDER BY id")
            filas = cur.fetchall()
    finally:
        conn.close()
    for f in filas:
        f["monto"] = float(f["monto"])
        f["fecha"] = f["fecha"].isoformat() if f["fecha"] else ""
        f["actualizado"] = f["actualizado"].isoformat()
        f["categoria"] = clasificar(f)
    return jsonify(filas)


@app.get("/api/historial")
def listar_historial():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pedido_id, fecha, tipo, detalle, origen FROM historial"
                        " ORDER BY fecha DESC, id DESC LIMIT 200")
            filas = cur.fetchall()
    finally:
        conn.close()
    for f in filas:
        f["fecha"] = f["fecha"].isoformat()
    return jsonify(filas)


@app.post("/api/pedidos")
def crear_o_actualizar():
    datos = request.get_json(silent=True) or {}
    pedido, error = normalizar(datos)
    if error:
        return jsonify(error=error), 400
    return jsonify(resumen=guardar([pedido], "formulario"))


@app.post("/api/pedidos/<pedido_id>/envio")
def cambiar_envio(pedido_id):
    estado = opcion((request.get_json(silent=True) or {}).get("estado"), ESTADOS_ENVIO)
    if estado is None:
        return jsonify(error="estado de envío no válido"), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pedidos WHERE id=%s", (pedido_id,))
            prev = cur.fetchone()
    finally:
        conn.close()
    if prev is None:
        return jsonify(error="pedido no encontrado"), 404
    prev["estado_envio"] = estado
    return jsonify(resumen=guardar([prev], "web"))


@app.post("/api/importar")
def importar_excel():
    archivo = request.files.get("archivo")
    if archivo is None:
        return jsonify(error="Sube un archivo Excel (.xlsx)."), 400
    try:
        wb = load_workbook(archivo, data_only=True, read_only=True)
    except Exception:
        return jsonify(error="El archivo no es un Excel válido (.xlsx)."), 400
    filas = wb.worksheets[0].iter_rows(values_only=True)
    cabecera = next(filas, None)
    if not cabecera:
        return jsonify(error="El archivo no tiene encabezados."), 400
    campos = [ALIAS.get(sin_acentos(c)) for c in cabecera]
    if "id" not in campos or "cliente" not in campos:
        return jsonify(error="Faltan columnas obligatorias (ID pedido, Cliente, ...)."), 400

    validas, errores = [], []
    for i, fila in enumerate(filas, start=2):
        if not fila or all(v in (None, "") for v in fila):
            continue
        o = {campo: fila[j] for j, campo in enumerate(campos) if campo and j < len(fila)}
        pedido, error = normalizar(o)
        if error:
            errores.append(f"fila {i}: {error}")
        else:
            validas.append(pedido)
    resumen = guardar(validas, "Excel") if validas else {"nuevos": 0, "cambiados": 0, "sin_cambios": 0}
    return jsonify(resumen=resumen, errores=errores)


@app.get("/api/plantilla")
def descargar_plantilla():
    wb = Workbook()
    ws = wb.active
    ws.title = "Pedidos"
    ws.append(COLUMNAS)
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    info = wb.create_sheet("Instrucciones")
    for linea in [
        "Cómo llenar la plantilla",
        "Una fila por pedido. No cambies los nombres de las columnas.",
        "ID pedido: código único, por ejemplo P002. Si ya existe, el pedido se actualiza.",
        "Monto (USD): solo el número, por ejemplo 45.",
        "Estado pago: Pagado o Pendiente.",
        "Estado envío: Pendiente, Enviado o Entregado.",
        "Número de guía: obligatorio si el envío está Entregado.",
        "Fecha: por ejemplo 2024-09-20.",
    ]:
        info.append([linea])
    info.column_dimensions["A"].width = 90
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="plantilla_pedidos.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.errorhandler(pymysql.MySQLError)
def error_base_datos(e):
    app.logger.exception("Error de base de datos")
    return jsonify(error="No se pudo acceder a la base de datos."), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", "5000")))
