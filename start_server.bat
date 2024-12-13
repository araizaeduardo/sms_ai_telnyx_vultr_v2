@echo off
setlocal enabledelayedexpansion

:: Obtener directorio actual
set "PROJECT_DIR=%~dp0"

:: Activar entorno virtual
call "%PROJECT_DIR%\venv\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: No se pudo activar el entorno virtual
    pause
    exit /b 1
)

:: Iniciar el servidor con redirección de logs
python -m gunicorn -c gunicorn.conf.py app:app >> "%PROJECT_DIR%\logs\server.log" 2>> "%PROJECT_DIR%\logs\error.log"

endlocal 