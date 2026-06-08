@echo off
chcp 65001 >nul
title SISDAH — Instalación inicial
color 0B
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║        SISDAH Web — Instalación inicial          ║
echo  ║        HGUGM Departamento de Informática         ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Detectar Python portable
set PYTHON=%~dp0..\python\python.exe
if not exist "%PYTHON%" (
    echo [ERROR] No se encontró Python en ..\python\python.exe
    echo         Asegúrate de ejecutar este script desde la carpeta web\
    pause & exit /b 1
)
echo [OK] Python encontrado: %PYTHON%

:: Instalar dependencias
echo.
echo [*] Instalando dependencias Python...
"%PYTHON%" -m pip install -r "%~dp0..\requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] Falló la instalación de dependencias.
    pause & exit /b 1
)
echo [OK] Dependencias instaladas.

:: Crear .env si no existe
if not exist "%~dp0.env" (
    echo [*] Creando archivo .env...
    :: Generar SECRET_KEY criptográficamente segura con Python
    for /f %%K in ('"%PYTHON%" -c "import secrets; print(secrets.token_hex(32))"') do set SK=%%K
    (
        echo # ══ SISDAH — Configuración de entorno ══════════════
        echo # IMPORTANTE: Este fichero NUNCA debe subirse a Git
        echo.
        echo # Seguridad
        echo SECRET_KEY=%SK%
        echo.
        echo # Base de datos ^(SQLite por defecto; editar para MySQL^)
        echo USE_SQLITE=1
        echo DB_HOST=localhost
        echo DB_PORT=3306
        echo DB_USER=root
        echo DB_PASSWORD=
        echo DB_NAME=sisdah
        echo.
        echo # Servidor
        echo PORT=5000
        echo FLASK_DEBUG=0
        echo SESSION_SECURE=0
        echo.
        echo # Acceso de emergencia ^(cambiar DNI tras primer despliegue^)
        echo EMERGENCY_DNI=54421076V
    ) > "%~dp0.env"
    echo [OK] .env creado con SECRET_KEY segura y SQLite por defecto.
) else (
    echo [OK] .env ya existe, no se sobreescribe.
)

:: Inicializar base de datos
echo.
echo [*] Inicializando base de datos...
cd /d "%~dp0"
"%PYTHON%" -c "import sys; sys.path.insert(0,'.'); from app import create_app; app=create_app(); print('[OK] Base de datos lista.')"
if errorlevel 1 (
    echo [ERROR] No se pudo conectar a la base de datos.
    echo         Si usas MySQL: abre XAMPP y arranca MySQL antes de ejecutar esto.
    pause & exit /b 1
)

echo.
echo  ══════════════════════════════════════════════════
echo  [OK] Instalación completada.
echo.
echo  Para iniciar el servidor ejecuta: INICIAR_SERVIDOR.bat
echo  Para instalar como servicio:      INSTALAR_SERVICIO.bat  (recomendado)
echo  ══════════════════════════════════════════════════
echo.
pause
