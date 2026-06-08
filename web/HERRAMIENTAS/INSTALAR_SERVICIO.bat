@echo off
chcp 65001 >nul
title SISDAH - Instalar arranque automatico
color 0E

:: Requiere permisos de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Este script necesita ejecutarse como Administrador.
    echo         Clic derecho -^> "Ejecutar como administrador"
    pause
    exit /b 1
)

set PYTHON=%~dp0..\python\python.exe
set SCRIPT=%~dp0..\run.py
set TASK_NAME=SISDAH_Web
set LOG_DIR=%~dp0..\logs

echo.
echo  ==================================================
echo  SISDAH - Instalacion de arranque automatico
echo  ==================================================
echo.

:: Verificar Python
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro Python en:
    echo         %PYTHON%
    pause
    exit /b 1
)
echo [OK] Python encontrado.

:: Verificar run.py
if not exist "%SCRIPT%" (
    echo [ERROR] No se encontro run.py en:
    echo         %SCRIPT%
    pause
    exit /b 1
)
echo [OK] run.py encontrado.

:: Crear carpeta de logs
mkdir "%LOG_DIR%" 2>nul

:: Eliminar tarea anterior si existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Crear tarea en el Programador de tareas
:: Se ejecuta al iniciar el sistema, como SYSTEM, sin ventana visible
echo [*] Registrando tarea de inicio automatico...
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON%\" \"%SCRIPT%\"" ^
    /sc onstart ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

if errorlevel 1 (
    echo [ERROR] No se pudo registrar la tarea.
    pause
    exit /b 1
)
echo [OK] Tarea registrada correctamente.

:: Arrancar ahora sin esperar al reinicio
echo [*] Arrancando SISDAH ahora...
schtasks /run /tn "%TASK_NAME%"

:: Esperar a que arranque
timeout /t 5 /nobreak >nul

:: Verificar que esta corriendo
netstat -ano | findstr ":5000" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] El servidor aun no responde en el puerto 5000.
    echo         Puede tardar unos segundos. Comprueba en el navegador:
) else (
    echo [OK] Servidor escuchando en puerto 5000.
)

echo.
echo  ==================================================
echo  [OK] Instalacion completada.
echo.
echo  SISDAH arrancara automaticamente al encender el PC.
echo.
echo  Accede desde el navegador con HTTPS:
echo    https://[IP-del-servidor]:5000
echo  (acepta el aviso de certificado la primera vez)
echo.
echo  Gestionar:
echo    Iniciar ahora : schtasks /run /tn %TASK_NAME%
echo    Detener       : taskkill /im python.exe /f
echo    Ver estado    : schtasks /query /tn %TASK_NAME%
echo  ==================================================
echo.
pause
