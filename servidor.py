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
    # Tabla de configuración centralizada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT UNIQUE,
            valor TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "Servidor POS Online funcionando correctamente"

# --- ENDPOINTS CONFIGURACIÓN ---
@app.route("/configuracion", methods=["GET", "POST"])
def manejar_configuracion():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        if not data:
            conn.close()
            return jsonify({"status": "error", "mensaje": "No se recibieron datos"}), 400

        # Guardar cada clave/valor de la configuración en la base de datos
        for clave, valor in data.items():
            cursor.execute('''
                INSERT INTO configuracion (clave, valor)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    valor = excluded.valor
            ''', (clave, str(valor)))

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "mensaje": "Configuración sincronizada en la nube"}), 201

    else:
        cursor.execute("SELECT clave, valor FROM configuracion")
        filas = cursor.fetchall()
        conn.close()
        
        resultado = {}
        for f in filas:
            resultado[f[0]] = f[1]
            
        return jsonify(resultado), 200

# --- ENDPOINTS PRODUCTOS ---
@app.route("/productos", methods=["GET", "POST"])
def manejar_productos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        
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
        cursor.execute("SELECT id, codigo, nombre, categoria, precio, costo, stock FROM productos")
        filas = cursor.fetchall()
        conn.close()
        
        resultado = []
        for f in filas:
            resultado.append({
                "id": f[0],
                "codigo": f[1],
                "nombre": f[2],
                "categoria": f[3],
                "precio": f[4],
                "costo": f[5],
                "stock": f[6]
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
        
        items = data.get("items", [])
        for item in items:
            codigo = item.get("codigo")
            cantidad = float(item.get("cantidad", 0.0))
            if codigo and cantidad > 0:
                cursor.execute('''
                    UPDATE productos 
                    SET stock = MAX(0, stock - ?) 
                    WHERE codigo = ?
                ''', (cantidad, codigo))

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "mensaje": "Venta registrada e inventario actualizado"}), 201

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

# --- ENDPOINT RESTABLECER HISTORIAL DE VENTAS (PRUEBAS) ---
@app.route("/ventas/reset", methods=["POST", "DELETE"])
def reset_ventas():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ventas")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='ventas'")
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "mensaje": "Historial de ventas restablecido por completo"}), 200
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
