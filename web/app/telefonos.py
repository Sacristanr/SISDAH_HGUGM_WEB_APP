from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from .models import db, Telefono, Localizacion

bp = Blueprint("telefonos", __name__, url_prefix="/telefonos")


@bp.route("/")
@login_required
def lista():
    q = request.args.get("q", "")
    query = Telefono.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            Telefono.extension.ilike(like) |
            Telefono.ubicacion_libre.ilike(like) |
            Telefono.seccion.ilike(like) |
            Telefono.ns.ilike(like) |
            Telefono.mac.ilike(like) |
            Telefono.servicio.ilike(like)
        )
    telefonos = query.order_by(Telefono.extension).all()
    localizaciones = Localizacion.query.filter_by(activa=True).order_by(
        Localizacion.edificio, Localizacion.planta).all()
    return render_template("telefonos/lista.html",
                           telefonos=telefonos, q=q,
                           localizaciones=localizaciones)


@bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json()
    tid  = data.get("id")
    t = Telefono.query.get(tid) if tid else Telefono()
    if not tid:
        db.session.add(t)
    t.extension       = data.get("extension", "").strip() or None
    t.modelo          = data.get("modelo", "").strip()
    t.ns              = data.get("ns", "").strip()
    t.mac             = data.get("mac", "").strip()
    t.ip              = data.get("ip", "").strip()
    t.servicio        = data.get("servicio", "").strip()
    t.seccion         = data.get("seccion", "").strip()
    t.estado          = data.get("estado", "activo")
    t.notas           = data.get("notas", "").strip()
    # Ubicación estructurada vs libre
    loc_id = data.get("ubicacion_id")
    t.ubicacion_id    = int(loc_id) if loc_id else None
    t.ubicacion_libre = data.get("ubicacion_libre", "").strip() if not loc_id else ""
    if not tid:
        t.fecha_alta = date.today().isoformat()
    db.session.commit()
    return jsonify({"ok": True, "id": t.id})


@bp.route("/eliminar/<int:tid>", methods=["POST"])
@login_required
def eliminar(tid):
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    t = Telefono.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})


# ── API Localizaciones (compartida con AP WiFi) ────────────────
@bp.route("/api/localizaciones")
@login_required
def api_localizaciones():
    locs = Localizacion.query.filter_by(activa=True).order_by(
        Localizacion.edificio, Localizacion.planta).all()
    return jsonify([l.to_dict() for l in locs])


@bp.route("/localizaciones/guardar", methods=["POST"])
@login_required
def guardar_localizacion():
    data = request.get_json()
    lid  = data.get("id")
    l = Localizacion.query.get(lid) if lid else Localizacion()
    if not lid:
        db.session.add(l)
    l.edificio = data.get("edificio", "").strip()
    l.planta   = data.get("planta", "").strip()
    l.zona     = data.get("zona", "").strip()
    l.activa   = data.get("activa", True)
    if not l.edificio or not l.planta:
        return jsonify({"ok": False, "error": "Edificio y planta son obligatorios"})
    db.session.commit()
    return jsonify({"ok": True, "loc": l.to_dict()})


@bp.route("/localizaciones/eliminar/<int:lid>", methods=["POST"])
@login_required
def eliminar_localizacion(lid):
    l = Localizacion.query.get_or_404(lid)
    db.session.delete(l)
    db.session.commit()
    return jsonify({"ok": True})
