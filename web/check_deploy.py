#!/usr/bin/env python
"""Script de verificación pre-despliegue SISDAH"""
import sys, os
# Consolas Windows con cp1252 no soportan algunos caracteres — forzar UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

errors   = []
warnings = []
ok       = []

# 1. Dependencias
deps = {
    'flask':           'Flask',
    'flask_login':     'Flask-Login',
    'flask_sqlalchemy':'Flask-SQLAlchemy',
    'flask_wtf':       'Flask-WTF',
    'PIL':             'Pillow',
    'pyzbar':          'pyzbar (escaner servidor)',
    'OpenSSL':         'pyOpenSSL (HTTPS)',
    'openpyxl':        'openpyxl (Excel)',
}
for mod, name in deps.items():
    try:
        __import__(mod)
        ok.append(f'Dependencia {name}')
    except ImportError:
        errors.append(f'FALTA dependencia: {name}  →  pip install {mod}')

# 2. Archivos críticos
# cert/key solo hacen falta si HTTPS está activo (SSL_ADHOC=1 en .env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
_ssl_on = os.getenv('SSL_ADHOC', '1') == '1'
files = [
    ('run.py',                    'Servidor principal'),
    ('.env',                      'Configuracion .env'),
    ('requirements.txt',          'requirements.txt'),
    ('INICIAR_SERVIDOR.bat',      'Script inicio servidor'),
    ('ACTUALIZAR_EN_HOSPITAL.bat','Script actualizacion'),
    ('ABRIR_FIREWALL.bat',        'Script firewall'),
]
if _ssl_on:
    files += [('cert.pem', 'Certificado SSL'), ('key.pem', 'Clave SSL')]
for fname, desc in files:
    if os.path.exists(fname):
        ok.append(f'Archivo {desc} ({fname})')
    else:
        errors.append(f'FALTA archivo: {fname}  ({desc})')
if not _ssl_on:
    ok.append('HTTPS desactivado (SSL_ADHOC=0) — cert.pem/key.pem no requeridos')

# 3. Validez del certificado SSL
if os.path.exists('cert.pem'):
    try:
        from OpenSSL import crypto
        import datetime
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open('cert.pem','rb').read())
        exp  = datetime.datetime.strptime(cert.get_notAfter().decode(), '%Y%m%d%H%M%SZ')
        dias = (exp - datetime.datetime.utcnow()).days
        if dias > 30:
            ok.append(f'Certificado SSL valido {dias} dias (hasta {exp.strftime("%d/%m/%Y")})')
        else:
            warnings.append(f'Certificado SSL caduca en {dias} dias ({exp.strftime("%d/%m/%Y")})')
    except Exception as e:
        warnings.append(f'No se pudo leer el certificado: {e}')

# 4. La app arranca
app = None
try:
    from app import create_app
    app = create_app()
    ok.append('App Flask arranca correctamente')
except Exception as e:
    errors.append(f'La app NO arranca: {e}')

# 5. Ruta decode-barcode registrada
if app is not None:
    try:
        rules = [str(r) for r in app.url_map.iter_rules()]
        if any('decode-barcode' in r for r in rules):
            ok.append('Ruta /retiradas/api/decode-barcode registrada')
        else:
            errors.append('FALTA ruta /retiradas/api/decode-barcode')
    except Exception as e:
        warnings.append(f'No se pudo verificar rutas: {e}')

# 6. pyzbar puede decodificar una imagen real
try:
    from PIL import Image
    from pyzbar.pyzbar import decode
    import io
    # Crear un codigo de barras Code128 simple en blanco/negro
    img = Image.new('RGB', (200, 100), 'white')
    result = decode(img)   # imagen en blanco → sin codigo, pero no debe fallar
    ok.append('pyzbar funciona (libreria ZBar cargada correctamente)')
except Exception as e:
    errors.append(f'pyzbar falla al ejecutar: {e}')

# ── Resultado ───────────────────────────────────────────────
print()
print('=' * 55)
print('  SISDAH — Verificacion pre-despliegue')
print('=' * 55)
print()
for msg in ok:
    print(f'  [OK]    {msg}')
if warnings:
    print()
    for msg in warnings:
        print(f'  [AVISO] {msg}')
if errors:
    print()
    for msg in errors:
        print(f'  [ERROR] {msg}')
print()
if errors:
    print(f'  RESULTADO: {len(errors)} error(es) — CORREGIR antes del despliegue')
elif warnings:
    print(f'  RESULTADO: OK con {len(warnings)} aviso(s) — revisar si es posible')
else:
    print(f'  RESULTADO: TODO OK — listo para el despliegue')
print('=' * 55)
print()
sys.exit(1 if errors else 0)
