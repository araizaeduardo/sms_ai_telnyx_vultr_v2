#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_error() {
    echo -e "${RED}[!] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[*] $1${NC}"
}

# Verificar si se está ejecutando como root
if [ "$EUID" -ne 0 ]; then 
    print_error "Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Obtener el nombre de usuario no-root
ACTUAL_USER=$(logname)
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_message "Iniciando instalación..."

# Actualizar sistema
print_message "Actualizando sistema..."
apt-get update
apt-get upgrade -y

# Instalar dependencias del sistema
print_message "Instalando dependencias del sistema..."
apt-get install -y python3-venv supervisor

# Crear y activar entorno virtual
print_message "Configurando entorno virtual..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de Python
print_message "Instalando dependencias de Python..."
pip install -r requirements.txt
pip install gunicorn

# Crear archivo de configuración de Gunicorn
print_message "Configurando Gunicorn..."
cat > gunicorn.conf.py << EOL
bind = "0.0.0.0:8000"
workers = 3
timeout = 120
EOL

# Crear directorio para logs
print_message "Configurando directorio de logs..."
mkdir -p /var/log/chatbot
chown -R $ACTUAL_USER:$ACTUAL_USER /var/log/chatbot

# Crear configuración de Supervisor
print_message "Configurando Supervisor..."
cat > /etc/supervisor/conf.d/chatbot.conf << EOL
[program:chatbot]
directory=$PROJECT_DIR
command=$PROJECT_DIR/venv/bin/gunicorn -c gunicorn.conf.py app:app
user=$ACTUAL_USER
autostart=true
autorestart=true
stderr_logfile=/var/log/chatbot/chatbot.err.log
stdout_logfile=/var/log/chatbot/chatbot.out.log
environment=PATH="$PROJECT_DIR/venv/bin"
EOL

# Verificar si existe el archivo .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_warning "Creando archivo .env de ejemplo..."
    cat > .env << EOL
TELNYX_API_KEY=your_api_key
TELNYX_PUBLIC_KEY=your_public_key
TELNYX_MESSAGING_PROFILE_ID=your_profile_id
TELNYX_FROM_NUMBER=+1234567890
VULTR_CLOUD_INFERENCE_API_KEY=your_vultr_key
DB_NAME=crm_pipeline.db
EOL
    print_warning "Por favor, edita el archivo .env con tus credenciales"
fi

# Reiniciar Supervisor
print_message "Reiniciando Supervisor..."
supervisorctl reread
supervisorctl update
supervisorctl start chatbot

# Verificar la instalación
print_message "Verificando la instalación..."
if supervisorctl status chatbot | grep -q "RUNNING"; then
    print_message "¡Instalación completada con éxito!"
    print_message "El servicio está corriendo en http://localhost:8000"
    print_message "Puedes ver los logs con: sudo tail -f /var/log/chatbot/chatbot.out.log"
else
    print_error "Hubo un problema al iniciar el servicio. Revisa los logs para más detalles."
fi

# Mostrar estado final
supervisorctl status chatbot
