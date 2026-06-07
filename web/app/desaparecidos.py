from flask import Blueprint, render_template
from flask_login import login_required
from .models import db, Equipo, Movimiento

bp = Blueprint("desaparecidos", __name__, url_prefix="/desaparecidos")


@bp.route("/")
@login_required
def panel():
    equipos = Equipo.query.filter(
        Equipo.ubicacion == "Ubicacion desconocida"
    ).order_by(Equipo.icm).all()

    # Para cada equipo, buscamos el movimiento de revisión que lo marcó
    # como "ubicacion desconocida" — de ahí sacamos la fecha de la revisión
    # en la que desapareció.
    icms = [e.icm for e in equipos]
    movimientos = {}
    if icms:
        movs = (Movimiento.query
                .filter(Movimiento.icm.in_(icms))
                .filter(Movimiento.descripcion.ilike("%ubicacion desconocida%"))
                .order_by(Movimiento.fecha.desc())
                .all())
        for m in movs:
            # nos quedamos con el más reciente por icm
            if m.icm not in movimientos:
                movimientos[m.icm] = m

    filas = [(eq, movimientos.get(eq.icm)) for eq in equipos]

    return render_template("desaparecidos/panel.html",
                           filas=filas, total=len(equipos))
