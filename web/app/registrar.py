import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import db, Equipo, Movimiento, Telefono, Localizacion
from .catalogo_data import get_secciones, get_marcas, get_modelos

bp = Blueprint("registrar", __name__, url_prefix="/registrar")

try:
    from validators import validar_icm
except ImportError:
    def validar_icm(icm):
        icm = icm.strip().upper()
        if len(icm) < 3:
            return False, "Mínimo 3 caracteres"
        return True, ""


@bp.route("/", methods=["GET"])
@login_required
def form():
    return render_template("registrar/form.html", secciones=get_secciones())


@bp.route("/guardar_telefono", methods=["POST"])
@login_required
def guardar_telefono():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    ns  = data.get("ns", "").strip()
    mac = data.get("mac", "").strip()
    if not ns and not mac:
        return jsonify({"ok": False, "error": "NS o MAC son obligatorios"})

    t = Telefono()
    t.modelo          = data.get("modelo", "").strip() or None
    t.ns              = ns or None
    t.mac             = mac or None
    t.ip              = data.get("ip", "").strip() or None
    t.extension       = None          # se puede asignar luego desde la lista
    t.estado          = "activo"
    t.fecha_alta      = datetime.today().strftime("%Y-%m-%d")

    loc_id = data.get("ubicacion_id")
    t.ubicacion_id    = int(loc_id) if loc_id else None
    t.ubicacion_libre = data.get("ubicacion_libre", "").strip() if not loc_id else ""

    try:
        db.session.add(t)
        db.session.commit()
        return jsonify({"ok": True, "id": t.id,
                        "label": f"{t.modelo or 'Teléfono'} · {t.ns or t.mac or ''}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"DB error: {str(e)}"}), 500


@bp.route("/api/marcas")
@login_required
def api_marcas():
    seccion = request.args.get("seccion", "")
    return jsonify(get_marcas(seccion))


@bp.route("/api/modelos")
@login_required
def api_modelos():
    seccion = request.args.get("seccion", "")
    marca   = request.args.get("marca", "")
    return jsonify(get_modelos(seccion, marca))


@bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    items            = data.get("items", [])
    pedido           = data.get("numero_pedido", "").strip()
    marca            = data.get("marca", "").strip().upper()
    modelo           = data.get("modelo", "").strip().upper()
    seccion          = data.get("seccion", "").strip().upper()
    ubicacion_global = data.get("ubicacion", "").strip()   # viene del modo individual
    fecha_hoy        = datetime.now().strftime("%d/%m/%Y")

    guardados, duplicados, errores = [], [], []

    for item in items:
        icm = item.get("icm", "").strip().upper()
        sn  = item.get("sn", "").strip()

        ok, msg = validar_icm(icm)
        if not ok:
            errores.append({"icm": icm, "error": msg})
            continue

        if Equipo.query.filter_by(icm=icm).first():
            duplicados.append(icm)
            continue

        # lote: ubicacion viene dentro del item; individual: viene a nivel raíz del body
        ubicacion = (item.get("ubicacion") or ubicacion_global or "").strip() or None

        equipo = Equipo(
            icm=icm, marca=marca, modelo=modelo, seccion=seccion,
            estado="en stock", sn=sn or None,
            fecha_entrada=fecha_hoy, numero_pedido=pedido or None,
            ubicacion=ubicacion,
        )
        db.session.add(equipo)

        mov = Movimiento(icm=icm, tipo="entrada",
                         usuario_dni=current_user.dni,
                         descripcion=f"Registro inicial. Pedido: {pedido or '-'}",
                         pc=request.remote_addr)
        db.session.add(mov)
        guardados.append(icm)

    db.session.commit()
    return jsonify({"ok": True, "guardados": guardados,
                    "duplicados": duplicados, "errores": errores})
