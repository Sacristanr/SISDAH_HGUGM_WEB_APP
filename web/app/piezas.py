from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import db, Pieza, Complemento

bp = Blueprint("piezas", __name__, url_prefix="/piezas")


@bp.route("/")
@login_required
def lista():
    piezas = Pieza.query.order_by(Pieza.nombre).all()
    complementos = Complemento.query.order_by(Complemento.tipo, Complemento.marca).all()
    return render_template("piezas/lista.html", piezas=piezas, complementos=complementos)


@bp.route("/guardar_pieza", methods=["POST"])
@login_required
def guardar_pieza():
    data = request.get_json()
    pid  = data.get("id")
    p    = Pieza.query.get(pid) if pid else Pieza()
    if not pid: db.session.add(p)
    p.nombre     = data.get("nombre", "").strip()
    p.referencia = data.get("referencia", "").strip()
    p.cantidad   = int(data.get("cantidad", 0))
    p.ubicacion  = data.get("ubicacion", "").strip()
    p.compatible = data.get("compatible", "").strip()
    p.notas      = data.get("notas", "").strip()
    db.session.commit()
    return jsonify({"ok": True, "id": p.id})


@bp.route("/guardar_complemento", methods=["POST"])
@login_required
def guardar_complemento():
    data = request.get_json()
    cid  = data.get("id")
    c    = Complemento.query.get(cid) if cid else Complemento()
    if not cid: db.session.add(c)
    c.tipo         = data.get("tipo", "").strip()
    c.marca        = data.get("marca", "").strip()
    c.modelo       = data.get("modelo", "").strip()
    c.cantidad     = int(data.get("cantidad", 0))
    c.estado       = data.get("estado", "en stock")
    c.icm_asociado = data.get("icm_asociado", "").strip() or None
    c.notas        = data.get("notas", "").strip()
    db.session.commit()
    return jsonify({"ok": True, "id": c.id})


@bp.route("/eliminar_pieza/<int:pid>", methods=["POST"])
@login_required
def eliminar_pieza(pid):
    db.session.delete(Pieza.query.get_or_404(pid))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/eliminar_complemento/<int:cid>", methods=["POST"])
@login_required
def eliminar_complemento(cid):
    db.session.delete(Complemento.query.get_or_404(cid))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/retirar_complemento/<int:cid>", methods=["POST"])
@login_required
def retirar_complemento(cid):
    c    = Complemento.query.get_or_404(cid)
    data = request.get_json()
    cant = int(data.get("cantidad", 1))
    if cant <= 0:
        return jsonify({"ok": False, "error": "Cantidad inválida"})
    if cant > c.cantidad:
        return jsonify({"ok": False, "error": f"Solo hay {c.cantidad} en stock"})
    c.cantidad -= cant
    if c.cantidad == 0:
        c.estado = "asignado"
    # Registrar en notas quién lo retiró
    entrada = f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Retirado x{cant} por {current_user.nombre} ({current_user.dni})"
    if data.get("destino"):
        entrada += f" — Destino: {data['destino']}"
    if data.get("motivo"):
        entrada += f" — {data['motivo']}"
    c.notas = ((c.notas or "") + "\n" + entrada).strip()
    db.session.commit()
    return jsonify({"ok": True, "stock_restante": c.cantidad})


@bp.route("/retirar_pieza/<int:pid>", methods=["POST"])
@login_required
def retirar_pieza(pid):
    p    = Pieza.query.get_or_404(pid)
    data = request.get_json()
    cant = int(data.get("cantidad", 1))
    if cant <= 0:
        return jsonify({"ok": False, "error": "Cantidad inválida"})
    if cant > p.cantidad:
        return jsonify({"ok": False, "error": f"Solo hay {p.cantidad} en stock"})
    p.cantidad -= cant
    entrada = f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Retirado x{cant} por {current_user.nombre} ({current_user.dni})"
    if data.get("destino"):
        entrada += f" — Destino: {data['destino']}"
    if data.get("motivo"):
        entrada += f" — {data['motivo']}"
    p.notas = ((p.notas or "") + "\n" + entrada).strip()
    db.session.commit()
    return jsonify({"ok": True, "stock_restante": p.cantidad})
