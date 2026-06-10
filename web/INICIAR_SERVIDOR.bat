@echo off
chcp 65001 >nul
title SISDAH Web -- Servidor activo
color 0A

:: Buscar Python portable en las rutas conocidas
set PYTHON=%~dp0..\python\python.exe
if not exist "%PYTHON%" set PYTHON=%USERPROFILE%\Desktop\SISDAH\python\python.exe
if not exist "%PYTHON%" set PYTHON=C:\Users\54421076V\Desktop\SISDAH\python\python.exe
set SCRIPT=%~dp0run.py
set FLASK_DEBUG=0
:: HTTPS se controla desde .env (SSL_ADHOC=0 para HTTP, 1 para HTTPS)

echo.
echo  =============================================
echo  SISDAH Web -- Servidor Flask
echo  =============================================
echo  Puerto : 5000
echo  URL    : http(s)://localhost:5000
echo  Red    : http(s)://[IP-del-equipo]:5000
echo  (HTTP u HTTPS segun SSL_ADHOC en .env)
echo  =============================================
echo  Cierra esta ventana para detener.
echo.

cd /d "%~dp0"
"%PYTHON%" "%SCRIPT%"
pause
