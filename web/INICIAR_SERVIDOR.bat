@echo off
chcp 65001 >nul
title SISDAH Web -- Servidor activo
color 0A

set PYTHON=%~dp0..\python\python.exe
set SCRIPT=%~dp0run.py
set SSL_ADHOC=1
set FLASK_DEBUG=0

echo.
echo  =============================================
echo  SISDAH Web -- Servidor Flask (HTTPS)
echo  =============================================
echo  Puerto : 5000
echo  URL    : https://localhost:5000
echo  Red    : https://[IP-del-equipo]:5000
echo  =============================================
echo  Cierra esta ventana para detener.
echo.

cd /d "%~dp0"
"%PYTHON%" "%SCRIPT%"
pause
