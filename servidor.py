from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

DB_NAME = "pos_central.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla de productos centralizada
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
    # Tabla de ventas centralizada
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

# --- ENDPOINTS PRODUCTOS ---
@app.route("/productos", methods=["GET", "POST"])
def manejar_productos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        
        # Permite recibir tanto un solo producto como una lista
        if not isinstance(data, list):
            data = [data]

        for p in data:
            cursor.execute('''
                INSERT INTO productos (codigo, nombre, categoria, precio, costo, stock)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre=excluded.nombre,
                    categoria=excluded.categoria,
                    precio=excluded.precio,
                    costo=excluded.costo,
                    stock=excluded.stock
            ''', (
                p.get("codigo"),
                p.get("nombre"),
                p.get("categoria", "General"),
                p.get("precio", 0.0),
                p.get("costo", 0.0),
                p.get("stock", 0.0)
            ))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "mensaje": "Productos sincronizados"}), 201

    else:
        cursor.execute("SELECT codigo, nombre, categoria, precio, costo, stock FROM productos")
        filas = cursor.fetchall()
        conn.close()
        
        resultado = []
        for f in filas:
            resultado.append({
                "codigo": f[0],
                "nombre": f[1],
                "categoria": f[2],
                "precio": f[3],
                "costo": f[4],
                "stock": f[5]
            })
        return jsonify(resultado), 200

# --- ENDPOINTS VENTAS ---
@app.route("/ventas", methods=["GET", "POST"])
def manejar_ventas():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        cursor.execute('''
            INSERT INTO ventas (cajero, detalle, total_dolares, total_bolivares, tasa, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get("cajero", "Desconocido"),
            data.get("detalle", ""),
            data.get("total_dolares", 0.0),
            data.get("total_bolivares", 0.0),
            data.get("tasa", 0.0),
            data.get("fecha", "")
        ))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "mensaje": "Venta registrada"}), 201

    else:
        cursor.execute("SELECT id, cajero, detalle, total_dolares, total_bolivares, tasa, fecha FROM ventas")
        filas = cursor.fetchall()
        conn.close()
        
        resultado = []
        for f in filas:
            resultado.append({
                "id": f[0],
                "cajero": f[1],
                "detalle": f[2],
                "total_dolares": f[3],
                "total_bolivares": f[4],
                "tasa": f[5],
                "fecha": f[6]
            })
        return jsonify(resultado), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
