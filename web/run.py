import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    port  = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"   # produccion por defecto; FLASK_DEBUG=1 para desarrollo

    # ── HTTPS con certificado autofirmado ────────────────────────────────
    # Los navegadores solo permiten getUserMedia (cámara/micrófono) en
    # "contextos seguros": HTTPS o localhost. Para poder usar el escáner de
    # códigos con la cámara del móvil dentro de la red del hospital (acceso
    # por IP, sin dominio), activamos HTTPS con un certificado autofirmado.
    # La primera vez el navegador avisará de "certificado no confiable":
    # hay que aceptar el aviso una vez y la conexión queda marcada como
    # segura, habilitando el acceso a la cámara con normalidad.
    # HTTPS con certificado persistente (se genera una vez y se reutiliza).
    # Así el navegador solo pide aceptarlo una vez y no vuelve a quejarse.
    # Para deshabilitar HTTPS: SSL_ADHOC=0
    if os.getenv("SSL_ADHOC", "1") == "1":
        cert = os.path.join(os.path.dirname(__file__), "cert.pem")
        key  = os.path.join(os.path.dirname(__file__), "key.pem")
        if os.path.exists(cert) and os.path.exists(key):
            ssl_context = (cert, key)   # certificado persistente
        else:
            ssl_context = "adhoc"       # fallback: genera uno nuevo
    else:
        ssl_context = None

    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug,
            ssl_context=ssl_context)
