from flask import Blueprint, render_template, request
from flask_login import login_required
from .models import db, Movimiento, Equipo, Usuario
from sqlalchemy import func

bp = Blueprint("usuarios_hist", __name__, url_prefix="/usuarios/historial")


@bp.route("/")
@login_required
def buscar():
    q = request.args.get("q", "").strip().upper()
    usuario = None
    movimientos = []
    stats = {}

    if q:
        usuario = Usuario.query.filter(
            (Usuario.dni == q) | (Usuario.nombre.ilike(f"%{q}%"))
        ).first()

        if usuario:
            q = usuario.dni

        movs = Movimiento.query.filter(
            Movimiento.usuario_dni.ilike(f"%{q}%")
        ).order_by(Movimiento.fecha.desc()).all()

        # Enriquecer con datos del equipo
        icms = {m.icm for m in movs}
        equipos_map = {e.icm: e for e in Equipo.query.filter(Equipo.icm.in_(icms)).all()}

        movimientos = [(m, equipos_map.get(m.icm)) for m in movs]

        stats = {
            "total":         len(movs),
            "retiradas":     sum(1 for m in movs if m.tipo == "retirada"),
            "averias":       sum(1 for m in movs if m.tipo in ("averia", "modificacion") and "averia" in (m.descripcion or "").lower()),
            "reacondicionados": sum(1 for m in movs if "reacondicionado" in (m.descripcion or "").lower()),
            "entradas":      sum(1 for m in movs if m.tipo == "entrada"),
        }

    # Lista de usuarios para autocompletar
    usuarios = Usuario.query.order_by(Usuario.nombre).all()

    return render_template("usuarios/historial.html",
                           q=q, usuario=usuario, movimientos=movimientos,
                           stats=stats, usuarios=usuarios)
