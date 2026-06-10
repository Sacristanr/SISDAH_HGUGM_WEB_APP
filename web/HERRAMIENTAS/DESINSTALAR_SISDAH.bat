@echo off
chcp 65001 >nul
title SISDAH -- DESINSTALACION TOTAL
color 0C

:: =============================================================
::  ELIMINA TODO LO RELACIONADO CON SISDAH DE ESTE PC:
::   - Detiene el servidor si esta corriendo
::   - Quita el autoarranque de Windows
::   - Quita la regla del firewall (puerto 5000)
::   - Borra la carpeta SISDAH completa (web, python, backups)
::   - Borra C:\whl (paquetes descargados a mano)
::  NO toca XAMPP/MySQL: la base de datos 'sisdah' queda intacta
::  por seguridad (se indica como borrarla al final).
:: =============================================================

echo.
echo  =====================================================
echo  DESINSTALADOR TOTAL DE SISDAH
echo  =====================================================
echo.

:: -- Localizar instalacion -------------------------------------
set DESTINO=
if exist "%USERPROFILE%\Desktop\SISDAH\web\run.py" set DESTINO=%USERPROFILE%\Desktop\SISDAH
if exist "C:\Users\54421076V\Desktop\SISDAH\web\run.py" set DESTINO=C:\Users\54421076V\Desktop\SISDAH
if "%DESTINO%"=="" (
    set /p DESTINO="No se encontro SISDAH. Escribe la ruta (o deja vacio para limpiar solo rastros): "
)

echo  Esto va a ELIMINAR de este equipo:
if not "%DESTINO%"=="" echo   - La carpeta completa: %DESTINO%
echo   - El autoarranque de SISDAH al encender el PC
echo   - La regla del firewall "SISDAH Web" (puerto 5000)
if exist "C:\whl\" echo   - La carpeta C:\whl
echo.
echo  La base de datos MySQL NO se toca (queda en XAMPP).
echo.
choice /C SN /M "Estas SEGURO de que quieres desinstalar todo"
if errorlevel 2 exit /b 0
echo.
choice /C SN /M "Confirmacion final: borrar SISDAH de este PC"
if errorlevel 2 exit /b 0

:: -- Copia de seguridad final (opcional) -----------------------
if not "%DESTINO%"=="" (
    echo.
    choice /C SN /M "Quieres guardar una copia ZIP final en el Escritorio antes de borrar"
    if not errorlevel 2 (
        set FECHA=%date:~-4%-%date:~3,2%-%date:~0,2%
        echo [*] Creando copia final...
        powershell -NoProfile -Command ^
          "Get-ChildItem -Path '%DESTINO%\web' -Recurse | Where-Object { $_.FullName -notmatch '__pycache__|\.pyc$' } | Compress-Archive -DestinationPath \"$env:USERPROFILE\Desktop\SISDAH_copia_final.zip\" -Update"
        if exist "%USERPROFILE%\Desktop\SISDAH_copia_final.zip" (
            echo [OK] Copia guardada en el Escritorio: SISDAH_copia_final.zip
        ) else (
            echo [AVISO] No se pudo crear la copia final.
            choice /C SN /M "Continuar borrando de todas formas"
            if errorlevel 2 exit /b 0
        )
    )
)

:: -- 1. Detener servidor ---------------------------------------
echo.
echo [*] Deteniendo servidor SISDAH si esta corriendo...
if not "%DESTINO%"=="" (
    powershell -NoProfile -Command ^
      "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.ExecutablePath -like '%DESTINO%*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
)
echo [OK] Procesos detenidos.

:: -- 2. Quitar autoarranque ------------------------------------
echo [*] Quitando autoarranque...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_sisdah.bat" >nul 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_sisdah.lnk" >nul 2>nul
del "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\start_sisdah.bat" >nul 2>nul
del "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\start_sisdah.lnk" >nul 2>nul
echo [OK] Autoarranque eliminado.

:: -- 3. Quitar regla del firewall ------------------------------
echo [*] Quitando regla del firewall...
netsh advfirewall firewall delete rule name="SISDAH Web" >nul 2>nul
if errorlevel 1 (
    echo [AVISO] No se pudo quitar la regla del firewall.
    echo         Si existe, ejecuta este script como Administrador.
) else (
    echo [OK] Regla del firewall eliminada.
)

:: -- 4. Borrar C:\whl ------------------------------------------
if exist "C:\whl\" (
    echo [*] Borrando C:\whl...
    rmdir /s /q "C:\whl" >nul 2>nul
    echo [OK] C:\whl eliminado.
)

:: -- 5. Borrar carpeta SISDAH ----------------------------------
if not "%DESTINO%"=="" (
    if exist "%DESTINO%" (
        echo [*] Borrando %DESTINO% ...
        :: salir de la carpeta por si estamos dentro
        cd /d "%USERPROFILE%"
        rmdir /s /q "%DESTINO%"
        if exist "%DESTINO%" (
            echo [AVISO] No se pudo borrar todo. Cierra ventanas que
            echo         usen esa carpeta y borra a mano: %DESTINO%
        ) else (
            echo [OK] Carpeta SISDAH eliminada por completo.
        )
    )
)

echo.
echo  =====================================================
echo  [OK] SISDAH DESINSTALADO
echo.
echo  Lo unico que queda (a proposito) es la base de datos
echo  MySQL 'sisdah' dentro de XAMPP. Si tambien quieres
echo  borrarla: abre phpMyAdmin, selecciona la base de
echo  datos 'sisdah' y pulsa "Eliminar" (Drop).
echo  =====================================================
echo.
pause
