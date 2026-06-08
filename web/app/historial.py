from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from .models import db, Movimiento, Equipo

bp = Blueprint("historial", __name__, url_prefix="/historial")


@bp.route("/")
@login_required
def lista():
    q    = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")
    page = request.args.get("page", 1, type=int)

    query = Movimiento.query

    # Los técnicos solo deben ver movimientos de equipos (entradas, retiradas,
    # cambios de estado, restauraciones...). Las entradas de auditoría —
    # intentos de acceso (login), errores del sistema y acciones de
    # administración— quedan reservadas a gestores/administradores.
    if not current_user.es_gestor:
        query = query.filter(
            ~Movimiento.tipo.in_(("acceso", "error")),
            ~Movimiento.icm.in_(("AUTH", "ADMIN", "ERROR")),
        )
        # Si alguien intenta forzar el filtro por tipo de auditoría vía URL,
        # lo ignoramos para que no se cuele nada.
        if tipo in ("acceso", "error"):
            tipo = ""

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
