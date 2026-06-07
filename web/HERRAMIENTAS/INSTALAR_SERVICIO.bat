@echo off
chcp 65001 >nul
title SISDAH — Instalar como servicio Windows
color 0E

:: Requiere permisos de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Este script necesita ejecutarse como Administrador.
    echo         Clic derecho → "Ejecutar como administrador"
    pause & exit /b 1
)

set NSSM=%~dp0nssm\nssm.exe
set PYTHON=%~dp0..\python\python.exe
set SCRIPT=%~dp0run.py
set SVC_NAME=SISDAH_Web

:: Descargar NSSM si no existe
if not exist "%NSSM%" (
    echo [*] Descargando NSSM (gestor de servicios)...
    mkdir "%~dp0nssm" 2>nul
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = 'Tls12'; Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%~dp0nssm\nssm.zip' }"
    powershell -Command "Expand-Archive '%~dp0nssm\nssm.zip' -DestinationPath '%~dp0nssm\' -Force"
    copy /y "%~dp0nssm\nssm-2.24\win64\nssm.exe" "%NSSM%" >nul
    echo [OK] NSSM descargado.
)

:: Eliminar servicio anterior si existe
sc query %SVC_NAME% >nul 2>&1
if not errorlevel 1 (
    echo [*] Eliminando servicio anterior...
    "%NSSM%" stop %SVC_NAME% >nul 2>&1
    "%NSSM%" remove %SVC_NAME% confirm >nul 2>&1
)

:: Instalar servicio
echo [*] Instalando servicio %SVC_NAME%...
"%NSSM%" install %SVC_NAME% "%PYTHON%" "%SCRIPT%"
"%NSSM%" set %SVC_NAME% AppDirectory "%~dp0"
"%NSSM%" set %SVC_NAME% DisplayName "SISDAH Web — HGUGM"
"%NSSM%" set %SVC_NAME% Description "Sistema de Archivo Hospitalario HGUGM"
"%NSSM%" set %SVC_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SVC_NAME% AppStdout "%~dp0logs\sisdah_out.log"
"%NSSM%" set %SVC_NAME% AppStderr "%~dp0logs\sisdah_err.log"
"%NSSM%" set %SVC_NAME% AppRotateFiles 1
"%NSSM%" set %SVC_NAME% AppRotateBytes 5242880

mkdir "%~dp0logs" 2>nul

:: Arrancar servicio
echo [*] Arrancando servicio...
"%NSSM%" start %SVC_NAME%

echo.
echo  ══════════════════════════════════════════════════
echo  [OK] Servicio instalado y arrancado.
echo.
echo  El servidor SISDAH arrancará automáticamente
echo  cada vez que se inicie Windows.
echo.
echo  URL: http://localhost:5000
echo.
echo  Para gestionar el servicio:
echo    Iniciar : sc start %SVC_NAME%
echo    Detener : sc stop %SVC_NAME%
echo    Logs    : web\logs\sisdah_out.log
echo  ══════════════════════════════════════════════════
pause
