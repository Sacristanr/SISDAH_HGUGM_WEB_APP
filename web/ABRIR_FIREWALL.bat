@echo off
net session >nul 2>&1
if errorlevel 1 (
    echo Ejecutar como Administrador.
    pause & exit /b 1
)
netsh advfirewall firewall add rule name="SISDAH Web" dir=in action=allow protocol=TCP localport=5000
echo [OK] Puerto 5000 abierto en el firewall.
echo Los equipos de la red ya pueden acceder a http://[IP]:5000
pause
