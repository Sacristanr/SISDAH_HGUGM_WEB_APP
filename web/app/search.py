from flask import Blueprint, render_template, request
from flask_login import login_required
from .models import db, Equipo, Movimiento, Telefono, Licencia

bp = Blueprint("search", __name__, url_prefix="/buscar")


@bp.route("/")
@login_required
def buscar():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("search/resultados.html", q=q,
                               equipos=[], movimientos=[], telefonos=[], licencias=[])

    equipos = Equipo.query.filter(
        Equipo.icm.ilike(f"%{q}%") |
        Equipo.sn.ilike(f"%{q}%") |
        Equipo.modelo.ilike(f"%{q}%") |
        Equipo.marca.ilike(f"%{q}%") |
        Equipo.retirado_por.ilike(f"%{q}%")
    ).limit(30).all()

    movimientos = Movimiento.query.filter(
        Movimiento.icm.ilike(f"%{q}%") |
        Movimiento.usuario_dni.ilike(f"%{q}%") |
        Movimiento.descripcion.ilike(f"%{q}%")
    ).order_by(Movimiento.fecha.desc()).limit(15).all()

    telefonos = Telefono.query.filter(
        Telefono.extension.ilike(f"%{q}%") |
        Telefono.ubicacion.ilike(f"%{q}%") |
        Telefono.seccion.ilike(f"%{q}%")
    ).limit(10).all()

    licencias = Licencia.query.filter(
        Licencia.software.ilike(f"%{q}%")
    ).limit(10).all()

    return render_template("search/resultados.html", q=q,
                           equipos=equipos, movimientos=movimientos,
                           telefonos=telefonos, licencias=licencias)
