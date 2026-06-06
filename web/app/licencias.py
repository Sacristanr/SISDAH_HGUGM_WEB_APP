from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from .models import db, Licencia

bp = Blueprint("licencias", __name__, url_prefix="/licencias")


@bp.route("/")
@login_required
def lista():
    licencias = Licencia.query.order_by(Licencia.software).all()
    return render_template("licencias/lista.html", licencias=licencias)


@bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    data = request.get_json()
    lid  = data.get("id")
    l    = Licencia.query.get(lid) if lid else Licencia()
    if not lid: db.session.add(l)
    l.software  = data.get("software", "").strip()
    l.clave     = data.get("clave", "").strip()
    l.tipo      = data.get("tipo", "")
    l.cantidad  = int(data.get("cantidad", 1))
    l.usadas    = int(data.get("usadas", 0))
    l.caducidad = data.get("caducidad", "")
    l.proveedor = data.get("proveedor", "")
    l.notas     = data.get("notas", "")
    db.session.commit()
    return jsonify({"ok": True, "id": l.id})


@bp.route("/eliminar/<int:lid>", methods=["POST"])
@login_required
def eliminar(lid):
    db.session.delete(Licencia.query.get_or_404(lid))
    db.session.commit()
    return jsonify({"ok": True})
