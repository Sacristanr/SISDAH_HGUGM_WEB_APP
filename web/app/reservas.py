from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, Reserva, Equipo
from datetime import datetime

bp = Blueprint("reservas", __name__, url_prefix="/reservas")


@bp.route("/")
@login_required
def lista():
    reservas = Reserva.query.filter_by(activa=True).order_by(Reserva.fecha_inicio.desc()).all()
    return render_template("reservas/lista.html", reservas=reservas)


@bp.route("/crear", methods=["POST"])
@login_required
def crear():
    data = request.get_json()
    icm  = data.get("icm", "").strip().upper()
    eq   = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": "ICM no encontrado"})
    r = Reserva(icm=icm, reservado_por=data.get("reservado_por", current_user.dni),
                motivo=data.get("motivo", ""), fecha_fin=data.get("fecha_fin", ""))
    eq.estado = "reservado"
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/liberar/<int:rid>", methods=["POST"])
@login_required
def liberar(rid):
    r = Reserva.query.get_or_404(rid)
    r.activa = False
    eq = Equipo.query.filter_by(icm=r.icm).first()
    if eq and eq.estado == "reservado":
        eq.estado = "en stock"
    db.session.commit()
    return jsonify({"ok": True})
