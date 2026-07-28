from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    
    # Verificamos si la tabla productos existe pero no tiene la columna UNIQUE o necesitamos actualizarla
    try:
        cursor.execute("SELECT codigo FROM productos LIMIT 1")
    except sqlite3.OperationalError:
        # Si la tabla no existe o falla, la creamos desde cero limpiamente
        cursor.execute("DROP TABLE IF EXISTS productos")
        cursor.execute('''
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nombre TEXT,
                categoria TEXT,
                precio REAL,
                costo REAL,
                stock REAL
            )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cajero TEXT,
            detalle TEXT,
            total_dolares REAL,
            total_bolivares REAL,
            tasa REAL,
            fecha TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return "Servidor POS Online funcionando correctamente"

@app.route("/productos", methods=["GET", "POST"])
def manejar_productos():
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    if request.method == "POST":
        data = request.json
        try:
            cursor.execute("""
                INSERT INTO productos (codigo, nombre, categoria, precio, costo, stock)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo) DO UPDATE SET
                nombre=excluded.nombre, categoria=excluded.categoria, 
                precio=excluded.precio, costo=excluded.costo, stock=excluded.stock
            """, (data.get("codigo"), data.get("nombre"), data.get("categoria"), data.get("precio"), data.get("costo"), data.get("stock")))
            conn.commit()
            conn.close()
            return jsonify({"status": "ok"})
        except Exception as e:
            conn.close()
            return jsonify({"error": str(e)}), 400
    else:
        cursor.execute("SELECT codigo, nombre, categoria, precio, costo, stock FROM productos")
        rows = cursor.fetchall()
        conn.close()
        prods = []
        for r in rows:
            prods.append({
                "codigo": r[0], "nombre": r[1], "categoria": r[2], 
                "precio": r[3], "costo": r[4], "stock": r[5]
            })
        return jsonify(prods)

@app.route("/ventas", methods=["POST"])
def registrar_venta():
    data = request.json
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ventas (cajero, detalle, total_dolares, total_bolivares, tasa, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data.get("cajero"), data.get("detalle"), data.get("total_dolares"), data.get("total_bolivares"), data.get("tasa"), data.get("fecha")))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
