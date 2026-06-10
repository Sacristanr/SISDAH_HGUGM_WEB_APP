@echo off
chcp 65001 >nul
title SISDAH -- Actualizacion desde USB
color 0A

:: =============================================================
::  EJECUTAR EN EL PC DEL HOSPITAL desde el USB.
::  No necesita internet. Hace todo solo:
::   1. Backup comprimido de la version actual
::   2. Copia el codigo nuevo (SIN tocar .env, BD ni certificados)
::   3. Instala dependencias desde el propio USB
::   4. Migra la base de datos y anade columnas faltantes
::   5. Verifica que la app arranca
:: =============================================================

set PKG=%~dp0

:: -- Localizar la instalacion de SISDAH ------------------------
set DESTINO=
if exist "%USERPROFILE%\Desktop\SISDAH\web\run.py" set DESTINO=%USERPROFILE%\Desktop\SISDAH
if exist "C:\Users\54421076V\Desktop\SISDAH\web\run.py" set DESTINO=C:\Users\54421076V\Desktop\SISDAH
if "%DESTINO%"=="" (
    echo [ERROR] No se encontro la instalacion de SISDAH.
    echo         Buscado en: %%USERPROFILE%%\Desktop\SISDAH
    echo.
    set /p DESTINO="Escribe la ruta de la carpeta SISDAH (la que contiene web\): "
)
if not exist "%DESTINO%\web\run.py" (
    echo [ERROR] En "%DESTINO%" no hay una instalacion valida de SISDAH.
    pause & exit /b 1
)
echo [OK] Instalacion encontrada: %DESTINO%

:: -- Localizar Python ------------------------------------------
set PYTHON=%DESTINO%\python\python.exe
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro Python en %DESTINO%\python\
    pause & exit /b 1
)
echo [OK] Python: %PYTHON%

echo.
echo  ATENCION: se va a actualizar SISDAH en %DESTINO%
echo  Cierra antes la ventana del servidor si esta abierta.
echo.
pause

:: -- 1. Backup comprimido --------------------------------------
set FECHA=%date:~-4%-%date:~3,2%-%date:~0,2%
set HORA=%time:~0,2%%time:~3,2%
set HORA=%HORA: =0%
mkdir "%DESTINO%\BACKUPS" >nul 2>nul
set ZIP=%DESTINO%\BACKUPS\%FECHA%_%HORA%_web.zip

echo.
echo [*] Creando copia de seguridad comprimida...
powershell -NoProfile -Command ^
  "Get-ChildItem -Path '%DESTINO%\web' -Recurse | Where-Object { $_.FullName -notmatch '__pycache__|\.pyc$' } | Compress-Archive -DestinationPath '%ZIP%' -Update"
if exist "%ZIP%" (
    echo [OK] Backup: %ZIP%
) else (
    echo [AVISO] No se pudo crear el backup. Continuar igualmente?
    pause
)
:: Conservar solo los 10 backups mas recientes
powershell -NoProfile -Command ^
  "Get-ChildItem '%DESTINO%\BACKUPS\' -Filter '*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 10 | Remove-Item -Force"

:: -- 2. Copiar codigo nuevo (preservando configuracion local) --
echo.
echo [*] Copiando codigo nuevo...
robocopy "%PKG%web" "%DESTINO%\web" /E /NFL /NDL /NJH /NJS ^
  /XF .env sisdah.db cert.pem key.pem server.log
if errorlevel 8 (
    echo [ERROR] Fallo al copiar el codigo. Restaura el backup si hace falta:
    echo         %ZIP%
    pause & exit /b 1
)
echo [OK] Codigo actualizado. (.env, BD y certificados intactos)

:: -- 3. Instalar dependencias desde el USB (sin internet) ------
echo.
echo [*] Instalando dependencias desde el USB...
"%PYTHON%" -m pip install -r "%DESTINO%\web\requirements.txt" --no-index --find-links "%PKG%whl" --quiet --no-warn-script-location
if errorlevel 1 (
    echo [AVISO] Alguna dependencia fallo. Detalle:
    "%PYTHON%" -m pip install -r "%DESTINO%\web\requirements.txt" --no-index --find-links "%PKG%whl"
    echo.
    echo Si falta algun .whl: descargalo en el PC de desarrollo
    echo (CREAR_PAQUETE_USB.bat lo hace solo) y regenera el paquete.
    pause
)
echo [OK] Dependencias instaladas.

:: -- 4. Migrar base de datos -----------------------------------
echo.
echo [*] Aplicando migraciones de base de datos...
cd /d "%DESTINO%\web"
"%PYTHON%" -m flask --app run.py db upgrade
if errorlevel 1 (
    echo [AVISO] flask db upgrade fallo. Probando sincronizador de columnas...
)
echo [*] Sincronizando columnas faltantes (modelos vs BD real)...
"%PYTHON%" HERRAMIENTAS\sincronizar_columnas.py --aplicar
if errorlevel 1 (
    echo [AVISO] Revisa los errores de arriba. Backup disponible en:
    echo         %ZIP%
)

:: -- 5. Verificacion final -------------------------------------
echo.
echo [*] Verificacion pre-arranque...
"%PYTHON%" check_deploy.py
if errorlevel 1 (
    echo.
    echo [AVISO] La verificacion encontro problemas. Revisa arriba.
    echo         Backup en: %ZIP%
    pause & exit /b 1
)

echo.
echo  =====================================================
echo  [OK] ACTUALIZACION COMPLETADA
echo  =====================================================
echo.
choice /C SN /M "Quieres arrancar el servidor ahora"
if errorlevel 2 goto :fin

echo.
echo [*] Arrancando servidor SISDAH...
start "SISDAH Servidor" /D "%DESTINO%\web" "%DESTINO%\web\INICIAR_SERVIDOR.bat"
echo [OK] Servidor arrancando en una ventana nueva.
echo.
echo  Prueba rapida recomendada:
echo   - Login tecnico y gestor
echo   - Abrir una ficha
echo   - Probar la nueva pantalla de Sustitucion
echo   - Imprimir una etiqueta de prueba
echo   - Escanear con el movil

:fin
echo.
pause
