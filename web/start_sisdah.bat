@echo off
set SSL_ADHOC=1
set FLASK_DEBUG=0
cd /d "C:\Users\rsacr\Desktop\PROYECTO HGUGM\web"

:: Generar certificado SSL persistente si no existe
if not exist cert.pem (
    "C:\Users\rsacr\Desktop\PROYECTO HGUGM\python\python.exe" -c "from OpenSSL import crypto; k=crypto.PKey(); k.generate_key(crypto.TYPE_RSA,2048); c=crypto.X509(); c.get_subject().CN='SISDAH'; c.set_serial_number(1); c.gmtime_adj_notBefore(0); c.gmtime_adj_notAfter(3*365*24*60*60); c.set_issuer(c.get_subject()); c.set_pubkey(k); c.sign(k,'sha256'); open('cert.pem','wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM,c)); open('key.pem','wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM,k))"
)

"C:\Users\rsacr\Desktop\PROYECTO HGUGM\python\python.exe" "C:\Users\rsacr\Desktop\PROYECTO HGUGM\web\run.py"
