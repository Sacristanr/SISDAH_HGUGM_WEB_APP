import hashlib, time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, Usuario
from .sanitize import clean_dni, clean_text, clean_log_field
from config import EMERGENCY_DNI, EMERGENCY_HASH, ROL_N3

bp = Blueprint("auth", __name__)


# ── Rate limiting simple en memoria (sin dependencias extra) ─────────────────
_login_attempts: dict = defaultdict(list)   # ip → [timestamps]
_lock = Lock()
_MAX_ATTEMPTS = 5        # intentos por ventana
_WINDOW_SECS  = 300      # ventana de 5 minutos
_BLOCK_SECS   = 900      # bloqueo 15 minutos tras superar límite

def _get_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

def _check_rate_limit(ip: str) -> tuple[bool, int]:
    """(permitido, segundos_restantes). Limpia entradas expiradas."""
    now = time.time()
    with _lock:
        _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECS]
        count = len(_login_attempts[ip])
        if count >= _MAX_ATTEMPTS:
            oldest = _login_attempts[ip][0]
            wait   = int(_BLOCK_SECS - (now - oldest))
            return False, max(wait, 0)
        return True, 0

def _record_attempt(ip: str):
    with _lock:
        _login_attempts[ip].append(time.time())

def _clear_attempts(ip: str):
    with _lock:
        _login_attempts.pop(ip, None)


def _hash_sha256(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def _log_acceso(dni: str, ok: bool, motivo: str = ""):
    """Registra intentos de login en la tabla movimientos como auditoría."""
    try:
        from .models import Movimiento
        ip   = _get_ip()
        dni  = clean_log_field(dni, max_len=20)
        desc = f"LOGIN {'OK' if ok else 'FAIL'} — {clean_log_field(motivo)}" if motivo else f"LOGIN {'OK' if ok else 'FAIL'}"
        mov = Movimiento(icm="AUTH", tipo="acceso",
                         usuario_dni=dni, descripcion=desc, pc=clean_log_field(ip, max_len=64))
        db.session.add(mov)
        db.session.commit()
    except Exception:
        db.session.rollback()


@bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        ip = _get_ip()
        permitido, wait = _check_rate_limit(ip)
        if not permitido:
            mins = wait // 60 + 1
            flash(f"Demasiados intentos fallidos. Espera {mins} minuto(s) antes de volver a intentarlo.", "danger")
            return render_template("auth/login.html")

        rol_tipo = request.form.get("rol_tipo")

        # ── Login técnico (DNI sin contraseña) ───────────────────
        if rol_tipo == "tecnico":
            dni = clean_dni(request.form.get("dni_tecnico", ""))
            if not dni:
                flash("Introduce tu DNI.", "danger")
                return render_template("auth/login.html")

            usuario = Usuario.query.filter(
                (Usuario.dni == dni) &
                (Usuario.activo == True) &
                (Usuario.rol == "tecnico")
            ).first()

            if not usuario:
                _record_attempt(ip)
                _log_acceso(dni, False, "DNI técnico no encontrado")
                flash("DNI no encontrado o sin acceso de técnico. Contacta con administración.", "danger")
                return render_template("auth/login.html")

            # Renovar sesión para evitar session fixation
            session.clear()
            session.permanent = True
            login_user(usuario, remember=False)

            # Actualizar último acceso
            usuario.ultimo_acceso = datetime.utcnow()
            usuario.intentos_fallidos = 0
            db.session.commit()

            _clear_attempts(ip)
            _log_acceso(dni, True, "técnico")
            return redirect(url_for("dashboard.home"))

        # ── Login gestor/admin (DNI+contraseña) ──────────────────
        elif rol_tipo == "gestor":
            identificador = clean_text(request.form.get("identificador", ""), max_len=120)
            password      = request.form.get("password", "")[:200]  # límite defensivo, sin tocar el contenido

            if not identificador or not password:
                flash("Introduce usuario y contraseña.", "danger")
                return render_template("auth/login.html")

            # Credencial de emergencia
            if identificador.upper() == EMERGENCY_DNI and _hash_sha256(password) == EMERGENCY_HASH:
                usuario = Usuario.query.filter_by(dni=EMERGENCY_DNI).first()
                if not usuario:
                    usuario = Usuario(dni=EMERGENCY_DNI, nombre="Administrador Emergencia",
                                      rol=ROL_N3, activo=True)
                    db.session.add(usuario)
                    db.session.commit()

                session.clear()
                session.permanent = True
                login_user(usuario, remember=False)
                usuario.ultimo_acceso = datetime.utcnow()
                db.session.commit()

                _clear_attempts(ip)
                _log_acceso(EMERGENCY_DNI, True, "acceso emergencia")
                flash("⚠️ Acceso de emergencia activo. Cambia las credenciales cuanto antes.", "warning")
                return redirect(url_for("dashboard.home"))

            # Usuario normal
            usuario = Usuario.query.filter(
                ((Usuario.dni == identificador.upper()) |
                 (Usuario.email == identificador.lower())) &
                (Usuario.activo == True)
            ).first()

            # Comprobar bloqueo por intentos fallidos
            if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > datetime.utcnow():
                wait_min = int((usuario.bloqueado_hasta - datetime.utcnow()).seconds / 60) + 1
                _record_attempt(ip)
                flash(f"Cuenta bloqueada por intentos fallidos. Espera {wait_min} minuto(s).", "danger")
                return render_template("auth/login.html")

            if not usuario or not usuario.check_password(password):
                _record_attempt(ip)
                if usuario:
                    usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
                    if usuario.intentos_fallidos >= 5:
                        usuario.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=15)
                        flash("Cuenta bloqueada 15 minutos por demasiados intentos.", "danger")
                    else:
                        flash("Credenciales incorrectas.", "danger")
                    db.session.commit()
                else:
                    flash("Credenciales incorrectas.", "danger")
                _log_acceso(identificador, False, "contraseña incorrecta")
                return render_template("auth/login.html")

            if usuario.rol == "tecnico":
                flash("Tu cuenta no tiene acceso de gestor.", "danger")
                return render_template("auth/login.html")

            session.clear()
            session.permanent = True
            login_user(usuario, remember=False)
            usuario.ultimo_acceso    = datetime.utcnow()
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta  = None
            db.session.commit()

            _clear_attempts(ip)
            _log_acceso(usuario.dni, True, usuario.rol)
            return redirect(url_for("dashboard.home"))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    _log_acceso(current_user.dni, True, "logout")
    session.clear()
    logout_user()
    return redirect(url_for("auth.login"))
