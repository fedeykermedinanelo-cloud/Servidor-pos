from flask import Flask, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)

def init_server_db():
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS productos (id TEXT PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER, categoria TEXT, imagen TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, cajero TEXT, detalle TEXT, total REAL, fecha TEXT)")
    conn.commit()
    conn.close()

init_server_db()

@app.route("/productos", methods=["GET"])
def obtener_productos():
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, stock, categoria, imagen FROM productos")
    rows = cursor.fetchall()
    conn.close()
    productos = [{"id": r[0], "nombre": r[1], "precio": r[2], "stock": r[3], "categoria": r[4], "imagen": r[5]} for r in rows]
    return jsonify(productos)

@app.route("/productos", methods=["POST"])
def guardar_o_actualizar_producto():
    data = request.json
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO productos (id, nombre, precio, stock, categoria, imagen) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
            nombre=excluded.nombre, precio=excluded.precio, stock=excluded.stock, categoria=excluded.categoria, imagen=excluded.imagen
        """, (
            str(data.get("codigo")), 
            data.get("nombre"),
            data.get("precio"),
            data.get("stock"),
            data.get("categoria"),
            data.get("imagen", "")
        ))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Producto sincronizado en la nube"})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/ventas", methods=["POST"])
def registrar_venta():
    data = request.json
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ventas (cajero, detalle, total, fecha) VALUES (?, ?, ?, ?)",
                       (data.get("cajero"), data.get("detalle"), data.get("total"), data.get("fecha")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Venta sincronizada y guardada en la nube"})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
