@echo off
chcp 65001 >nul
title SISDAH -- Actualizacion en equipo del hospital
color 0B

set PYTHON=%~dp0..\python\python.exe
set WEB=%~dp0
set FECHA=%date:~-4%-%date:~3,2%-%date:~0,2%
set HORA=%time:~0,2%%time:~3,2%
set HORA=%HORA: =0%
set BACKUP=%~dp0..\BACKUPS\%FECHA%_%HORA%

echo.
echo  =====================================================
echo  SISDAH -- Actualizacion en equipo del hospital
echo  HGUGM Departamento de Informatica
echo  =====================================================
echo.
echo  Este script va a:
echo   1. Hacer una copia de seguridad de la version actual
echo   2. Instalar/actualizar dependencias
echo   3. Aplicar migraciones de base de datos
echo   4. Verificar que la app arranca
echo   5. Dejarlo listo para iniciar con INICIAR_SERVIDOR.bat
echo.
echo  (El firewall NO se toca aqui -- usa ABRIR_FIREWALL.bat aparte
echo   solo si es la primera instalacion en este equipo)
echo.
pause

:: ── 1. Copia de seguridad comprimida ─────────────────────────
echo.
echo [*] Creando copia de seguridad comprimida...
mkdir "%~dp0..\BACKUPS" >nul 2>nul

set ZIP_WEB=%~dp0..\BACKUPS\%FECHA%_%HORA%_web.zip
set ZIP_DB=%~dp0..\BACKUPS\%FECHA%_%HORA%_db.zip

:: Comprimir carpeta web (excluyendo __pycache__ y .pyc)
echo [*] Comprimiendo carpeta web...
powershell -NoProfile -Command ^
  "Get-ChildItem -Path '%WEB%' -Recurse | Where-Object { $_.FullName -notmatch '__pycache__|\.pyc$' } | Compress-Archive -DestinationPath '%ZIP_WEB%' -Update"
if exist "%ZIP_WEB%" (
    echo [OK] Web comprimida: %ZIP_WEB%
) else (
    echo [AVISO] No se pudo comprimir la carpeta web.
)

:: Comprimir base de datos SQLite si existe
if exist "%WEB%sisdah.db" (
    powershell -NoProfile -Command "Compress-Archive -Path '%WEB%sisdah.db' -DestinationPath '%ZIP_DB%' -Force"
    echo [OK] Base de datos comprimida: %ZIP_DB%
) else (
    echo [INFO] No hay sisdah.db local ^(probablemente usas MySQL^).
)

:: Limpiar backups antiguos — conservar solo los 10 mas recientes
powershell -NoProfile -Command ^
  "Get-ChildItem '%~dp0..\BACKUPS\' -Filter '*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 10 | Remove-Item -Force"

echo.
echo  =====================================================
echo  Copia de seguridad completada.
echo  Guardada en: BACKUPS\
echo  Se conservan los 10 backups mas recientes.
echo  =====================================================
echo.
pause

:: ── 2. Verificar Python portable ─────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro Python portable en ..\python\python.exe
    echo         Copia la carpeta "python" junto a la carpeta "web"
    pause & exit /b 1
)
echo [OK] Python portable encontrado.

:: ── 3. Instalar/actualizar dependencias ──────────────────────
echo.
echo [*] Instalando dependencias Python...
"%PYTHON%" -m pip install -r "%WEB%requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    echo         Puedes restaurar la copia de seguridad de %BACKUP% si hace falta.
    pause & exit /b 1
)
echo [OK] Dependencias instaladas.

:: ── 4. Verificar .env ─────────────────────────────────────────
if not exist "%WEB%.env" (
    echo.
    echo [!] No se encontro el archivo .env
    echo     Copiando plantilla .env.example como .env...
    copy "%WEB%.env.example" "%WEB%.env" >nul
    echo.
    echo  =====================================================
    echo  IMPORTANTE: Antes de continuar debes editar .env
    echo  con los datos reales de MySQL y la SECRET_KEY.
    echo  =====================================================
    echo.
    notepad "%WEB%.env"
    echo [*] Cuando hayas guardado .env, pulsa cualquier tecla para continuar...
    pause >nul
)
echo [OK] Archivo .env encontrado.

:: ── 5. Migracion de base de datos ─────────────────────────────
echo.
echo [*] Aplicando migracion de base de datos...
cd /d "%WEB%"
"%PYTHON%" migrar_seguridad.py
if errorlevel 1 (
    echo [AVISO] La migracion tuvo algun problema. Revisa la BD manualmente.
    echo         Tienes la copia de seguridad en %BACKUP% por si hay que restaurar.
) else (
    echo [OK] Base de datos actualizada.
)

:: ── 6. Verificar que la app arranca ──────────────────────────
echo.
echo [*] Verificando que la aplicacion arranca correctamente...
"%PYTHON%" -c "import sys; sys.path.insert(0,'.'); from app import create_app; create_app(); print('[OK] App verificada correctamente.')"
if errorlevel 1 (
    echo [ERROR] La aplicacion no arranca. Revisa el .env y la conexion a la BD.
    echo         Restaura la copia de seguridad de %BACKUP% si es necesario.
    pause & exit /b 1
)

echo.
echo  =====================================================
echo  [OK] Actualizacion completada con exito.
echo.
echo  Copia de seguridad comprimida en:
echo  BACKUPS\%FECHA%_%HORA%_web.zip
echo.
echo  Ahora ejecuta INICIAR_SERVIDOR.bat para arrancar
echo  y haz una prueba rapida: login tecnico, login gestor,
echo  abrir una ficha y probar el escaner desde el movil.
echo  =====================================================
echo.
pause
