@echo off
setlocal enabledelayedexpansion

:: Colores para output
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "NC=[0m"

:: Funciones para imprimir mensajes
:print_message
echo %GREEN%[+] %~1%NC%
goto :eof

:print_error
echo %RED%[!] %~1%NC%
goto :eof

:print_warning
echo %YELLOW%[*] %~1%NC%
goto :eof

:: Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    call :print_error "Este script debe ejecutarse como administrador"
    pause
    exit /b 1
)

:: Obtener directorio actual
set "PROJECT_DIR=%~dp0"

call :print_message "Iniciando instalación..."

:: Crear y activar entorno virtual
call :print_message "Configurando entorno virtual..."
cd /d "%PROJECT_DIR%"
python -m venv venv
if errorlevel 1 (
    call :print_error "Error al crear el entorno virtual"
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    call :print_error "Error al activar el entorno virtual"
    pause
    exit /b 1
)

:: Instalar dependencias de Python
call :print_message "Instalando dependencias de Python..."
pip install -r requirements.txt
if errorlevel 1 (
    call :print_error "Error al instalar dependencias de requirements.txt"
    pause
    exit /b 1
)

pip install gunicorn
if errorlevel 1 (
    call :print_error "Error al instalar gunicorn"
    pause
    exit /b 1
)

:: Crear archivo de configuración de Gunicorn
call :print_message "Configurando Gunicorn..."
(
echo bind = "0.0.0.0:8000"
echo workers = 3
echo timeout = 120
) > gunicorn.conf.py

:: Crear directorio para logs
call :print_message "Configurando directorio de logs..."
if not exist logs mkdir logs

:: Verificar si existe el archivo .env
if not exist "%PROJECT_DIR%\.env" (
    call :print_warning "Creando archivo .env de ejemplo..."
    (
    echo TELNYX_API_KEY=your_api_key
    echo TELNYX_PUBLIC_KEY=your_public_key
    echo TELNYX_MESSAGING_PROFILE_ID=your_profile_id
    echo TELNYX_FROM_NUMBER=+1234567890
    echo VULTR_CLOUD_INFERENCE_API_KEY=your_vultr_key
    echo DB_NAME=crm_pipeline.db
    ) > .env
    call :print_warning "Por favor, edita el archivo .env con tus credenciales"
)

:: Crear archivo batch para ejecutar el servicio
call :print_message "Creando archivo de inicio..."
(
echo @echo off
echo call "%%~dp0\venv\Scripts\activate.bat"
echo python -m gunicorn -c gunicorn.conf.py app:app
) > start_server.bat

:: Crear tarea programada para inicio automático
call :print_message "Configurando inicio automático..."
schtasks /create /tn "ChatbotServer" /tr """%PROJECT_DIR%start_server.bat""" /sc onlogon /ru System /f
if errorlevel 1 (
    call :print_error "Error al crear la tarea programada"
    call :print_warning "El servicio deberá iniciarse manualmente"
)

:: Iniciar el servicio
call :print_message "Iniciando el servicio..."
start "" "%PROJECT_DIR%start_server.bat"

:: Verificar la instalación
call :print_message "¡Instalación completada con éxito!"
call :print_message "El servicio está corriendo en http://localhost:8000"
call :print_message "Los logs se encuentran en la carpeta logs"

pause
exit /b 0
