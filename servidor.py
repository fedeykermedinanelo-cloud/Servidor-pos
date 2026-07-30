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
        
        encontrado = False
        for i, p in enumerate(productos):
            if str(p.get("codigo", "")).strip().lower() == codigo:
                productos[i] = nuevo_prod
                encontrado = True
                break
        if not encontrado:
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
        
        # Descontar stock al vender de forma segura
        lista_items = nueva_venta.get("items", nueva_venta.get("productos", []))
        if lista_items:
            productos_server = leer_json(PRODUCTS_SERVER_FILE, [])
            for item_vendido in lista_items:
                cod_vendido = str(item_vendido.get("codigo", "")).strip().lower()
                cant_vendida = float(item_vendido.get("cantidad", item_vendido.get("cant", 1)))
                
                for p in productos_server:
                    if str(p.get("codigo", "")).strip().lower() == cod_vendido:
                        stock_actual = float(p.get("stock", p.get("stock_disp", 0)))
                        p["stock"] = max(0.0, stock_actual - cant_vendida)
                        if "stock_disp" in p:
                            p["stock_disp"] = p["stock"]
                        break
            guardar_json(PRODUCTS_SERVER_FILE, productos_server)

        return jsonify({"status": "success", "id": nueva_venta["id"]}), 201
    else:
        return jsonify(ventas), 200

@app.route('/ventas/<int:venta_id>', methods=['DELETE'])
def eliminar_venta(venta_id):
    ventas = leer_json(SALES_SERVER_FILE, [])
    
    venta_a_revertir = None
    ventas_filtradas = []
    
    for v in ventas:
        if int(v.get("id", 0)) == int(venta_id) or str(v.get("id")) == str(venta_id):
            venta_a_revertir = v
        else:
            ventas_filtradas.append(v)
            
    if not venta_a_revertir:
        return jsonify({"error": "Venta ya revertida o no encontrada"}), 404

    # Revertir stock de forma estricta y controlada una sola vez
    lista_items = venta_a_revertir.get("items", [])
    if not lista_items:
        lista_items = venta_a_revertir.get("productos", [])

    if lista_items:
        productos_server = leer_json(PRODUCTS_SERVER_FILE, [])
        
        for item_vendido in lista_items:
            cod_vendido = str(item_vendido.get("codigo", "")).strip().lower()
            id_vendido = str(item_vendido.get("id", "")).strip()
            cant_vendida = float(item_vendido.get("cantidad", item_vendido.get("cant", 1)))
            
            actualizado = False
            for p in productos_server:
                if actualizado:
                    break
                    
                p_cod = str(p.get("codigo", "")).strip().lower()
                p_id = str(p.get("id", "")).strip()
                
                match_id = (p_id and id_vendido and p_id == id_vendido)
                match_cod = (p_cod and cod_vendido and p_cod == cod_vendido)
                
                if match_id or match_cod:
                    stock_actual = float(p.get("stock", p.get("stock_disp", 0)))
                    p["stock"] = stock_actual + cant_vendida
                    if "stock_disp" in p:
                        p["stock_disp"] = p["stock"]
                    actualizado = True
                    break
                    
        guardar_json(PRODUCTS_SERVER_FILE, productos_server)

    guardar_json(SALES_SERVER_FILE, ventas_filtradas)
    return jsonify({"status": "success", "message": f"Venta {venta_id} revertida y stock restaurado"}), 200

@app.route('/ventas/reset', methods=['DELETE'])
def reset_ventas():
    guardar_json(SALES_SERVER_FILE, [])
    return jsonify({"status": "success", "message": "Historial de ventas reiniciado"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
