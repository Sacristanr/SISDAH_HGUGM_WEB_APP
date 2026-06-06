@echo off
chcp 65001 >nul
title SISDAH Web -- Servidor activo
color 0A

set PYTHON=%~dp0..\python\python.exe
set SCRIPT=%~dp0run.py

echo.
echo  =============================================
echo  SISDAH Web -- Servidor Flask
echo  =============================================
echo  Puerto : 5000
echo  URL    : http://localhost:5000
echo  Red    : http://[IP-del-equipo]:5000
echo  =============================================
echo  Cierra esta ventana para detener.
echo.

cd /d "%~dp0"
"%PYTHON%" "%SCRIPT%"
pause
