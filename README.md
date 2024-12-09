# Chatbot con Flask y Vultr

Sistema de chatbot inteligente que procesa mensajes SMS usando Flask, Vultr y Telnyx.

## Características Principales

- Procesamiento automático de mensajes SMS vía Telnyx
- Generación de respuestas usando IA de Vultr
- Almacenamiento de conversaciones en SQLite
- Panel de control web para monitoreo

## Requisitos

- Python 3.8+
- Cuenta en Telnyx
- Cuenta en Vultr
- Conexión a Internet

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-repositorio>
cd <nombre-proyecto>
```

2. Crear y activar entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Crear archivo .env con las siguientes variables:
```bash
TELNYX_API_KEY=your_api_key
TELNYX_PUBLIC_KEY=your_public_key
TELNYX_MESSAGING_PROFILE_ID=your_profile_id
TELNYX_FROM_NUMBER=+1234567890
VULTR_CLOUD_INFERENCE_API_KEY=your_vultr_key
DB_NAME=crm_pipeline.db
```
## Ejecución

1. Iniciar el servidor:
```bash
python app.py
```

2. El servidor estará disponible en: `http://localhost:8000`

3. Probar el endpoint SMS:
```bash
curl -X POST http://localhost:8000/sms \
-d "Body=Hola, ¿qué servicios ofrecen?" \
-d "From=+16072222222"
```

## Ejecución con Gunicorn y Supervisor

### 1. Instalar Gunicorn en el entorno virtual
```bash
# Activar el entorno virtual
source venv/bin/activate  # Linux/macOS
# o
.\venv\Scripts\activate   # Windows

# Instalar gunicorn
pip install gunicorn
```

### 2. Crear archivo de configuración para Gunicorn
```bash
# /ruta/a/tu/proyecto/gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 3
timeout = 120
```

### 3. Instalar Supervisor
```bash
sudo apt-get install supervisor
```

### 4. Crear archivo de configuración para Supervisor
```bash
# /etc/supervisor/conf.d/chatbot.conf
[program:chatbot]
directory=/ruta/a/tu/proyecto
command=/ruta/a/tu/proyecto/venv/bin/gunicorn -c gunicorn.conf.py app:app
user=tu_usuario
autostart=true
autorestart=true
stderr_logfile=/var/log/chatbot/chatbot.err.log
stdout_logfile=/var/log/chatbot/chatbot.out.log
environment=PATH="/ruta/a/tu/proyecto/venv/bin"
```

### 5. Crear directorio para logs
```bash
sudo mkdir -p /var/log/chatbot
sudo chown -R tu_usuario:tu_usuario /var/log/chatbot
```

### 6. Iniciar y gestionar el servicio
```bash
# Recargar configuración de supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Iniciar el servicio
sudo supervisorctl start chatbot

# Ver estado
sudo supervisorctl status chatbot

# Ver logs en tiempo real
sudo tail -f /var/log/chatbot/chatbot.out.log
```

### 7. Probar la instalación
```bash
# Verificar que Gunicorn está instalado en el entorno virtual
source venv/bin/activate
which gunicorn  # Debería mostrar la ruta dentro de tu entorno virtual

# Probar manualmente (opcional)
gunicorn -c gunicorn.conf.py app:app
```

## Estructura del Proyecto

```
.
├── app.py              # Aplicación principal
├── templates/          # Plantillas HTML
│   └── dashboard.html  # Panel de control
├── .env               # Variables de entorno
└── requirements.txt    # Dependencias
```

## Endpoints

- `/` - Panel de control web
- `/sms` - Endpoint para webhooks de Telnyx (POST)

## Panel de Control

Accede al dashboard en `http://localhost:8000` para:
- Ver historial de conversaciones
- Monitorear estado de mensajes
- Consultar estadísticas

## Solución de Problemas

1. Verificar logs en consola (modo debug activado)
2. Confirmar variables de entorno correctas
3. Validar conexión con Telnyx y Vultr

## Documentación Adicional

- [Documentación de Telnyx](https://developers.telnyx.com/)
- [API de Vultr](https://www.vultr.com/api/)
