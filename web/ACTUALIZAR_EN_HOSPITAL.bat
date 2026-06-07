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

:: ── 1. Copia de seguridad ────────────────────────────────────
echo.
echo [*] Creando copia de seguridad en:
echo     %BACKUP%
mkdir "%BACKUP%" >nul 2>nul

if exist "%WEB%" (
    xcopy "%WEB%*" "%BACKUP%\web\" /E /I /Q /Y >nul
    echo [OK] Copia de la carpeta "web" guardada.
) else (
    echo [AVISO] No se encontro la carpeta web a copiar.
)

if exist "E:\SISDAH\data\sisdah.db" (
    copy "E:\SISDAH\data\sisdah.db" "%BACKUP%\sisdah.db" >nul
    echo [OK] Copia de la base de datos SQLite guardada.
) else (
    echo [INFO] No se encontro sisdah.db en E:\SISDAH\data ^(puede que uses MySQL^).
    echo        Si usas MySQL, haz tu un volcado con mysqldump antes de continuar.
)

echo.
echo  =====================================================
echo  Copia de seguridad completada en:
echo  %BACKUP%
echo  Si algo falla, puedes restaurar desde esa carpeta.
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
echo  Copia de seguridad guardada en:
echo  %BACKUP%
echo.
echo  Ahora ejecuta INICIAR_SERVIDOR.bat para arrancar
echo  y haz una prueba rapida: login tecnico, login gestor,
echo  abrir una ficha y probar el escaner desde el movil.
echo  =====================================================
echo.
pause
