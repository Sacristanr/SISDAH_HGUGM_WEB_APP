@echo off
chcp 65001 >nul
title SISDAH -- Crear paquete de actualizacion USB
color 0B

:: =============================================================
::  EJECUTAR EN EL PC DE DESARROLLO (con internet).
::  Genera una carpeta PAQUETE_SISDAH lista para copiar a un USB
::  con: codigo nuevo + dependencias .whl + script de instalacion.
::  En el hospital solo hay que ejecutar ACTUALIZAR.bat del USB.
:: =============================================================

set WEB=%~dp0..
set DEST=%~dp0..\..\PAQUETE_SISDAH

:: Detectar Python portable
set PYTHON=%~dp0..\..\python\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo.
echo  =====================================================
echo  SISDAH -- Crear paquete de actualizacion USB
echo  =====================================================
echo.
echo  Destino: %DEST%
echo.

:: Limpiar paquete anterior
if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
mkdir "%DEST%\web"
mkdir "%DEST%\whl"

:: -- 1. Copiar el codigo (sin secretos ni basura) --------------
echo [*] Copiando codigo...
robocopy "%WEB%" "%DEST%\web" /E /NFL /NDL /NJH /NJS ^
  /XD __pycache__ BACKUPS ^
  /XF .env server.log sisdah.db cert.pem key.pem *.pyc
if errorlevel 8 (
    echo [ERROR] Fallo al copiar el codigo.
    pause & exit /b 1
)
echo [OK] Codigo copiado.

:: -- 2. Descargar dependencias para instalar sin internet ------
echo.
echo [*] Descargando dependencias .whl (esto necesita internet)...
"%PYTHON%" -m pip download -r "%WEB%\requirements.txt" -d "%DEST%\whl" --quiet
if errorlevel 1 (
    echo [ERROR] Fallo la descarga de dependencias. Hay internet?
    pause & exit /b 1
)
echo [OK] Dependencias descargadas en whl\

:: -- 3. Copiar Python portable (para instalaciones desde cero) -
if exist "%~dp0..\..\python\python.exe" (
    echo [*] Copiando Python portable al paquete...
    robocopy "%~dp0..\..\python" "%DEST%\python" /E /NFL /NDL /NJH /NJS >nul
    echo [OK] Python incluido ^(permite instalar en PCs sin SISDAH^).
) else (
    echo [AVISO] No se encontro la carpeta python\ -- el paquete solo
    echo         servira para ACTUALIZAR, no para instalar desde cero.
)

:: -- 4. Copiar instalador y desinstalador al paquete -----------
copy "%~dp0plantilla_ACTUALIZAR.bat" "%DEST%\ACTUALIZAR.bat" >nul
copy "%~dp0DESINSTALAR_SISDAH.bat" "%DEST%\DESINSTALAR_SISDAH.bat" >nul 2>nul
echo [OK] Instalador ACTUALIZAR.bat incluido.

:: -- 4. Resumen ------------------------------------------------
echo.
echo  =====================================================
echo  [OK] Paquete creado en:
echo       %DEST%
echo.
echo  Pasos:
echo   1. Copia la carpeta PAQUETE_SISDAH entera a un USB
echo   2. En el PC del hospital, abre el USB y ejecuta
echo      ACTUALIZAR.bat (doble clic)
echo   3. El script hace backup, copia el codigo, instala
echo      dependencias sin internet, migra la BD y verifica.
echo  =====================================================
echo.
pause
