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