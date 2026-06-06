from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from .models import db, Equipo, Movimiento, Usuario
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint("estadisticas", __name__, url_prefix="/estadisticas")


@bp.route("/")
@login_required
def panel():
    # Por sección
    por_seccion = db.session.query(
        Equipo.seccion, func.count(Equipo.id)
    ).group_by(Equipo.seccion).order_by(func.count(Equipo.id).desc()).all()

    # Por marca
    por_marca = db.session.query(
        Equipo.marca, func.count(Equipo.id)
    ).group_by(Equipo.marca).order_by(func.count(Equipo.id).desc()).limit(10).all()

    # Por estado
    por_estado = db.session.query(
        Equipo.estado, func.count(Equipo.id)
    ).group_by(Equipo.estado).all()

    # Movimientos últimos 30 días
    hace_30 = datetime.utcnow() - timedelta(days=30)
    mov_recientes = Movimiento.query.filter(
        Movimiento.fecha >= hace_30
    ).order_by(Movimiento.fecha.desc()).limit(50).all()

    # Retiradas por técnico
    por_tecnico = db.session.query(
        Equipo.retirado_por, func.count(Equipo.id)
    ).filter(Equipo.estado == "retirado", Equipo.retirado_por != None
    ).group_by(Equipo.retirado_por).order_by(func.count(Equipo.id).desc()).limit(10).all()

    stats = {
        "total":      Equipo.query.count(),
        "en_stock":   Equipo.query.filter_by(estado="en stock").count(),
        "retirados":  Equipo.query.filter_by(estado="retirado").count(),
        "averia":     Equipo.query.filter_by(estado="averia").count(),
        "reservados": Equipo.query.filter_by(estado="reservado").count(),
        "papelera":   Equipo.query.filter_by(estado="papelera").count(),
        "usuarios":   Usuario.query.filter_by(activo=True).count(),
        "movimientos":Movimiento.query.count(),
    }

    return render_template("estadisticas/panel.html",
                           stats=stats, por_seccion=por_seccion,
                           por_marca=por_marca, por_estado=por_estado,
                           mov_recientes=mov_recientes, por_tecnico=por_tecnico)
