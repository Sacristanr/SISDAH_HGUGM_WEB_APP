from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, Equipo, Movimiento
from datetime import datetime
from functools import wraps
from flask import abort

bp = Blueprint("papelera", __name__, url_prefix="/papelera")

def solo_admin(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.es_admin: abort(403)
        return f(*a, **kw)
    return dec


@bp.route("/")
@login_required
def lista():
    equipos   = Equipo.query.filter_by(estado="papelera").order_by(Equipo.fecha_retiro.desc()).all()
    retirados = Equipo.query.filter_by(estado="retirado").order_by(Equipo.fecha_retiro.desc()).all()
    return render_template("papelera/lista.html", equipos=equipos, retirados=retirados)


@bp.route("/restaurar/<icm>", methods=["POST"])
@login_required
@solo_admin
def restaurar(icm):
    eq = Equipo.query.filter_by(icm=icm.upper()).first_or_404()
    eq.estado = "en stock"
    eq.fecha_retiro = None
    mov = Movimiento(icm=icm.upper(), tipo="restauracion",
                     usuario_dni=current_user.dni,
                     descripcion="Restaurado desde papelera",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/eliminar/<icm>", methods=["POST"])
@login_required
@solo_admin
def eliminar(icm):
    eq = Equipo.query.filter_by(icm=icm.upper()).first_or_404()
    db.session.delete(eq)
    db.session.commit()
    return jsonify({"ok": True})
