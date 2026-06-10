@echo off
chcp 65001 >nul
title SISDAH -- Instalacion inicial
color 0B
echo.
echo  +==================================================+
echo  |        SISDAH Web -- Instalacion inicial          |
echo  |        HGUGM Departamento de Informatica         |
echo  +==================================================+
echo.

:: Detectar Python portable (carpeta "python" hermana de "web")
set PYTHON=%~dp0..\..\python\python.exe
if not exist "%PYTHON%" set PYTHON=%~dp0..\python\python.exe
if not exist "%PYTHON%" set PYTHON=%USERPROFILE%\Desktop\SISDAH\python\python.exe
if not exist "%PYTHON%" set PYTHON=C:\Users\54421076V\Desktop\SISDAH\python\python.exe
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro Python portable.
    echo         La carpeta "python" debe estar junto a la carpeta "web".
    pause & exit /b 1
)
echo [OK] Python encontrado: %PYTHON%

:: Instalar dependencias (si existe C:\whl se instala sin internet)
echo.
echo [*] Instalando dependencias Python...
set PIPOPTS=
if exist "C:\whl\" set PIPOPTS=--no-index --find-links C:\whl
"%PYTHON%" -m pip install -r "%~dp0..\requirements.txt" %PIPOPTS% --quiet
if errorlevel 1 (
    if exist "C:\whl\" (
        echo [AVISO] Faltan paquetes en C:\whl -- reintentando contra PyPI...
        "%PYTHON%" -m pip install -r "%~dp0..\requirements.txt" --quiet
    )
)
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    echo         Si la red bloquea PyPI: descarga los .whl que falten
    echo         desde el navegador y dejalos en C:\whl\
    pause & exit /b 1
)
echo [OK] Dependencias instaladas.

:: Crear .env si no existe
if not exist "%~dp0.env" (
    echo [*] Creando archivo .env...
    :: Generar SECRET_KEY criptograficamente segura con Python
    for /f %%K in ('"%PYTHON%" -c "import secrets; print(secrets.token_hex(32))"') do set SK=%%K
    (
        echo # == SISDAH -- Configuracion de entorno ==============
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
echo  ==================================================
echo  [OK] Instalacion completada.
echo.
echo  Para iniciar el servidor ejecuta: INICIAR_SERVIDOR.bat
echo  Para instalar como servicio:      INSTALAR_SERVICIO.bat  (recomendado)
echo  ==================================================
echo.
pause
