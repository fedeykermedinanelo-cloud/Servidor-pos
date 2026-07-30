from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Archivos de persistencia en el servidor
CONFIG_SERVER_FILE = "server_config.json"
PRODUCTS_SERVER_FILE = "server_productos.json"
SALES_SERVER_FILE = "server_ventas.json"
USERS_SERVER_FILE = "server_usuarios.json"
SESSIONS_SERVER_FILE = "server_sesiones.json"

# --- FUNCIONES AUXILIARES DE PERSISTENCIA ---
def leer_json(archivo, default):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def guardar_json(archivo, datos):
    try:
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error guardando {archivo}: {e}")
        return False

# --- RUTAS DE CONFIGURACIÓN ---
@app.route('/configuracion', methods=['GET', 'POST'])
def manejar_configuracion():
    config_default = {
        "url_servidor": "https://servidor-pos-j3tn.onrender.com",
        "tasa_bcv": 36.50,
        "correo_destino": "",
        "correo_emisor": "",
        "pass_emisor": "",
        "actualizar_tasa_auto": "Sí"
    }
    if request.method == 'POST':
        data = request.json
        guardar_json(CONFIG_SERVER_FILE, data)
        return jsonify({"status": "success", "message": "Configuración actualizada"}), 200
    else:
        config = leer_json(CONFIG_SERVER_FILE, config_default)
        return jsonify(config), 200

# --- RUTAS DE USUARIOS ---
@app.route('/usuarios', methods=['GET', 'POST'])
def manejar_usuarios():
    usuarios_default = {
        "Administrador": ["admin123", "Administrador"],
        "Caja 1": ["caja123", "Cajero"],
        "Caja 2": ["caja456", "Cajero"],
        "Caja 3": ["caja789", "Cajero"]
    }
    if request.method == 'POST':
        data = request.json
        guardar_json(USERS_SERVER_FILE, data)
        return jsonify({"status": "success", "message": "Usuarios sincronizados"}), 200
    else:
        usuarios = leer_json(USERS_SERVER_FILE, usuarios_default)
        return jsonify(usuarios), 200

# --- CONTROL DE SESIONES ACTIVAS (Una computadora por usuario) ---
@app.route('/sesiones/verificar', methods=['GET'])
def verificar_sesion():
    usuario = request.args.get("usuario", "")
    sesiones = leer_json(SESSIONS_SERVER_FILE, {})
    activo = sesiones.get(usuario, False)
    return jsonify({"activo": activo}), 200

@app.route('/sesiones/iniciar', methods=['POST'])
def iniciar_sesion():
    data = request.json
    usuario = data.get("usuario")
    if usuario:
        sesiones = leer_json(SESSIONS_SERVER_FILE, {})
        sesiones[usuario] = True
        guardar_json(SESSIONS_SERVER_FILE, sesiones)
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Usuario no especificado"}), 400

@app.route('/sesiones/cerrar', methods=['POST'])
def cerrar_sesion():
    data = request.json
    usuario = data.get("usuario")
    if usuario:
        sesiones = leer_json(SESSIONS_SERVER_FILE, {})
        sesiones[usuario] = False
        guardar_json(SESSIONS_SERVER_FILE, sesiones)
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Usuario no especificado"}), 400

# --- RUTAS DE PRODUCTOS ---
@app.route('/productos', methods=['GET', 'POST'])
def manejar_productos():
    productos = leer_json(PRODUCTS_SERVER_FILE, [])
    if request.method == 'POST':
        nuevo_prod = request.json
        codigo = str(nuevo_prod.get("codigo", "")).strip().lower()
        
        # Buscar si ya existe por código para actualizarlo o agregarlo
        encontrado = False
        for i, p in enumerate(productos):
            if str(p.get("codigo", "")).strip().lower() == codigo:
                productos[i] = nuevo_prod
                encontrado = True
                break
        if not encontrado:
            # Asignar ID autoincrementable si no lo tiene
            nuevo_prod["id"] = len(productos) + 1
            productos.append(nuevo_prod)
            
        guardar_json(PRODUCTS_SERVER_FILE, productos)
        return jsonify({"status": "success", "message": "Producto guardado"}), 201
    else:
        return jsonify(productos), 200

# --- RUTAS DE VENTAS Y REVERSIÓN ---
@app.route('/ventas', methods=['GET', 'POST'])
def manejar_ventas():
    ventas = leer_json(SALES_SERVER_FILE, [])
    if request.method == 'POST':
        nueva_venta = request.json
        nueva_venta["id"] = len(ventas) + 1
        ventas.append(nueva_venta)
        guardar_json(SALES_SERVER_FILE, ventas)
        return jsonify({"status": "success", "id": nueva_venta["id"]}), 201
    else:
        return jsonify(ventas), 200

@app.route('/ventas/<int:venta_id>', methods=['DELETE'])
def eliminar_venta(venta_id):
    ventas = leer_json(SALES_SERVER_FILE, [])
    ventas_filtradas = [v for v in ventas if int(v.get("id", 0)) != venta_id]
    
    if len(ventas_filtradas) == len(ventas):
        # Intentar buscar por coincidencia si el ID difiere
        ventas_filtradas = [v for v in ventas if str(v.get("id")) != str(venta_id)]

    guardar_json(SALES_SERVER_FILE, ventas_filtradas)
    return jsonify({"status": "success", "message": f"Venta {venta_id} revertida/eliminada"}), 200

@app.route('/ventas/reset', methods=['DELETE'])
def reset_ventas():
    guardar_json(SALES_SERVER_FILE, [])
    return jsonify({"status": "success", "message": "Historial de ventas reiniciado"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
