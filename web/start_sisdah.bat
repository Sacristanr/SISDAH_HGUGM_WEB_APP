@echo off
:: Arranque automatico de SISDAH (para carpeta Inicio de Windows)
:: Usa rutas relativas: funciona en cualquier PC donde este instalado.
set FLASK_DEBUG=0
cd /d "%~dp0"

set PYTHON=%~dp0..\python\python.exe
if not exist "%PYTHON%" set PYTHON=%USERPROFILE%\Desktop\SISDAH\python\python.exe

:: Generar certificado SSL persistente si no existe (solo si HTTPS activo)
if not exist cert.pem (
    "%PYTHON%" -c "from OpenSSL import crypto; k=crypto.PKey(); k.generate_key(crypto.TYPE_RSA,2048); c=crypto.X509(); c.get_subject().CN='SISDAH'; c.set_serial_number(1); c.gmtime_adj_notBefore(0); c.gmtime_adj_notAfter(3*365*24*60*60); c.set_issuer(c.get_subject()); c.set_pubkey(k); c.sign(k,'sha256'); open('cert.pem','wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM,c)); open('key.pem','wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM,k))" 2>/dev/null
)

"%PYTHON%" "%~dp0run.py"
