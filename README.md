# Documentación del Chatbot con Flask y Vultr
Este proyecto implementa un chatbot inteligente utilizando Flask y Vultr, con integración de Telnyx para mensajería SMS. Las principales características incluyen:

### Funcionalidades Principales

1. **Procesamiento de Mensajes SMS**
   - Recibe mensajes SMS a través de Telnyx
   - Procesa el contenido utilizando IA
   - Reenvía respuestas automáticas

2. **Integración con IA**
   - Utiliza el modelo de Vultr para generar respuestas
   - Sistema de fallback con respuestas predefinidas
   - Procesamiento de lenguaje natural

3. **Gestión de Base de Datos**
   - Almacenamiento de interacciones con clientes
   - Registro de mensajes y estados
   - Seguimiento de conversaciones

4. **Características Técnicas**
   - API REST con Flask
   - Integración con Telnyx para SMS
   - Base de datos SQLite
   - Sistema de respaldo con respuestas predefinidas
   - Procesamiento de números telefónicos

### Flujo de Trabajo
1. Usuario envía SMS
2. Sistema procesa el mensaje
3. Genera respuesta usando IA
4. Almacena la interacción
5. Reenvía respuesta al número configurado

El sistema está diseñado para ser escalable y mantener un registro completo de todas las interacciones con los usuarios.


## Índice
1. [Requisitos Previos](#requisitos-previos)
2. [Configuración del Entorno Python](#configuración-del-entorno-python)
3. [Configuración de Telnyx](#configuración-de-telnyx)
4. [Ejecución del Proyecto](#ejecución-del-proyecto)

## Requisitos Previos
- Linux, macOS, o Windows con WSL2
- Python 3.8+
- pip
- Cuenta en Telnyx
- Conexión a Internet

## Configuración del Entorno Python

1. Crear entorno virtual:
   ```bash
   python3 -m venv venv
   ```

2. Activar entorno:
   ```bash
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Variables de entorno:
   - TELNYX_API_KEY
   - VULTR_CLOUD_INFERENCE_API_KEY

## Configuración de Telnyx

1. Obtener API Key de Telnyx
2. Configurar webhook para el servidor Flask
3. Verificar conectividad

## Ejecución del Proyecto

1. Inicializar base de datos:
   ```bash
   python manage.py migrate
   ```

2. Iniciar servidor:
   ```bash
   python manage.py runserver
   ```

3. Probar conectividad:
   ```bash
   curl -X POST http://localhost:5005/sms \
   -d "Body=Hola estoy buscando una playa con buen clima en México, ¿cuál recomiendas?" \
   -d "From=+16072222222"
   ```

### Arquitectura del Sistema
1. **Backend (Flask)**
   - Endpoints REST para procesamiento de mensajes
   - Middleware de autenticación y validación
   - Manejo de errores y logging
   - Sistema de caché para optimizar respuestas

2. **Integración con IA (Vultr)**
   - Modelo de lenguaje personalizado
   - Sistema de prompts optimizados
   - Control de tokens y costos
   - Mecanismo de retry automático

3. **Base de Datos**
   - Esquema optimizado para conversaciones
   - Índices para búsqueda rápida
   - Sistema de backup automático
   - Purga automática de datos antiguos

### Configuración Detallada

1. **Variables de Entorno Requeridas**
   ```bash
   TELNYX_API_KEY=your_api_key
   TELNYX_PUBLIC_KEY=your_public_key
   TELNYX_MESSAGING_PROFILE_ID=your_profile_id
   TELNYX_FROM_NUMBER=+1234567890
   TELNYX_TO_NUMBER=+1234567890
   VULTR_CLOUD_INFERENCE_API_KEY=your_vultr_key
   DB_NAME=crm_pipeline.db
   ```

2. **Estructura del Proyecto**
   ```
   .
   ├── app.py              # Aplicación principal Flask
   ├── templates/          # Plantillas HTML
   │   └── dashboard.html  # Panel de control
   ├── .env               # Variables de entorno
   └── requirements.txt    # Dependencias
   ```

### Características Técnicas

1. **Backend (Flask)**
   - Sistema de verificación de webhooks Telnyx
   - Dashboard web para monitoreo de mensajes
   - Base de datos SQLite para almacenamiento
   - Procesamiento y limpieza de números telefónicos
   - Manejo de errores y logging detallado

2. **Integración con IA (Vultr)**
   - Uso del modelo mixtral-8x7b
   - Sistema de prompts optimizado para respuestas concisas
   - Respuestas personalizadas para consultas sobre vuelos
   - Límite de tokens configurables
   - Fallback automático en caso de errores

3. **Base de Datos**
   - Tabla 'clientes' con campos:
     - id (PRIMARY KEY)
     - nombre
     - telefono
     - mensaje
     - respuesta
     - fecha_contacto
     - estado

### Panel de Control

El sistema incluye un dashboard web accesible en la ruta principal ('/') que muestra:
- Lista de todas las interacciones
- Estado de los mensajes
- Historial de conversaciones
- Interfaz responsive con Bootstrap
- Diseño moderno y fácil de usar

### Endpoints API

1. **/sms (POST)**
   - Recibe webhooks de Telnyx
   - Procesa mensajes entrantes
   - Genera respuestas usando IA
   - Almacena interacciones en la base de datos
   - Envía respuestas automáticas

### Seguridad

1. **Verificación de Webhooks**
   - Validación de firmas Telnyx
   - Verificación de timestamps
   - Manejo seguro de claves API

2. **Validación de Datos**
   - Limpieza de números telefónicos
   - Validación de formato E.164
   - Manejo de errores robusto

### Ejecución del Proyecto

1. **Instalación**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuración**
   - Crear archivo .env con las variables requeridas
   - Verificar permisos de base de datos
   - Configurar webhook en panel de Telnyx

3. **Iniciar Servidor**
   ```bash
   python app.py
   ```
   El servidor se iniciará en el puerto 8000

### Solución de Problemas

1. **Verificación de Configuración**
   ```python
   python app.py
   ```
   El sistema validará automáticamente todas las variables de entorno requeridas

2. **Logs y Debugging**
   - El modo debug está activado por defecto
   - Mensajes detallados en consola
   - Trazabilidad completa de errores