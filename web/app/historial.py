from flask import Blueprint, render_template, request
from flask_login import login_required
from .models import db, Movimiento, Equipo

bp = Blueprint("historial", __name__, url_prefix="/historial")


@bp.route("/")
@login_required
def lista():
    q    = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")
    page = request.args.get("page", 1, type=int)

    query = Movimiento.query
    if q:
        query = query.filter(
            Movimiento.icm.ilike(f"%{q}%") |
            Movimiento.usuario_dni.ilike(f"%{q}%") |
            Movimiento.descripcion.ilike(f"%{q}%")
        )
    if tipo:
        query = query.filter_by(tipo=tipo)

    movimientos = query.order_by(Movimiento.fecha.desc()).paginate(page=page, per_page=50)
    return render_template("historial/lista.html",
                           movimientos=movimientos, q=q, tipo=tipo)
