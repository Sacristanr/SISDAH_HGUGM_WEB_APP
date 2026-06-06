from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from .models import db, ApWifi, Localizacion

bp = Blueprint("ap_wifi", __name__, url_prefix="/ap-wifi")


@bp.route("/")
@login_required
def lista():
    q = request.args.get("q", "")
    query = ApWifi.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            ApWifi.nombre.ilike(like) |
            ApWifi.ns.ilike(like) |
            ApWifi.mac.ilike(like) |
            ApWifi.ip.ilike(like) |
            ApWifi.servicio.ilike(like) |
            ApWifi.ubicacion_libre.ilike(like)
        )
    aps = query.order_by(ApWifi.nombre).all()
    localizaciones = Localizacion.query.filter_by(activa=True).order_by(
        Localizacion.edificio, Localizacion.planta).all()
    return render_template("ap_wifi/lista.html", aps=aps, q=q,
                           localizaciones=localizaciones)


@bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json()
    aid  = data.get("id")
    a = ApWifi.query.get(aid) if aid else ApWifi()
    if not aid:
        db.session.add(a)
    a.nombre   = data.get("nombre", "").strip()
    a.ns       = data.get("ns", "").strip()
    a.mac      = data.get("mac", "").strip()
    a.ip       = data.get("ip", "").strip()
    a.modelo   = data.get("modelo", "").strip()
    a.servicio = data.get("servicio", "").strip()
    a.estado   = data.get("estado", "activo")
    a.notas    = data.get("notas", "").strip()
    loc_id = data.get("ubicacion_id")
    a.ubicacion_id    = int(loc_id) if loc_id else None
    a.ubicacion_libre = data.get("ubicacion_libre", "").strip() if not loc_id else ""
    if not aid:
        a.fecha_alta = date.today().isoformat()
    db.session.commit()
    return jsonify({"ok": True, "id": a.id})


@bp.route("/eliminar/<int:aid>", methods=["POST"])
@login_required
def eliminar(aid):
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    a = ApWifi.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"ok": True})
