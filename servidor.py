from flask import Flask, request, jsonify
import os
from supabase import create_client, Client

app = Flask(__name__)

# --- CONFIGURACIÓN DE SUPABASE ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")

# --- FUNCIONES AUXILIARES DE PERSISTENCIA EN SUPABASE ---
def leer_json(key_name, default):
    if not supabase:
        return default
    try:
        response = supabase.table("app_storage").select("data").eq("key", key_name).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["data"]
    except Exception as e:
        print(f"Error leyendo {key_name} de Supabase: {e}")
    return default

def guardar_json(key_name, datos):
    if not supabase:
        print("Supabase no está configurado.")
        return False
    try:
        # Usamos upsert para insertar o actualizar el registro basado en la 'key'
        supabase.table("app_storage").upsert({"key": key_name, "data": datos}).execute()
        return True
    except Exception as e:
        print(f"Error guardando {key_name} en Supabase: {e}")
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
        guardar_json("server_config", data)
        return jsonify({"status": "success", "message": "Configuración actualizada"}), 200
    else:
        config = leer_json("server_config", config_default)
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
        guardar_json("server_usuarios", data)
        return jsonify({"status": "success", "message": "Usuarios sincronizados"}), 200
    else:
        usuarios = leer_json("server_usuarios", usuarios_default)
        return jsonify(usuarios), 200

# --- CONTROL DE SESIONES ACTIVAS (Una computadora por usuario) ---
@app.route('/sesiones/verificar', methods=['GET'])
def verificar_sesion():
    usuario = request.args.get("usuario", "")
    sesiones = leer_json("server_sesiones", {})
    activo = sesiones.get(usuario, False)
    return jsonify({"activo": activo}), 200

@app.route('/sesiones/iniciar', methods=['POST'])
def iniciar_sesion():
    data = request.json
    usuario = data.get("usuario")
    if usuario:
        sesiones = leer_json("server_sesiones", {})
        sesiones[usuario] = True
        guardar_json("server_sesiones", sesiones)
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Usuario no especificado"}), 400

@app.route('/sesiones/cerrar', methods=['POST'])
def cerrar_sesion():
    data = request.json
    usuario = data.get("usuario")
    if usuario:
        sesiones = leer_json("server_sesiones", {})
        sesiones[usuario] = False
        guardar_json("server_sesiones", sesiones)
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Usuario no especificado"}), 400

# --- RUTAS DE PRODUCTOS ---
@app.route('/productos', methods=['GET', 'POST'])
def manejar_productos():
    productos = leer_json("server_productos", [])
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
            
        guardar_json("server_productos", productos)
        return jsonify({"status": "success", "message": "Producto guardado"}), 201
    else:
        return jsonify(productos), 200

# --- RUTAS DE VENTAS Y REVERSIÓN ---
@app.route('/ventas', methods=['GET', 'POST'])
def manejar_ventas():
    ventas = leer_json("server_ventas", [])
    if request.method == 'POST':
        nueva_venta = request.json
        nueva_venta["id"] = len(ventas) + 1
        ventas.append(nueva_venta)
        guardar_json("server_ventas", ventas)
        
        # Descontar stock al vender de forma segura
        lista_items = nueva_venta.get("items", nueva_venta.get("productos", []))
        if lista_items:
            productos_server = leer_json("server_productos", [])
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
            guardar_json("server_productos", productos_server)

        return jsonify({"status": "success", "id": nueva_venta["id"]}), 201
    else:
        return jsonify(ventas), 200

@app.route('/ventas/<int:venta_id>', methods=['DELETE'])
def eliminar_venta(venta_id):
    ventas = leer_json("server_ventas", [])
    
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
        productos_server = leer_json("server_productos", [])
        
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
                    
        guardar_json("server_productos", productos_server)

    guardar_json("server_ventas", ventas_filtradas)
    return jsonify({"status": "success", "message": f"Venta {venta_id} revertida y stock restaurado"}), 200

@app.route('/ventas/reset', methods=['DELETE'])
def reset_ventas():
    guardar_json("server_ventas", [])
    return jsonify({"status": "success", "message": "Historial de ventas reiniciado"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
