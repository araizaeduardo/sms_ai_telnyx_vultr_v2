from flask import Flask, request, render_template, jsonify, redirect, url_for
import telnyx
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import os
import openai
import hmac
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Configurar API key de Telnyx desde variables de entorno
telnyx.api_key = os.getenv('TELNYX_API_KEY')

# Otras configuraciones desde variables de entorno
DB_NAME = os.getenv('DB_NAME', 'crm_pipeline.db')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://paseotravelclientes.resvoyage.com')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '818-244-2184')

# Agregar configuración de base de datos y funciones relacionadas

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            telefono TEXT,
            mensaje TEXT,
            respuesta TEXT,
            fecha_contacto TEXT,
            estado TEXT DEFAULT 'Pendiente'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            mensaje TEXT,
            tipo TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    conn.commit()
    conn.close()
    
    logging.info("Base de datos inicializada correctamente")

def guardar_cliente(nombre, telefono, mensaje, estado="Pendiente", respuesta=None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clientes (nombre, telefono, mensaje, respuesta, fecha_contacto, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, telefono, mensaje, respuesta, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), estado))
        conn.commit()

# Reemplazar la configuración de Ollama con Vultr
VULTR_API_KEY = os.getenv('VULTR_CLOUD_INFERENCE_API_KEY')
VULTR_MODEL = os.getenv('VULTR_MODEL', 'mixtral-8x7b')

class VultrInferenceClient:
    def __init__(self, api_key=None):
        """Initialize the Vultr Inference Client"""
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.vultrinference.com/v1"
        )

    def ask_question(self, prompt, model="llama-3.1-70b-instruct-fp8-gh200", max_tokens=300, temperature=0.7):
        """Send a question to the Vultr Inference API"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error en la solicitud: {str(e)}"

def setup_logging():
    """Configure logging to write detailed logs to file and important ones to console"""
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Detailed formatter for file
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # Simpler formatter for console
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # File handler (detailed logging)
    log_file = os.path.join(logs_dir, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler (only important messages)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.WARNING)  # Only WARNING and above will show in console
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def generar_respuesta_ia(mensaje):
    logging.info("=== INICIO GENERACIÓN IA ===")
    try:
        logging.info(f"Mensaje a procesar: {mensaje}")
        
        # Verificar si el mensaje menciona vuelos
        if "vuelos" in mensaje.lower():
            return f"Te redirecciono a nuestro sistema de reservas donde podrás consultar precios y disponibilidad: {WEBSITE_URL}\nPor favor llámanos al {PHONE_NUMBER} para asistencia personalizada."
        
        # Inicializar cliente de Vultr
        client = VultrInferenceClient(api_key=VULTR_API_KEY)
        
        # Preparar el prompt con las instrucciones del sistema
        prompt = f"""Como agente de viajes y asistente de servicio al cliente que responde por SMS:
        - Responde de forma concisa y directa (ideal entre 100-300 caracteres)
        - Sé profesional pero amigable
        - No uses emojis
        - Usa español informal pero correcto
        - NO incluyas un número de teléfono en tu respuesta, se agregará automáticamente
        
        Pregunta del cliente: {mensaje}"""
        
        logging.info("Enviando solicitud a Vultr...")
        respuesta_ia = client.ask_question(prompt)
        
        # Agregar el número de teléfono a la respuesta
        respuesta_final = f"{respuesta_ia}\nPor favor llámanos al {PHONE_NUMBER} para más información."
        
        logging.info(f"Respuesta final: {respuesta_final}")
        return respuesta_final
            
    except Exception as e:
        logging.error(f"Error en generación IA: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        return "Lo sentimos, hay un problema técnico. Por favor llámanos al {PHONE_NUMBER} para más información."
    finally:
        logging.info("=== FIN GENERACIÓN IA ===")

def limpiar_numero_telefono(numero):
    # Eliminar cualquier carácter que no sea dígito o el signo '+'
    numero = ''.join(c for c in numero if c.isdigit() or c == '+')
    
    # Asegurarse de que el número tenga el formato internacional
    if not numero.startswith('+'):
        numero = '+1' + numero  # Asumiendo que es un número de EE.UU.
    
    # Verificar que el número tenga una longitud válida (E.164: máximo 15 dígitos)
    if len(numero.replace('+', '')) > 15:
        raise ValueError("Número de teléfono demasiado largo")
    
    return numero

# Add these new functions and configurations
TELNYX_PUBLIC_KEY = os.getenv('TELNYX_PUBLIC_KEY')  # Add this to your .env file

def verify_telnyx_signature(request_data, signature_header, timestamp_header):
    """Verify that the webhook request came from Telnyx"""
    if not TELNYX_PUBLIC_KEY:
        raise ValueError("TELNYX_PUBLIC_KEY is not configured")
        
    try:
        # Ensure request_data is a string if it's bytes
        if isinstance(request_data, bytes):
            request_data = request_data.decode('utf-8')
            
        # Convert timestamp to integer if it's a string
        if isinstance(timestamp_header, str):
            timestamp_header = int(timestamp_header)
            
        telnyx.Webhook.construct_event(
            request_data,
            signature_header,
            timestamp_header,
            TELNYX_PUBLIC_KEY
        )
        return True
    except ValueError as e:
        print(f"Timestamp conversion failed: {str(e)}")
        return False
    except Exception as e:
        print(f"Webhook verification failed: {str(e)}")
        return False

# Modificar la ruta SMS
@app.route("/sms", methods=["POST"])
def sms():
    logging.info("=== INICIO DE SOLICITUD SMS ===")
    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data)
        
        if data.get('data', {}).get('event_type') != 'message.received':
            logging.warning("Not a message event")
            return "Not a message event", 400
            
        payload = data['data']['payload']
        mensaje_entrante = payload.get('text', '')
        telefono_usuario = payload.get('from', {}).get('phone_number', '')
        
        telefono_usuario = limpiar_numero_telefono(telefono_usuario)
        
        # Verificar si existe un cliente con este teléfono hoy
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener la fecha actual en formato YYYY-MM-DD
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id FROM clientes 
            WHERE telefono = ? 
            AND date(fecha_contacto) = ?
        """, (telefono_usuario, hoy))
        
        cliente_existente = cursor.fetchone()
        
        if cliente_existente:
            # Si ya existe un cliente hoy, solo guardamos el mensaje en el historial
            cliente_id = cliente_existente[0]
            cursor.execute("""
                INSERT INTO historial_mensajes (cliente_id, mensaje, tipo)
                VALUES (?, ?, ?)
            """, (cliente_id, mensaje_entrante, 'recibido'))
            conn.commit()
            
            # Enviar notificación al panel de administración
            # (Aquí podrías implementar un sistema de notificaciones)
            
        else:
            # Si es el primer mensaje del día, usar IA para responder
            respuesta = generar_respuesta_ia(mensaje_entrante)
            
            # Guardar nuevo cliente
            cursor.execute("""
                INSERT INTO clientes (nombre, telefono, mensaje, respuesta, fecha_contacto, estado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Desconocido", telefono_usuario, mensaje_entrante, respuesta, 
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pendiente"))
            
            cliente_id = cursor.lastrowid
            
            # Guardar en historial
            cursor.execute("""
                INSERT INTO historial_mensajes (cliente_id, mensaje, tipo)
                VALUES (?, ?, ?)
            """, (cliente_id, mensaje_entrante, 'recibido'))
            
            # Enviar respuesta vía Telnyx
            telnyx.Message.create(
                from_=os.getenv('TELNYX_FROM_NUMBER'),
                to=telefono_usuario,
                text=respuesta,
                messaging_profile_id=os.getenv('TELNYX_MESSAGING_PROFILE_ID')
            )
            
            # Guardar respuesta en historial
            cursor.execute("""
                INSERT INTO historial_mensajes (cliente_id, mensaje, tipo)
                VALUES (?, ?, ?)
            """, (cliente_id, respuesta, 'enviado'))
            
        conn.commit()
        conn.close()
        
        return "OK", 200
        
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        logging.error(traceback.format_exc())
        return "Error processing webhook", 500

@app.route("/")
def index():
    return redirect(url_for('kanban'))

def validate_config():
    required_vars = [
        'TELNYX_API_KEY',
        'TELNYX_PUBLIC_KEY',
        'VULTR_CLOUD_INFERENCE_API_KEY',
        'TELNYX_FROM_NUMBER',
        'TELNYX_MESSAGING_PROFILE_ID'
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Agregar esta nueva ruta después de las rutas existentes
@app.route("/actualizar_estado", methods=["POST"])
def actualizar_estado():
    try:
        data = request.json
        mensaje_id = data.get('mensaje_id')
        nuevo_estado = data.get('estado')
        
        # Extraer el ID numérico del mensaje_id (eliminar el prefijo 'mensaje-')
        mensaje_id = mensaje_id.replace('mensaje-', '')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET estado = ? 
            WHERE id = ?
        """, (nuevo_estado, mensaje_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True}), 200
    except Exception as e:
        logging.error(f"Error actualizando estado: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/kanban")
def kanban():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Obtener todos los registros agrupados por estado
        cursor.execute("""
            SELECT 
                id,
                nombre,
                telefono,
                mensaje,
                respuesta,
                fecha_contacto,
                estado
            FROM clientes 
            ORDER BY fecha_contacto DESC
        """)
        
        clientes = cursor.fetchall()
        
        # Agregar logging para debug
        logging.info(f"Total de clientes recuperados: {len(clientes)}")
        for cliente in clientes:
            logging.info(f"Cliente ID: {cliente[0]}, Estado: {cliente[6]}, Teléfono: {cliente[2]}")
        
        # Organizar clientes por estado
        pendientes = [c for c in clientes if c[6] == 'Pendiente']
        en_proceso = [c for c in clientes if c[6] == 'En Proceso']
        en_revision = [c for c in clientes if c[6] == 'En Revisión']
        completados = [c for c in clientes if c[6] == 'Completado']
        
        # Logging de conteos
        logging.info(f"Pendientes: {len(pendientes)}")
        logging.info(f"En Proceso: {len(en_proceso)}")
        logging.info(f"En Revisión: {len(en_revision)}")
        logging.info(f"Completados: {len(completados)}")
        
        conn.close()
        
        return render_template("kanban.html", 
                             pendientes=pendientes,
                             en_proceso=en_proceso,
                             en_revision=en_revision,
                             completados=completados)
    except Exception as e:
        logging.error(f"Error recuperando datos: {str(e)}")
        return "Error recuperando datos", 500

@app.route("/last_update")
def last_update():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Obtener la fecha de la última actualización
        cursor.execute("""
            SELECT MAX(fecha_contacto)
            FROM clientes
        """)
        
        last_update = cursor.fetchone()[0] or ''
        conn.close()
        
        return jsonify({"last_update": last_update})
    except Exception as e:
        logging.error(f"Error checking last update: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/detalle/<int:id>')
def detalle_cliente(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener detalles del cliente
        cursor.execute('SELECT * FROM clientes WHERE id = ?', (id,))
        cliente = cursor.fetchone()
        
        # Obtener historial de mensajes agrupados por día
        cursor.execute('''
            SELECT 
                mensaje,
                tipo,
                strftime('%Y-%m-%d', fecha_hora) as fecha,
                strftime('%H:%M', fecha_hora) as hora
            FROM historial_mensajes 
            WHERE cliente_id = ? 
            ORDER BY fecha_hora DESC
        ''', (id,))
        mensajes = cursor.fetchall()
        
        # Agrupar mensajes por fecha
        historial_agrupado = {}
        for mensaje in mensajes:
            fecha = mensaje['fecha']
            if fecha not in historial_agrupado:
                historial_agrupado[fecha] = []
            historial_agrupado[fecha].append({
                'mensaje': mensaje['mensaje'],
                'tipo': mensaje['tipo'],
                'hora': mensaje['hora']
            })
        
        return render_template('detalle.html', 
                             cliente=cliente, 
                             historial_agrupado=historial_agrupado)
    except Exception as e:
        logging.error(f"Error al obtener detalles del cliente: {str(e)}")
        return f"ERROR: Error al obtener detalles del cliente: {str(e)}"
    finally:
        if conn:
            conn.close()

@app.route('/calendario')
def calendario():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nombre, telefono, mensaje, respuesta, 
                   fecha_contacto, estado
            FROM clientes 
            ORDER BY fecha_contacto DESC
        """)
        
        clientes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('calendario.html', 
                             clientes=clientes,
                             year=datetime.now().year)
        
    except Exception as e:
        logging.error(f"Error al obtener datos para el calendario: {str(e)}")
        return "Error al cargar el calendario", 500

# Agregar este filtro para la fecha en el template
@app.template_filter('now')
def datetime_format(value, format='%Y'):
    return datetime.now().strftime(format)

@app.route('/enviar-sms', methods=['POST'])
def enviar_sms():
    try:
        data = request.get_json()
        telefono = data['telefono']
        mensaje = data.get('mensaje', '')
        cliente_id = data.get('cliente_id')  # Necesitarás enviar esto desde el frontend
        
        # Enviar SMS con Telnyx
        telnyx.Message.create(
            from_=os.getenv('TELNYX_FROM_NUMBER'),
            to=telefono,
            text=mensaje,
            messaging_profile_id=os.getenv('TELNYX_MESSAGING_PROFILE_ID')
        )
        
        # Registrar en el historial
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historial_mensajes (cliente_id, mensaje, tipo)
            VALUES (?, ?, ?)
        ''', (data['cliente_id'], data['mensaje'], 'enviado'))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error enviando SMS: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    setup_logging()
    validate_config()
    init_db()
    app.run(debug=True, port=5005)
