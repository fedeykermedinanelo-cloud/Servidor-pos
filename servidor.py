from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("pos_central.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
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

init_db()

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
            # Soporta tanto una lista de productos como un solo producto
            items = data if isinstance(data, list) else [data]
            for p in items:
                cursor.execute("""
                    INSERT INTO productos (codigo, nombre, categoria, precio, costo, stock)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo) DO UPDATE SET
                        nombre=excluded.nombre,
                        categoria=excluded.categoria,
                        precio=excluded.precio,
                        costo=excluded.costo,
                        stock=excluded.stock
                """, (p.get("codigo"), p.get("nombre"), p.get("categoria"), p.get("precio"), p.get("costo"), p.get("stock")))
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
    app.run(host="0.0.0.0", port=10000)
