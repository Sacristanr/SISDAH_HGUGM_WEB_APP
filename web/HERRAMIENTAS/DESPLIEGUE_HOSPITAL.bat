@echo off
chcp 65001 >nul
title SISDAH -- Despliegue en equipo nuevo
color 0B

set PYTHON=%~dp0..\python\python.exe
set WEB=%~dp0

echo.
echo  =====================================================
echo  SISDAH -- Script de despliegue en equipo nuevo
echo  HGUGM Departamento de Informatica
echo  =====================================================
echo.

:: 1. Verificar Python portable
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro Python portable en ..\python\python.exe
    echo         Copia la carpeta "python" junto a la carpeta "web"
    pause & exit /b 1
)
echo [OK] Python portable encontrado.

:: 2. Instalar/actualizar dependencias
echo.
echo [*] Instalando dependencias Python...
"%PYTHON%" -m pip install -r "%WEB%requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause & exit /b 1
)
echo [OK] Dependencias instaladas.

:: 3. Verificar .env
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

:: 4. Ejecutar migracion de seguridad (añade columnas si no existen)
echo.
echo [*] Aplicando migracion de base de datos...
cd /d "%WEB%"
"%PYTHON%" migrar_seguridad.py
if errorlevel 1 (
    echo [AVISO] La migracion tuvo algun problema. Revisa la BD manualmente.
) else (
    echo [OK] Base de datos actualizada.
)

:: 5. Verificar que la app arranca
echo.
echo [*] Verificando que la aplicacion arranca correctamente...
"%PYTHON%" -c "import sys; sys.path.insert(0,'.'); from app import create_app; create_app(); print('[OK] App verificada correctamente.')"
if errorlevel 1 (
    echo [ERROR] La aplicacion no arranca. Revisa el .env y la conexion a MySQL.
    pause & exit /b 1
)

echo.
echo  =====================================================
echo  [OK] Despliegue completado con exito.
echo.
echo  Ejecuta INICIAR_SERVIDOR.bat para arrancar.
echo  URL: http://localhost:5000
echo  =====================================================
echo.
pause
