@echo off
chcp 65001 >nul
title SISDAH — Configurar MySQL
color 0B

echo.
echo  Configurar SISDAH para usar MySQL (XAMPP)
echo  ══════════════════════════════════════════
echo.

set PYTHON=%~dp0..\python\python.exe
set ENV_FILE=%~dp0.env

:: Pedir datos
set /p DB_PASS=Contraseña root de MySQL (dejar vacío si no tiene):
set /p DB_NAME=Nombre de la base de datos [sisdah]:
if "%DB_NAME%"=="" set DB_NAME=sisdah

:: Crear base de datos si no existe
echo.
echo [*] Creando base de datos '%DB_NAME%' si no existe...
"C:\xampp\mysql\bin\mysql.exe" -u root -p%DB_PASS% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>nul
if errorlevel 1 (
    echo [AVISO] No se pudo crear la BD automáticamente.
    echo         Créala manualmente en phpMyAdmin: http://localhost/phpmyadmin
)

:: Actualizar .env
echo SECRET_KEY=sisdah-hgugm-prod-2026 > "%ENV_FILE%"
echo USE_SQLITE=0 >> "%ENV_FILE%"
echo DB_HOST=localhost >> "%ENV_FILE%"
echo DB_PORT=3306 >> "%ENV_FILE%"
echo DB_USER=root >> "%ENV_FILE%"
echo DB_PASS=%DB_PASS% >> "%ENV_FILE%"
echo DB_NAME=%DB_NAME% >> "%ENV_FILE%"

echo [OK] .env actualizado para MySQL.

:: Inicializar tablas
echo [*] Creando tablas en MySQL...
cd /d "%~dp0"
"%PYTHON%" -c "import sys; sys.path.insert(0,'.'); from app import create_app; app=create_app(); print('[OK] Tablas creadas en MySQL.')"

echo.
echo  ══════════════════════════════════════════════
echo  [OK] SISDAH ahora usa MySQL.
echo  Reinicia el servicio para aplicar los cambios:
echo    sc stop SISDAH_Web
echo    sc start SISDAH_Web
echo  ══════════════════════════════════════════════
pause
