from flask import Flask, request, session as fsession
from flask_login import LoginManager, current_user as cu
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from .models import db, Usuario
from config import Config
from datetime import timedelta

login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "warning"
    app.permanent_session_lifetime = timedelta(hours=8)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ── Headers de seguridad (respuesta a todo) ──────────────────────────────
    @app.after_request
    def set_security_headers(response):
        # Evita que la app se incruste en iframes (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"
        # Evita MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # No enviar Referer a terceros
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Deshabilitar caché en respuestas autenticadas
        if "/static/" not in request.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"]         = "no-cache"
        # Content Security Policy — restringida: solo fuentes propias + CDN Bootstrap/BI
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        # HSTS — solo si se sirve por HTTPS
        import os
        if os.getenv("SESSION_SECURE", "0") == "1":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Versión global disponible en todas las plantillas ────────────────────
    from .version import VERSION, BUILD_DATE, RELEASE_NAME
    @app.context_processor
    def inject_version():
        return {"app_version": VERSION, "app_build": BUILD_DATE, "app_release": RELEASE_NAME}

    # ── Renovar sesión en cada request (deslizante) ──────────────────────────
    @app.before_request
    def refresh_session():
        if cu.is_authenticated:
            fsession.modified = True  # prolonga la cookie en cada petición

    # ── Capturar errores 500 y registrarlos en BD para el panel DEV ──────────
    @app.errorhandler(500)
    def error_500(e):
        import traceback
        from .models import Movimiento
        try:
            desc = f"500 {request.method} {request.path} — {str(e)[:300]}"
            tb   = traceback.format_exc()
            # Guardamos el traceback truncado en descripcion
            mov  = Movimiento(
                icm="ERROR", tipo="error",
                usuario_dni=cu.dni if cu.is_authenticated else "anon",
                descripcion=desc + "\n" + tb[:600],
                pc=request.remote_addr,
            )
            db.session.add(mov)
            db.session.commit()
        except Exception:
            db.session.rollback()
        from flask import render_template as rt
        return rt("errors/500.html"), 500

    @app.errorhandler(404)
    def error_404(e):
        from flask import render_template as rt
        return rt("errors/404.html"), 404

    # ── CSRF expirado: redirigir al login con mensaje claro ──────────────────
    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def error_csrf(e):
        from flask import redirect, url_for, flash
        flash("Tu sesión ha expirado. Vuelve a iniciar sesión.", "warning")
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_solicitudes_badge():
        from flask_login import current_user
        from .models import Solicitud
        try:
            if current_user.is_authenticated:
                if current_user.es_gestor:
                    n = Solicitud.query.filter_by(estado="pendiente").count()
                else:
                    n = Solicitud.query.filter_by(
                        solicitante_dni=current_user.dni, estado="pendiente").count()
                return {"solicitudes_pendientes": n}
        except Exception:
            pass
        return {"solicitudes_pendientes": 0}

    from .auth          import bp as auth_bp
    from .inventario    import bp as inv_bp
    from .registrar     import bp as reg_bp
    from .retiradas     import bp as ret_bp
    from .admin         import bp as adm_bp
    from .dashboard     import bp as dash_bp
    from .estadisticas  import bp as est_bp
    from .historial     import bp as his_bp
    from .papelera      import bp as pap_bp
    from .telefonos     import bp as tel_bp
    from .licencias     import bp as lic_bp
    from .piezas        import bp as pie_bp
    from .reservas      import bp as res_bp
    from .configuracion import bp as cfg_bp
    from .revision       import bp as rev_bp
    from .search         import bp as srch_bp
    from .fichas         import bp as fic_bp
    from .exports        import bp as exp_bp
    from .usuarios_hist  import bp as uhist_bp
    from .exproveedores  import bp as eprov_bp
    from .etiquetas      import bp as etiq_bp
    from .ap_wifi        import bp as apwifi_bp
    from .catalogo       import bp as cat_bp
    from .solicitudes    import bp as sol_bp

    # Exempt exports from CSRF (GET downloads)
    csrf.exempt(exp_bp)

    for blueprint in [auth_bp, inv_bp, reg_bp, ret_bp, adm_bp, dash_bp,
                      est_bp, his_bp, pap_bp, tel_bp, lic_bp, pie_bp,
                      res_bp, cfg_bp, rev_bp, srch_bp, fic_bp, exp_bp,
                      uhist_bp, eprov_bp, etiq_bp, apwifi_bp, cat_bp, sol_bp]:
        app.register_blueprint(blueprint)

    with app.app_context():
        db.create_all()
        _seed_admin(app)
        from .catalogo_data import seed_catalogo
        from .models import CatalogoItem
        seed_catalogo(db, CatalogoItem)

    return app


def _seed_admin(app):
    with app.app_context():
        if Usuario.query.count() == 0:
            demo = Usuario(dni="TECNICO", nombre="Técnico Demo", rol="tecnico")
            db.session.add(demo)
            db.session.commit()
