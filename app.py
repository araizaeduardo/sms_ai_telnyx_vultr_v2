from flask import Flask, request, render_template, jsonify, redirect, url_for, make_response
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
import traceback  # Agregar esta importación al inicio del archivo
import csv
from io import StringIO
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import numpy as np

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
    """Inicializa la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Crear tabla de documentos si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        contenido TEXT NOT NULL,
        tipo TEXT NOT NULL,
        embedding TEXT,
        activo INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Crear tabla de historial de mensajes si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historial_mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telefono TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        respuesta TEXT,
        estado TEXT DEFAULT 'pendiente',
        notas TEXT,
        fecha_recibido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_respondido TIMESTAMP
    )
    ''')

    # Verificar si la tabla configuracion existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracion'")
    if not cursor.fetchone():
        # Si no existe, crearla con la nueva estructura
        cursor.execute('''
        CREATE TABLE configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT UNIQUE NOT NULL,
            valor TEXT NOT NULL,
            descripcion TEXT,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Insertar configuración inicial
        cursor.execute('''
        INSERT INTO configuracion (clave, valor, descripcion)
        VALUES (
            'prompt_ia',
            'Eres un asistente virtual de una agencia de viajes. Tu objetivo es ayudar a los clientes con información sobre paquetes turísticos y reservaciones. Sé amable y profesional.',
            'Prompt base para el modelo de IA'
        )
        ''')
    else:
        # Si existe, asegurarse de que tenga el prompt_ia
        cursor.execute('SELECT valor FROM configuracion WHERE clave = "prompt_ia"')
        if not cursor.fetchone():
            cursor.execute('INSERT INTO configuracion (clave, valor) VALUES ("prompt_ia", ?)',
                         ('Eres un asistente virtual de una agencia de viajes. Tu objetivo es ayudar a los clientes con información sobre paquetes turísticos y reservaciones. Sé amable y profesional.',))

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
        logging.info("VultrInferenceClient inicializado")

    def ask_question(self, prompt, model="llama-3.1-70b-instruct-fp8", max_tokens=300, temperature=0.7):
        """Send a question to the Vultr Inference API"""
        try:
            logging.info(f"Enviando pregunta a Vultr - Modelo: {model}")
            logging.info(f"Configuración - max_tokens: {max_tokens}, temperature: {temperature}")
            
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            logging.info("Realizando llamada a la API de Vultr...")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            respuesta = response.choices[0].message.content
            logging.info("Respuesta recibida de Vultr exitosamente")
            return respuesta
            
        except Exception as e:
            logging.error(f"Error en Vultr Inference: {str(e)}")
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
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler (only important messages)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)  # Cambiar a DEBUG para ver más detalles
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Cambiar a DEBUG para ver más detalles
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# Variables globales
embedding_model = None

def get_embedding_model():
    """Obtiene o inicializa el modelo de embeddings"""
    global embedding_model
    if embedding_model is None:
        try:
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logging.error(f"Error al cargar el modelo de embeddings: {str(e)}")
            return None
    return embedding_model

def generar_embedding(texto, client):
    """Genera un embedding para el texto usando sentence-transformers"""
    try:
        logging.info("=== INICIO GENERACIÓN EMBEDDING ===")
        logging.info(f"Procesando texto de longitud: {len(texto)}")

        if not texto or not isinstance(texto, str):
            logging.error(f"Texto inválido para embedding: {texto}")
            return None

        # Limitar la longitud del texto
        texto_original = texto
        texto = texto[:8000]
        if len(texto) < len(texto_original):
            logging.info(f"Texto truncado de {len(texto_original)} a {len(texto)} caracteres")

        # Obtener el modelo
        logging.info("Obteniendo modelo de embeddings...")
        model = get_embedding_model()
        if model is None:
            logging.error("No se pudo cargar el modelo de embeddings")
            return None

        try:
            logging.info("Generando embedding...")
            embedding = model.encode([texto])[0]
            
            logging.info(f"Embedding generado - Dimensiones: {len(embedding)}")
            
            # Normalizar el vector
            if np.any(embedding):
                embedding = embedding / np.linalg.norm(embedding)
                logging.info("Embedding normalizado exitosamente")
                return embedding.tolist()
            else:
                logging.error("El embedding generado es un vector de ceros")
                return None

        except Exception as e:
            logging.error(f"Error al generar embedding: {str(e)}")
            return None

    except Exception as e:
        logging.error(f"Error general al generar embedding: {str(e)}")
        return None
    finally:
        logging.info("=== FIN GENERACIÓN EMBEDDING ===")

def generar_respuesta_ia(mensaje):
    logging.info("=== INICIO GENERACIÓN IA ===")
    try:
        logging.info(f"Mensaje a procesar: {mensaje}")
        
        # Inicializar cliente de Vultr
        logging.info("Inicializando cliente Vultr...")
        client = VultrInferenceClient(api_key=VULTR_API_KEY)
        
        # Generar embedding para la consulta
        logging.info("Generando embedding para la consulta...")
        query_embedding = generar_embedding(mensaje, client)
        
        # Buscar documentos relevantes
        logging.info("Iniciando búsqueda de documentos relevantes...")
        conn = get_db_connection()
        cursor = conn.cursor()
        documentos_relevantes = []
        
        if query_embedding:
            documentos_relevantes = buscar_documentos_relevantes(query_embedding, cursor, umbral=0.6)
            logging.info(f"Documentos relevantes encontrados: {len(documentos_relevantes)}")
        else:
            logging.warning("No se pudo generar embedding para la consulta")
        
        # Obtener el prompt base
        logging.info("Obteniendo prompt base...")
        cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', ('prompt_ia',))
        prompt_base = cursor.fetchone()[0]
        
        # Preparar contexto con documentos relevantes
        contexto_docs = ""
        if documentos_relevantes:
            contexto_docs = "\nInformación relevante disponible:\n"
            for doc in documentos_relevantes:
                contexto_docs += f"\n- {doc['tipo'].upper()}: {doc['contenido']}"
                logging.info(f"Usando documento: {doc['titulo']} (similitud: {doc['similitud']:.2f})")
        
        # Preparar el prompt completo
        logging.info("Preparando prompt completo...")
        prompt = f"""{prompt_base}

        {contexto_docs}

        Pregunta del cliente: {mensaje}

        Responde de manera natural, como si fueras un agente real conversando por SMS. 
        Si hay información relevante disponible, úsala en tu respuesta, pero mantén un tono conversacional."""
        
        logging.info("Enviando solicitud a Vultr para generar respuesta...")
        respuesta_ia = client.ask_question(prompt)
        
        # Agregar el número de teléfono a la respuesta
        respuesta_final = f"{respuesta_ia}\nPor favor llámanos al {PHONE_NUMBER} para más información."
        
        conn.close()
        logging.info("Conexión a base de datos cerrada")
        logging.info(f"Respuesta final generada: {respuesta_final}")
        return respuesta_final
            
    except Exception as e:
        logging.error(f"Error en generación IA: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        return f"Lo sentimos, hay un problema técnico. Por favor llámanos al {PHONE_NUMBER} para más información."
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
                INSERT INTO historial_mensajes (cliente_id, mensaje, tipo, estado)
                VALUES (?, ?, ?, ?)
            """, (cliente_id, mensaje_entrante, 'recibido', 0))
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
                INSERT INTO historial_mensajes (cliente_id, mensaje, tipo, estado)
                VALUES (?, ?, ?, ?)
            """, (cliente_id, mensaje_entrante, 'recibido', 0))
            
            # Enviar respuesta va Telnyx
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
            SELECT MAX(fecha_hora)
            FROM historial_mensajes
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
        
        # Modificar la consulta para incluir el ID del mensaje
        cursor.execute('''
            SELECT 
                id,
                mensaje,
                tipo,
                strftime('%Y-%m-%d', fecha_hora) as fecha,
                strftime('%H:%M', fecha_hora) as hora,
                estado,
                nota
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
                'id': mensaje['id'],
                'mensaje': mensaje['mensaje'],
                'tipo': mensaje['tipo'],
                'hora': mensaje['hora'],
                'estado': mensaje['estado'],
                'nota': mensaje['nota']
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

@app.route('/mark-as-read/<int:cliente_id>', methods=['POST'])
def mark_as_read(cliente_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Primero, verificamos si el cliente existe
        cursor.execute("SELECT id FROM clientes WHERE id = ?", (cliente_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404

        # Actualizamos el estado de los mensajes nuevos
        cursor.execute("""
            UPDATE historial_mensajes 
            SET leido = 1 
            WHERE cliente_id = ? 
            AND tipo = 'recibido' 
            AND (leido IS NULL OR leido = 0)
        """, (cliente_id,))
        
        # También podemos actualizar la tabla de clientes si es necesario
        cursor.execute("""
            UPDATE clientes 
            SET estado = CASE 
                WHEN estado = 'Pendiente' THEN 'En Proceso'
                ELSE estado 
            END
            WHERE id = ?
        """, (cliente_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})

    except Exception as e:
        logging.error(f"Error al marcar como leído: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# También necesitaremos una ruta para verificar mensajes nuevos
@app.route('/check-new-messages')
def check_new_messages():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Buscar mensajes no leídos
        cursor.execute("""
            SELECT DISTINCT c.id
            FROM clientes c
            JOIN historial_mensajes hm ON c.id = hm.cliente_id
            WHERE hm.tipo = 'recibido' 
            AND (hm.estado IS NULL OR hm.estado = 0)
            ORDER BY hm.fecha_hora DESC
        """)
        
        nuevos_mensajes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'nuevos_mensajes': nuevos_mensajes})

    except Exception as e:
        logging.error(f"Error al verificar mensajes nuevos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-kanban-data')
def get_kanban_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
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
        
        # Organizar clientes por estado
        pendientes = [list(c) for c in clientes if c[6] == 'Pendiente']
        en_proceso = [list(c) for c in clientes if c[6] == 'En Proceso']
        en_revision = [list(c) for c in clientes if c[6] == 'En Revisión']
        completados = [list(c) for c in clientes if c[6] == 'Completado']
        
        conn.close()
        
        return jsonify({
            'pendientes': pendientes,
            'en_proceso': en_proceso,
            'en_revision': en_revision,
            'completados': completados
        })
        
    except Exception as e:
        logging.error(f"Error obteniendo datos del kanban: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/actualizar-estado-mensaje', methods=['POST'])
def actualizar_estado_mensaje():
    try:
        data = request.get_json()
        mensaje_id = data['mensaje_id']
        estado = data['estado']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historial_mensajes 
            SET estado = ? 
            WHERE id = ?
        """, (estado, mensaje_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error actualizando estado del mensaje: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/guardar-nota-mensaje', methods=['POST'])
def guardar_nota_mensaje():
    try:
        data = request.get_json()
        mensaje_id = data['mensaje_id']
        nota = data['nota']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historial_mensajes 
            SET nota = ? 
            WHERE id = ?
        """, (nota, mensaje_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error guardando nota del mensaje: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-datos', methods=['POST'])
def exportar_datos():
    try:
        data = request.get_json()
        fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d')
        fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d') + timedelta(days=1)  # Incluir todo el día final
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener los datos filtrados por fecha
        cursor.execute("""
            SELECT 
                c.id,
                c.nombre,
                c.telefono,
                c.mensaje,
                c.respuesta,
                c.fecha_contacto,
                c.estado,
                hm.mensaje as historial_mensaje,
                hm.tipo as tipo_mensaje,
                hm.fecha_hora,
                hm.nota
            FROM clientes c
            LEFT JOIN historial_mensajes hm ON c.id = hm.cliente_id
            WHERE DATE(c.fecha_contacto) BETWEEN DATE(?) AND DATE(?)
            ORDER BY c.fecha_contacto DESC, hm.fecha_hora DESC
        """, (fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')))
        
        resultados = cursor.fetchall()
        
        # Crear archivo CSV en memoria
        si = StringIO()
        csv_writer = csv.writer(si)
        
        # Escribir encabezados
        headers = ['ID', 'Nombre', 'Teléfono', 'Mensaje Inicial', 'Respuesta Inicial', 
                  'Fecha Contacto', 'Estado', 'Mensaje Historial', 'Tipo Mensaje', 
                  'Fecha/Hora Mensaje', 'Nota']
        csv_writer.writerow(headers)
        
        # Escribir datos
        for row in resultados:
            csv_writer.writerow(row)
        
        # Preparar la respuesta
        output = si.getvalue()
        si.close()
        
        response = make_response(output)
        response.headers["Content-Disposition"] = f"attachment; filename=exportacion_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
        
    except Exception as e:
        logging.error(f"Error en la exportación: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def limpiar_base_datos():
    """Limpia todas las tablas de la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lista de tablas a limpiar
        tablas = ['documentos', 'mensajes', 'configuracion']
        
        for tabla in tablas:
            try:
                cursor.execute(f'DELETE FROM {tabla}')
                logging.info(f"Tabla {tabla} limpiada exitosamente")
            except Exception as e:
                logging.error(f"Error limpiando tabla {tabla}: {str(e)}")
        
        # Reiniciar los autoincrement
        cursor.execute("DELETE FROM sqlite_sequence")
        
        conn.commit()
        conn.close()
        logging.info("Base de datos limpiada exitosamente")
        
        # Reinicializar la base de datos
        init_db()
        logging.info("Base de datos reinicializada")
        
    except Exception as e:
        logging.error(f"Error limpiando la base de datos: {str(e)}")

@app.route('/limpiar-db', methods=['POST'])
def limpiar_db_endpoint():
    """Endpoint para limpiar la base de datos"""
    try:
        limpiar_base_datos()
        return jsonify({'success': True, 'message': 'Base de datos limpiada exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin')
def admin_panel():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Estadísticas generales con COALESCE para manejar NULLs
        cursor.execute("""
            SELECT 
                COUNT(*) as total_clientes,
                COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) as pendientes,
                COALESCE(SUM(CASE WHEN estado = 'En Proceso' THEN 1 ELSE 0 END), 0) as en_proceso,
                COALESCE(SUM(CASE WHEN estado = 'Completado' THEN 1 ELSE 0 END), 0) as completados
            FROM clientes
        """)
        stats_row = cursor.fetchone()
        # Convertir stats a diccionario
        stats = {
            'total_clientes': stats_row[0] if stats_row else 0,
            'pendientes': stats_row[1] if stats_row else 0,
            'en_proceso': stats_row[2] if stats_row else 0,
            'completados': stats_row[3] if stats_row else 0
        }
        
        # Mensajes por día con COALESCE
        cursor.execute("""
            SELECT 
                DATE(fecha_hora) as fecha,
                COUNT(*) as total_mensajes,
                COALESCE(SUM(CASE WHEN tipo = 'recibido' THEN 1 ELSE 0 END), 0) as recibidos,
                COALESCE(SUM(CASE WHEN tipo = 'enviado' THEN 1 ELSE 0 END), 0) as enviados
            FROM historial_mensajes
            WHERE fecha_hora >= date('now', '-7 days')
            GROUP BY DATE(fecha_hora)
            ORDER BY fecha DESC
        """)
        mensajes_rows = cursor.fetchall()
        # Convertir mensajes_por_dia a lista de diccionarios
        mensajes_por_dia = [
            {
                'fecha': row[0],
                'total_mensajes': row[1],
                'recibidos': row[2],
                'enviados': row[3]
            }
            for row in mensajes_rows
        ] if mensajes_rows else []
        
        # Últimos mensajes no leídos con IFNULL para campos que podrían ser NULL
        cursor.execute("""
            SELECT 
                hm.id,
                IFNULL(c.telefono, 'Desconocido') as telefono,
                IFNULL(hm.mensaje, '') as mensaje,
                IFNULL(hm.fecha_hora, CURRENT_TIMESTAMP) as fecha_hora,
                c.id as cliente_id
            FROM historial_mensajes hm
            LEFT JOIN clientes c ON hm.cliente_id = c.id
            WHERE hm.tipo = 'recibido' 
            AND (hm.estado IS NULL OR hm.estado = 0)
            ORDER BY hm.fecha_hora DESC
            LIMIT 10
        """)
        mensajes_rows = cursor.fetchall()
        # Convertir mensajes_no_leidos a lista de diccionarios
        mensajes_no_leidos = [
            {
                'id': row[0],
                'telefono': row[1],
                'mensaje': row[2],
                'fecha_hora': row[3],
                'cliente_id': row[4]
            }
            for row in mensajes_rows
        ] if mensajes_rows else []
        
        return render_template('admin.html',
                             stats=stats,
                             mensajes_por_dia=mensajes_por_dia,
                             mensajes_no_leidos=mensajes_no_leidos)
                             
    except sqlite3.Error as e:
        logging.error(f"Error de SQLite en panel de administración: {str(e)}")
        return "Error en la base de datos: " + str(e), 500
    except Exception as e:
        logging.error(f"Error en panel de administración: {str(e)}\n{traceback.format_exc()}")
        return "Error interno del servidor: " + str(e), 500
    finally:
        if conn:
            conn.close()

@app.route('/obtener-prompt-ia')
def obtener_prompt_ia():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', ('prompt_ia',))
        resultado = cursor.fetchone()
        prompt = resultado[0] if resultado else ""
        return jsonify({'success': True, 'prompt': prompt})
    except Exception as e:
        logging.error(f"Error obteniendo prompt IA: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if conn:
            conn.close()

@app.route('/guardar-prompt-ia', methods=['POST'])
def guardar_prompt_ia():
    try:
        nuevo_prompt = request.json.get('prompt', '')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE configuracion SET valor = ? WHERE clave = ?', 
                      (nuevo_prompt, 'prompt_ia'))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error guardando prompt IA: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if conn:
            conn.close()

# Funciones para RAG
def buscar_documentos_relevantes(query_embedding, cursor, umbral=0.7, limite=3):
    """Busca documentos relevantes basados en la similitud de embeddings"""
    logging.info("=== INICIO BÚSQUEDA DE DOCUMENTOS ===")
    logging.info(f"Parámetros - umbral: {umbral}, límite: {limite}")
    logging.info(f"Query embedding length: {len(query_embedding)}")
    
    if not query_embedding:
        logging.error("Query embedding es None")
        return []

    documentos_relevantes = []
    try:
        logging.info("Consultando documentos en la base de datos...")
        cursor.execute('SELECT id, titulo, contenido, tipo, embedding FROM documentos WHERE activo = 1')
        todos_docs = cursor.fetchall()
        logging.info(f"Total de documentos encontrados: {len(todos_docs)}")

        # Obtener los nombres de las columnas
        columnas = [description[0] for description in cursor.description]
        logging.info(f"Columnas: {columnas}")

        for doc in todos_docs:
            try:
                # Convertir la tupla en un diccionario
                doc_dict = dict(zip(columnas, doc))
                logging.info(f"Procesando documento: {doc_dict['id']} - {doc_dict['titulo']}")
                
                doc_embedding = json.loads(doc_dict['embedding'])
                logging.info(f"Embedding length: {len(doc_embedding)}")
                
                if not doc_embedding:
                    logging.warning(f"Documento {doc_dict['id']} no tiene embedding válido")
                    continue

                similitud = cosine_similarity(query_embedding, doc_embedding)
                logging.info(f"Documento {doc_dict['id']} ({doc_dict['titulo']}) - Similitud: {similitud:.4f}")
                
                if similitud > umbral:
                    documentos_relevantes.append({
                        'id': doc_dict['id'],
                        'titulo': doc_dict['titulo'],
                        'contenido': doc_dict['contenido'],
                        'tipo': doc_dict['tipo'],
                        'similitud': similitud
                    })
                    logging.info(f"Documento {doc_dict['id']} agregado a resultados")
            except Exception as e:
                logging.error(f"Error procesando documento {doc_dict.get('id', 'desconocido')}: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error en búsqueda de documentos: {str(e)}")
        return []
    finally:
        logging.info(f"Documentos relevantes encontrados: {len(documentos_relevantes)}")
        logging.info("=== FIN BÚSQUEDA DE DOCUMENTOS ===")

    return sorted(documentos_relevantes, key=lambda x: x['similitud'], reverse=True)[:limite]

def cosine_similarity(v1, v2):
    """Calcula la similitud del coseno entre dos vectores"""
    try:
        logging.info(f"Calculando similitud del coseno - len(v1): {len(v1)}, len(v2): {len(v2)}")
        
        if not v1 or not v2 or len(v1) != len(v2):
            logging.warning(f"Vectores inválidos o de diferente longitud")
            return 0.0

        import numpy as np
        v1_array = np.array(v1)
        v2_array = np.array(v2)
        
        dot_product = np.dot(v1_array, v2_array)
        norm1 = np.linalg.norm(v1_array)
        norm2 = np.linalg.norm(v2_array)
        
        logging.info(f"Producto punto: {dot_product}, Norma1: {norm1}, Norma2: {norm2}")
        
        if norm1 == 0 or norm2 == 0:
            logging.warning("Al menos una de las normas es cero")
            return 0.0
            
        similitud = dot_product / (norm1 * norm2)
        logging.info(f"Similitud calculada: {similitud}")
        return similitud
        
    except Exception as e:
        logging.error(f"Error en cosine_similarity: {str(e)}")
        return 0.0

# Rutas para gestionar documentos
@app.route('/agregar-documento', methods=['POST'])
def agregar_documento():
    try:
        data = request.get_json()
        titulo = data.get('titulo')
        contenido = data.get('contenido')
        tipo = data.get('tipo')
        
        if not all([titulo, contenido, tipo]):
            return jsonify({'success': False, 'error': 'Faltan campos requeridos'})
        
        # Inicializar cliente de Vultr
        client = VultrInferenceClient(api_key=VULTR_API_KEY)
        
        # Generar embedding
        embedding = generar_embedding(contenido, client)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documentos (titulo, contenido, tipo, embedding)
            VALUES (?, ?, ?, ?)
        ''', (titulo, contenido, tipo, json.dumps(embedding) if embedding else None))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error agregando documento: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/listar-documentos')
def listar_documentos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, titulo, tipo, fecha_actualizacion
            FROM documentos
            WHERE activo = 1
            ORDER BY fecha_actualizacion DESC
        ''')
        
        documentos = [{
            'id': row[0],
            'titulo': row[1],
            'tipo': row[2],
            'fecha_actualizacion': row[3]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({'success': True, 'documentos': documentos})
        
    except Exception as e:
        logging.error(f"Error listando documentos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/eliminar-documento/<int:doc_id>', methods=['DELETE'])
def eliminar_documento(doc_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Soft delete
        cursor.execute('''
            UPDATE documentos
            SET activo = 0
            WHERE id = ?
        ''', (doc_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error eliminando documento: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test-rag', methods=['GET'])
def test_rag():
    try:
        logging.info("=== INICIO TEST RAG ===")
        
        # 1. Primero, agregar un documento de prueba
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Documento de prueba sobre un paquete turístico
        documento_prueba = {
            'titulo': 'Paquete Cancún Todo Incluido',
            'contenido': '''Disfruta de unas vacaciones inolvidables en Cancún con nuestro paquete todo incluido:
            - 7 días y 6 noches en hotel 5 estrellas frente al mar
            - Vuelos redondos incluidos desde CDMX
            - Todas las comidas y bebidas ilimitadas
            - Acceso a actividades acuáticas (snorkel, kayak)
            - Traslados aeropuerto-hotel-aeropuerto
            - Tour a Chichen Itzá incluido
            Precios especiales para grupos y familias. Niños menores de 12 años tienen 50% de descuento.''',
            'tipo': 'paquete_turistico'
        }
        
        logging.info("Generando embedding para documento de prueba...")
        embedding = generar_embedding(documento_prueba['contenido'], None)  # No necesitamos client para embeddings locales
        
        if embedding:
            logging.info("Embedding generado exitosamente")
            # Guardar documento con su embedding
            cursor.execute('''
                INSERT INTO documentos (titulo, contenido, tipo, embedding)
                VALUES (?, ?, ?, ?)
            ''', (
                documento_prueba['titulo'],
                documento_prueba['contenido'],
                documento_prueba['tipo'],
                json.dumps(embedding)
            ))
            conn.commit()
            logging.info("Documento guardado en la base de datos")
            
            # 2. Hacer una consulta de prueba
            query = "¿Qué incluye el paquete a Cancún?"
            logging.info(f"Realizando consulta de prueba: {query}")
            
            query_embedding = generar_embedding(query, None)
            
            if query_embedding:
                logging.info("Embedding de consulta generado exitosamente")
                documentos = buscar_documentos_relevantes(query_embedding, cursor, umbral=0.5)  # Bajamos el umbral a 0.5
                
                resultado = {
                    'query': query,
                    'documentos_encontrados': len(documentos),
                    'documentos': documentos
                }
                logging.info(f"Búsqueda completada - Documentos encontrados: {len(documentos)}")
            else:
                resultado = {'error': 'No se pudo generar el embedding para la consulta'}
                logging.error("No se pudo generar el embedding para la consulta")
        else:
            resultado = {'error': 'No se pudo generar el embedding para el documento'}
            logging.error("No se pudo generar el embedding para el documento")
            
        conn.close()
        logging.info("=== FIN TEST RAG ===")
        return jsonify(resultado)
        
    except Exception as e:
        logging.error(f"Error en test-rag: {str(e)}")
        return jsonify({'error': str(e)}), 500

def agregar_documentos_prueba():
    """Agrega documentos de prueba a la base de datos"""
    documentos = [
        {
            'titulo': 'Paquete Cancún Todo Incluido',
            'contenido': '''Disfruta de unas vacaciones inolvidables en Cancún con nuestro paquete todo incluido:
            - 7 días y 6 noches en hotel 5 estrellas frente al mar
            - Vuelos redondos incluidos desde CDMX
            - Todas las comidas y bebidas ilimitadas
            - Acceso a actividades acuáticas (snorkel, kayak)
            - Traslados aeropuerto-hotel-aeropuerto
            - Tour a Chichen Itzá incluido
            Precios especiales para grupos y familias. Niños menores de 12 años tienen 50% de descuento.''',
            'tipo': 'paquete_turistico'
        },
        {
            'titulo': 'Paquete Los Cabos Aventura',
            'contenido': '''Explora Los Cabos con nuestro paquete de aventura:
            - 5 días y 4 noches en resort de lujo
            - Vuelos redondos incluidos
            - Desayuno buffet diario
            - Tour de snorkel en el arco
            - Paseo en ATV por el desierto
            - Cena romántica en la playa
            Ideal para parejas y aventureros. Incluye todos los equipos necesarios para las actividades.''',
            'tipo': 'paquete_turistico'
        },
        {
            'titulo': 'Información General Cancún',
            'contenido': '''Cancún es un destino paradisíaco ubicado en el Caribe mexicano:
            - Clima tropical todo el año
            - Playas de arena blanca y agua turquesa
            - Temperatura promedio de 27°C
            - Temporada alta: diciembre a abril
            - Temporada de lluvia: junio a octubre
            - Múltiples opciones de hospedaje
            - Excelente vida nocturna
            - Cerca de sitios arqueológicos mayas''',
            'tipo': 'informacion_destino'
        }
    ]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for doc in documentos:
            logging.info(f"Procesando documento: {doc['titulo']}")
            
            # Generar embedding para el documento
            embedding = generar_embedding(doc['contenido'], None)
            
            if embedding:
                # Guardar documento con su embedding
                cursor.execute('''
                    INSERT INTO documentos (titulo, contenido, tipo, embedding, activo)
                    VALUES (?, ?, ?, ?, 1)
                ''', (
                    doc['titulo'],
                    doc['contenido'],
                    doc['tipo'],
                    json.dumps(embedding)
                ))
                logging.info(f"Documento guardado exitosamente: {doc['titulo']}")
            else:
                logging.error(f"No se pudo generar embedding para: {doc['titulo']}")
        
        conn.commit()
        conn.close()
        logging.info("Documentos de prueba agregados exitosamente")
        return True
        
    except Exception as e:
        logging.error(f"Error agregando documentos de prueba: {str(e)}")
        return False

@app.route('/agregar-documentos-prueba', methods=['POST'])
def agregar_documentos_prueba_endpoint():
    """Endpoint para agregar documentos de prueba"""
    try:
        if agregar_documentos_prueba():
            return jsonify({'success': True, 'message': 'Documentos de prueba agregados exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error agregando documentos de prueba'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/limpiar-mensajes', methods=['POST'])
def limpiar_mensajes():
    """Endpoint para limpiar la tabla de mensajes de clientes"""
    try:
        logging.info("=== INICIO LIMPIEZA DE MENSAJES ===")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar todos los registros de la tabla historial_mensajes
        cursor.execute('DELETE FROM historial_mensajes')
        
        # También limpiamos la tabla de clientes ya que está relacionada
        cursor.execute('DELETE FROM clientes')
        
        conn.commit()
        conn.close()
        
        logging.info("Mensajes y clientes eliminados exitosamente")
        return jsonify({
            'success': True,
            'message': 'Historial de mensajes y clientes limpiado exitosamente'
        })
        
    except Exception as e:
        logging.error(f"Error al limpiar mensajes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == "__main__":
    setup_logging()
    validate_config()
    init_db()
    # verificar_estructura_tabla()  # Comenta esta línea si no quieres ver la estructura
    app.run(debug=True, port=5004)
