from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import db, Equipo, Usuario

bp = Blueprint("dashboard", __name__)


@bp.route("/home")
@login_required
def home():
    # Los equipos en "ubicacion desconocida" no se pueden retirar/usar,
    # así que no cuentan como "en stock" disponible (pero sí entran en el total,
    # que es el registro completo de todo lo que hay en el inventario).
    no_desaparecido = db.or_(Equipo.ubicacion.is_(None),
                             Equipo.ubicacion != "Ubicacion desconocida")

    stats = {
        # Total de activos: absolutamente todo lo registrado (en stock, averia,
        # retirado, reacondicionado, desaparecido...) — el registro completo.
        "total":     Equipo.query.count(),
        # En stock: lo que se puede retirar y usar ahora mismo —
        # "en stock" propiamente dicho + "reacondicionado" (ya reparado),
        # excluyendo lo que está en ubicación desconocida.
        "en_stock":  Equipo.query.filter(
                         Equipo.estado.in_(["en stock", "reacondicionado"])
                     ).filter(no_desaparecido).count(),
        "retirados": Equipo.query.filter_by(estado="retirado").count(),
        "averia":    Equipo.query.filter_by(estado="averia").count(),
        "reservados":Equipo.query.filter_by(estado="reservado").count(),
        "usuarios":  Usuario.query.filter_by(activo=True).count(),
    }

    if current_user.es_dev:
        return _home_dev(stats)

    return render_template("dashboard/home.html", stats=stats)


def _home_dev(stats):
    """Home exclusivo para rol developer — seguridad, monitorización y gestión."""
    from datetime import datetime, timedelta
    from .models import Movimiento, Solicitud, Pieza, Complemento

    ahora   = datetime.utcnow()
    hace24h = ahora - timedelta(hours=24)
    hace1h  = ahora - timedelta(hours=1)

    # ── Seguridad ─────────────────────────────────────────────────────────────
    logins_ok_24h   = Movimiento.query.filter(
        Movimiento.icm == "AUTH",
        Movimiento.descripcion.ilike("%LOGIN OK%"),
        Movimiento.fecha >= hace24h,
    ).count()
    logins_fail_24h = Movimiento.query.filter(
        Movimiento.icm == "AUTH",
        Movimiento.descripcion.ilike("%LOGIN FAIL%"),
        Movimiento.fecha >= hace24h,
    ).count()
    errores_24h = Movimiento.query.filter(
        Movimiento.icm == "ERROR",
        Movimiento.fecha >= hace24h,
    ).count()
    usuarios_bloqueados = 0
    try:
        usuarios_bloqueados = Usuario.query.filter(
            Usuario.bloqueado_hasta > ahora
        ).count()
    except Exception:
        pass

    # Últimos 8 eventos de auditoría
    ultimos_logs = Movimiento.query.filter(
        Movimiento.icm.in_(["AUTH", "ADMIN", "ERROR"])
    ).order_by(Movimiento.fecha.desc()).limit(8).all()

    # ── Sistema ───────────────────────────────────────────────────────────────
    import os, platform
    sys_info = {
        "python":  platform.python_version(),
        "os":      platform.system() + " " + platform.release(),
        "debug":   os.getenv("FLASK_DEBUG", "0") == "1",
        "secure":  os.getenv("SESSION_SECURE", "0") == "1",
        "db_user": os.getenv("DB_USER", "?"),
        "db_name": os.getenv("DB_NAME", "?"),
    }

    # ── Actividad reciente (últimos movimientos de inventario) ────────────────
    actividad = Movimiento.query.filter(
        ~Movimiento.icm.in_(["AUTH", "ADMIN", "ERROR"])
    ).order_by(Movimiento.fecha.desc()).limit(8).all()

    # ── Solicitudes pendientes ────────────────────────────────────────────────
    sol_pendientes = 0
    try:
        sol_pendientes = Solicitud.query.filter_by(estado="pendiente").count()
    except Exception:
        pass

    # ── Usuarios por rol ──────────────────────────────────────────────────────
    from sqlalchemy import func
    roles = db.session.query(
        Usuario.rol, func.count(Usuario.id)
    ).filter_by(activo=True).group_by(Usuario.rol).all()
    roles_dict = {r: c for r, c in roles}

    return render_template(
        "dashboard/home_dev.html",
        stats=stats,
        logins_ok_24h=logins_ok_24h,
        logins_fail_24h=logins_fail_24h,
        errores_24h=errores_24h,
        usuarios_bloqueados=usuarios_bloqueados,
        ultimos_logs=ultimos_logs,
        sys_info=sys_info,
        actividad=actividad,
        sol_pendientes=sol_pendientes,
        roles_dict=roles_dict,
        ahora=ahora,
    )
