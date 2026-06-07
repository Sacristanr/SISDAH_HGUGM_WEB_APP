from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user
from .models import db, Usuario, Equipo, Movimiento
from .sanitize import clean_dni, clean_text, clean_email, is_valid_email, clean_log_field
from functools import wraps
from datetime import datetime

bp = Blueprint("admin", __name__, url_prefix="/admin")


def solo_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@login_required
@solo_admin
def panel():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    total    = Equipo.query.count()
    return render_template("admin/panel.html", usuarios=usuarios, total=total)


@bp.route("/usuarios")
@login_required
@solo_admin
def usuarios():
    lista = Usuario.query.order_by(Usuario.nombre).all()
    return render_template("admin/usuarios.html", usuarios=lista)


@bp.route("/usuarios/<int:uid>/toggle", methods=["POST"])
@login_required
@solo_admin
def toggle_activo(uid):
    u = Usuario.query.get_or_404(uid)
    u.activo = not u.activo
    db.session.commit()
    return jsonify({"ok": True, "activo": u.activo})


@bp.route("/reasignar")
@login_required
@solo_admin
def reasignar():
    historial = Movimiento.query.filter_by(tipo="reasignacion").order_by(
        Movimiento.fecha.desc()).limit(20).all()
    return render_template("admin/reasignar.html", historial=historial)


@bp.route("/reasignar/buscar")
@login_required
@solo_admin
def reasignar_buscar():
    icm = request.args.get("icm", "").strip().upper()
    eq  = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": f"ICM '{icm}' no encontrado"})
    return jsonify({"ok": True, "equipo": eq.to_dict()})


@bp.route("/reasignar/aplicar", methods=["POST"])
@login_required
@solo_admin
def reasignar_aplicar():
    data     = request.get_json(silent=True) or {}
    icm      = clean_text(data.get("icm", ""), max_len=40).upper()
    eq       = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": "ICM no encontrado"})

    seccion   = clean_text(data.get("seccion", ""), max_len=80)
    estado    = clean_text(data.get("estado", ""), max_len=20)
    ubicacion = clean_text(data.get("ubicacion", ""), max_len=150)
    notas     = clean_text(data.get("notas", ""), max_len=500)

    cambios = []
    if seccion:
        cambios.append(f"sección: {eq.seccion} → {seccion}")
        eq.seccion = seccion
    if estado:
        cambios.append(f"estado: {eq.estado} → {estado}")
        eq.estado = estado
    if ubicacion:
        eq.ubicacion = ubicacion
        cambios.append(f"ubicación: {ubicacion}")
    if notas:
        eq.notas = notas

    desc = clean_log_field(notas or (", ".join(cambios) if cambios else "Reasignación"), max_len=500)
    mov  = Movimiento(icm=icm, tipo="reasignacion",
                      usuario_dni=current_user.dni,
                      descripcion=desc, pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/versiones")
@login_required
def versiones():
    if not current_user.es_dev:
        abort(403)
    from .version import VERSION, BUILD_DATE, RELEASE_NAME, CHANGELOG
    return render_template("admin/versiones.html",
                           version=VERSION, build=BUILD_DATE,
                           release=RELEASE_NAME, changelog=CHANGELOG)


@bp.route("/seguridad")
@login_required
def seguridad():
    if not current_user.es_dev:
        abort(403)

    from datetime import datetime, timedelta
    import sys, platform

    # ── Logs de auditoría (AUTH / ADMIN) ─────────────────────────────────────
    page     = request.args.get("page", 1, type=int)
    tipo_f   = request.args.get("tipo", "")        # filtro: acceso | admin | error
    q_f      = request.args.get("q", "").strip()   # búsqueda libre

    audit_q = Movimiento.query.filter(
        Movimiento.icm.in_(["AUTH", "ADMIN", "ERROR"])
    )
    if tipo_f:
        audit_q = audit_q.filter(Movimiento.tipo == tipo_f)
    if q_f:
        audit_q = audit_q.filter(
            db.or_(
                Movimiento.usuario_dni.ilike(f"%{q_f}%"),
                Movimiento.descripcion.ilike(f"%{q_f}%"),
                Movimiento.pc.ilike(f"%{q_f}%"),
            )
        )
    audit_q  = audit_q.order_by(Movimiento.fecha.desc())
    per_page = 50
    total    = audit_q.count()
    logs     = audit_q.offset((page - 1) * per_page).limit(per_page).all()
    pages    = (total + per_page - 1) // per_page

    # ── Estadísticas rápidas ─────────────────────────────────────────────────
    from datetime import timezone
    ahora   = datetime.utcnow()
    hace24h = ahora - timedelta(hours=24)
    logins_ok   = Movimiento.query.filter(
        Movimiento.icm == "AUTH",
        Movimiento.tipo == "acceso",
        Movimiento.descripcion.ilike("%LOGIN OK%"),
        Movimiento.fecha >= hace24h,
    ).count()
    logins_fail = Movimiento.query.filter(
        Movimiento.icm == "AUTH",
        Movimiento.tipo == "acceso",
        Movimiento.descripcion.ilike("%LOGIN FAIL%"),
        Movimiento.fecha >= hace24h,
    ).count()
    cambios_admin = Movimiento.query.filter(
        Movimiento.icm == "ADMIN",
        Movimiento.fecha >= hace24h,
    ).count()
    usuarios_bloqueados = Usuario.query.filter(
        Usuario.bloqueado_hasta > ahora
    ).count() if hasattr(Usuario, "bloqueado_hasta") else 0

    # ── Info del sistema ─────────────────────────────────────────────────────
    import os
    sys_info = {
        "python":   platform.python_version(),
        "os":       platform.system() + " " + platform.release(),
        "debug":    os.getenv("FLASK_DEBUG", "0"),
        "secure":   os.getenv("SESSION_SECURE", "0"),
        "db_user":  os.getenv("DB_USER", "?"),
        "uptime":   "—",  # no disponible sin psutil
    }

    # ── Usuarios con incidencias de seguridad ────────────────────────────────
    usuarios_lista = Usuario.query.order_by(Usuario.nombre).all()

    return render_template(
        "admin/seguridad.html",
        logs=logs, page=page, pages=pages, total=total,
        tipo_f=tipo_f, q_f=q_f,
        logins_ok=logins_ok, logins_fail=logins_fail,
        cambios_admin=cambios_admin,
        usuarios_bloqueados=usuarios_bloqueados,
        sys_info=sys_info,
        usuarios_lista=usuarios_lista,
    )


@bp.route("/email_resumen")
@login_required
@solo_admin
def email_resumen():
    from .models import ConfigApp
    smtp_dest = ConfigApp.get("smtp_dest", "")
    smtp_host = ConfigApp.get("smtp_host", "")
    return render_template("admin/email_resumen.html",
                           total=Equipo.query.count(),
                           en_stock=Equipo.query.filter_by(estado="en stock").count(),
                           retirados=Equipo.query.filter_by(estado="retirado").count(),
                           averias=Equipo.query.filter_by(estado="averia").count(),
                           smtp_dest=smtp_dest,
                           smtp_configurado=bool(smtp_host))


@bp.route("/email/enviar", methods=["POST"])
@login_required
@solo_admin
def email_enviar():
    from .email_utils import enviar_resumen
    data   = request.get_json()
    dest   = data.get("dest", "").strip()
    asunto = data.get("asunto", "Resumen SISDAH")
    notas  = data.get("notas", "")
    ok, msg = enviar_resumen(dest, asunto, notas)
    return jsonify({"ok": ok, "error": msg if not ok else ""})


from config import ROLES_VALIDOS, MIN_PASSWORD_LEN
from .models import validar_password


@bp.route("/usuarios/crear", methods=["POST"])
@login_required
@solo_admin
def crear_usuario():
    data   = request.get_json(silent=True) or {}
    dni    = clean_dni(data.get("dni", ""))
    nombre = clean_text(data.get("nombre", ""), max_len=100)
    email  = clean_email(data.get("email", "")) or None
    rol    = clean_text(data.get("rol", "tecnico"), max_len=20)

    if not dni or not nombre:
        return jsonify({"ok": False, "error": "DNI y nombre obligatorios"})
    if len(dni) > 20 or len(nombre) > 100:
        return jsonify({"ok": False, "error": "Datos demasiado largos"})
    if email and not is_valid_email(email):
        return jsonify({"ok": False, "error": "Email no válido"})
    if rol not in ROLES_VALIDOS:
        return jsonify({"ok": False, "error": "Rol no válido"})
    # Solo developer puede crear otro developer
    if rol == "developer" and not current_user.es_dev:
        return jsonify({"ok": False, "error": "Solo un desarrollador puede crear otro desarrollador"}), 403
    if Usuario.query.filter_by(dni=dni).first():
        return jsonify({"ok": False, "error": "DNI ya registrado"})

    u = Usuario(dni=dni, nombre=nombre, email=email, rol=rol)
    if rol != "tecnico":
        password = data.get("password", "")
        if not password:
            return jsonify({"ok": False, "error": "La contraseña es obligatoria para este rol"})
        ok, msg = validar_password(password)
        if not ok:
            return jsonify({"ok": False, "error": f"Contraseña débil: {msg}"})
        u.set_password(password)
    db.session.add(u)
    db.session.commit()

    # Auditoría
    mov = Movimiento(icm="ADMIN", tipo="modificacion",
                     usuario_dni=current_user.dni,
                     descripcion=f"Usuario creado: {dni} rol={rol}",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True, "id": u.id})


@bp.route("/usuarios/<int:uid>/rol", methods=["POST"])
@login_required
@solo_admin
def cambiar_rol(uid):
    u   = Usuario.query.get_or_404(uid)
    rol = clean_text((request.get_json(silent=True) or {}).get("rol", "tecnico"), max_len=20)

    if rol not in ROLES_VALIDOS:
        return jsonify({"ok": False, "error": "Rol no válido"}), 400
    # Solo developer puede asignar/quitar rol developer
    if (rol == "developer" or u.rol == "developer") and not current_user.es_dev:
        return jsonify({"ok": False, "error": "Solo un desarrollador puede modificar ese rol"}), 403
    # No puede cambiar su propio rol
    if u.id == current_user.id:
        return jsonify({"ok": False, "error": "No puedes cambiar tu propio rol"}), 400

    rol_anterior = u.rol
    u.rol = rol
    mov = Movimiento(icm="ADMIN", tipo="modificacion",
                     usuario_dni=current_user.dni,
                     descripcion=f"Cambio rol {u.dni}: {rol_anterior} → {rol}",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/usuarios/<int:uid>/password", methods=["POST"])
@login_required
@solo_admin
def cambiar_password(uid):
    u   = Usuario.query.get_or_404(uid)
    pwd = request.get_json().get("password", "")
    if not pwd:
        return jsonify({"ok": False, "error": "Contraseña vacía"})
    # Solo developer puede cambiar la contraseña de otro developer
    if u.rol == "developer" and not current_user.es_dev:
        return jsonify({"ok": False, "error": "Sin permisos para modificar esta cuenta"}), 403
    ok, msg = validar_password(pwd)
    if not ok:
        return jsonify({"ok": False, "error": f"Contraseña débil: {msg}"})
    u.set_password(pwd)
    u.intentos_fallidos = 0
    u.bloqueado_hasta   = None
    mov = Movimiento(icm="ADMIN", tipo="modificacion",
                     usuario_dni=current_user.dni,
                     descripcion=f"Contraseña cambiada para {u.dni}",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/usuarios/<int:uid>/eliminar", methods=["POST"])
@login_required
@solo_admin
def eliminar_usuario(uid):
    u = Usuario.query.get_or_404(uid)
    if u.id == current_user.id:
        return jsonify({"ok": False, "error": "No puedes eliminarte a ti mismo"}), 400
    if u.rol == "developer" and not current_user.es_dev:
        return jsonify({"ok": False, "error": "Sin permisos para eliminar esta cuenta"}), 403
    mov = Movimiento(icm="ADMIN", tipo="modificacion",
                     usuario_dni=current_user.dni,
                     descripcion=f"Usuario eliminado: {u.dni} ({u.rol})",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True})
