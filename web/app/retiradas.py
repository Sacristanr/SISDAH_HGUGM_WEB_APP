from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import db, Equipo, Movimiento, Usuario, Telefono, ApWifi, TipoRetirada, MovimientoRed

bp = Blueprint("retiradas", __name__, url_prefix="/retiradas")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _tipos_activos():
    """Devuelve los tipos de retirada activos; crea los del sistema si no existen."""
    if TipoRetirada.query.count() == 0:
        defaults = [
            TipoRetirada(nombre="Hardware", descripcion="Equipos con ICM de la CM",
                         icono="bi-pc-display", panel_clave="hardware",
                         activo=True, orden=0, sistema=True),
            TipoRetirada(nombre="Teléfonos", descripcion="Teléfonos Cisco IP",
                         icono="bi-telephone", panel_clave="telefono",
                         activo=True, orden=1, sistema=True),
            TipoRetirada(nombre="AP WiFi", descripcion="Puntos de acceso inalámbrico",
                         icono="bi-wifi", panel_clave="ap_wifi",
                         activo=True, orden=2, sistema=True),
        ]
        for d in defaults:
            db.session.add(d)
        db.session.commit()
    return TipoRetirada.query.filter_by(activo=True).order_by(TipoRetirada.orden).all()


# ── Vistas ───────────────────────────────────────────────────────────────────

@bp.route("/")
@login_required
def form():
    tipos = _tipos_activos()
    return render_template("retiradas/form.html", tipos=tipos)


# ── API Hardware (ICM) ────────────────────────────────────────────────────────

@bp.route("/buscar_icm")
@login_required
def buscar_icm():
    icm = request.args.get("icm", "").strip().upper()
    equipo = Equipo.query.filter_by(icm=icm).first()
    if not equipo:
        return jsonify({"ok": False, "error": "ICM no encontrado en el inventario"})
    if equipo.estado == "retirado":
        return jsonify({"ok": False, "error": "Este equipo ya está retirado"})
    if equipo.estado == "reservado":
        return jsonify({"ok": False, "error": "Equipo bloqueado. Requiere contraseña de gestor.",
                        "bloqueado": True})
    return jsonify({"ok": True, "equipo": equipo.to_dict()})


@bp.route("/cambiar_estado", methods=["POST"])
@login_required
def cambiar_estado():
    data   = request.get_json()
    icm    = data.get("icm", "").strip().upper()
    estado = data.get("estado", "").strip()
    motivo = data.get("motivo", "").strip() or f"Estado cambiado a {estado}"

    ESTADOS_VALIDOS = {"en stock", "averia", "reservado", "papelera", "retirado", "reacondicionado"}
    if estado not in ESTADOS_VALIDOS:
        return jsonify({"ok": False, "error": "Estado no valido"})

    # Técnicos solo pueden registrar avería, reparación o reacondicionado
    ESTADOS_TECNICO = {"averia", "en stock", "reacondicionado"}
    if not current_user.es_gestor and estado not in ESTADOS_TECNICO:
        return jsonify({"ok": False, "error": "Sin permisos para ese estado"})

    eq = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": f"ICM '{icm}' no encontrado"})

    estado_anterior = eq.estado
    eq.estado = estado

    mov = Movimiento(
        icm=icm, tipo="modificacion",
        usuario_dni=current_user.dni,
        descripcion=f"{estado_anterior} -> {estado}: {motivo}",
        pc=request.remote_addr
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True, "estado": estado})


@bp.route("/confirmar", methods=["POST"])
@login_required
def confirmar():
    data = request.get_json()
    icm     = data.get("icm", "").strip().upper()
    dni     = data.get("dni", "").strip().upper()
    ticket  = data.get("ticket", "").strip().upper()
    icm_ver = data.get("icm_verificacion", "").strip().upper()

    if icm != icm_ver:
        return jsonify({"ok": False, "error": "El ICM de verificación no coincide"})

    equipo = Equipo.query.filter_by(icm=icm).first()
    if not equipo:
        return jsonify({"ok": False, "error": "ICM no encontrado"})
    if equipo.estado == "retirado":
        return jsonify({"ok": False, "error": "Ya retirado"})

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    equipo.estado        = "retirado"
    equipo.retirado_por  = dni
    equipo.codigo_ticket = ticket
    equipo.fecha_retiro  = fecha_hoy

    mov = Movimiento(icm=icm, tipo="retirada",
                     usuario_dni=current_user.dni,
                     descripcion=f"Retirada por {dni}. Ticket: {ticket}",
                     pc=request.remote_addr)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True, "icm": icm, "fecha": fecha_hoy})


# ── API Red: Teléfonos y AP WiFi ──────────────────────────────────────────────

@bp.route("/buscar_red")
@login_required
def buscar_red():
    tipo = request.args.get("tipo", "")   # 'telefono' | 'ap_wifi'
    ns   = request.args.get("ns",  "").strip()
    mac  = request.args.get("mac", "").strip()

    if not ns and not mac:
        return jsonify({"ok": False, "error": "Introduce al menos el SN o la MAC"})

    if tipo == "telefono":
        equipo = None
        if ns:
            equipo = Telefono.query.filter(Telefono.ns.ilike(ns)).first()
        if not equipo and mac:
            equipo = Telefono.query.filter(Telefono.mac.ilike(mac)).first()
    elif tipo == "ap_wifi":
        equipo = None
        if ns:
            equipo = ApWifi.query.filter(ApWifi.ns.ilike(ns)).first()
        if not equipo and mac:
            equipo = ApWifi.query.filter(ApWifi.mac.ilike(mac)).first()
    else:
        return jsonify({"ok": False, "error": "Tipo de dispositivo no válido"})

    if not equipo:
        return jsonify({"ok": False, "error": "Dispositivo no encontrado con ese SN o MAC"})
    if equipo.estado == "retirado":
        return jsonify({"ok": False, "error": "Este dispositivo ya está retirado"})

    return jsonify({"ok": True, "equipo": equipo.to_dict()})


@bp.route("/confirmar_red", methods=["POST"])
@login_required
def confirmar_red():
    data       = request.get_json()
    tipo       = data.get("tipo")          # 'telefono' | 'ap_wifi'
    equipo_id  = data.get("id")
    ns         = data.get("ns",        "").strip()
    mac        = data.get("mac",       "").strip()
    ubicacion  = data.get("ubicacion", "").strip()
    ticket     = data.get("ticket",    "").strip().upper()
    dni        = data.get("dni",       "").strip().upper()

    if not ticket or not ubicacion:
        return jsonify({"ok": False, "error": "Ticket y ubicación son obligatorios"})

    if tipo == "telefono":
        equipo = Telefono.query.get(equipo_id)
        label  = f"Extensión {equipo.extension}" if equipo else "Teléfono"
    elif tipo == "ap_wifi":
        equipo = ApWifi.query.get(equipo_id)
        label  = f"AP {equipo.nombre}" if equipo else "AP WiFi"
    else:
        return jsonify({"ok": False, "error": "Tipo no válido"})

    if not equipo:
        return jsonify({"ok": False, "error": "Dispositivo no encontrado"})
    if equipo.estado == "retirado":
        return jsonify({"ok": False, "error": "Ya retirado"})

    equipo.estado = "retirado"

    mov = MovimientoRed(
        tipo_equipo     = tipo,
        equipo_id       = equipo.id,
        ns              = ns or equipo.ns,
        mac             = mac or equipo.mac,
        ubicacion_salida= ubicacion,
        ticket          = ticket,
        tecnico_dni     = dni,
        usuario_id      = current_user.id,
        accion          = "retirada",
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({"ok": True, "label": label})


# ── Admin: gestión de TipoRetirada ───────────────────────────────────────────

@bp.route("/admin/tipos")
@login_required
def admin_tipos():
    if not current_user.es_admin:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    tipos = TipoRetirada.query.order_by(TipoRetirada.orden).all()
    return render_template("admin/tipos_retirada.html", tipos=tipos)


@bp.route("/admin/tipos/guardar", methods=["POST"])
@login_required
def admin_tipos_guardar():
    if not current_user.es_admin:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json()
    tid  = data.get("id")
    t    = TipoRetirada.query.get(tid) if tid else TipoRetirada()
    if not tid:
        db.session.add(t)
    t.nombre      = data.get("nombre", "").strip()
    t.descripcion = data.get("descripcion", "").strip()
    t.icono       = data.get("icono", "bi-box-arrow-right").strip()
    t.panel_clave = data.get("panel_clave", "custom").strip()
    t.activo      = data.get("activo", True)
    t.orden       = int(data.get("orden", 99))
    if not t.nombre:
        return jsonify({"ok": False, "error": "El nombre es obligatorio"})
    db.session.commit()
    return jsonify({"ok": True, "id": t.id})


@bp.route("/admin/tipos/eliminar/<int:tid>", methods=["POST"])
@login_required
def admin_tipos_eliminar(tid):
    if not current_user.es_admin:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    t = TipoRetirada.query.get_or_404(tid)
    if t.sistema:
        return jsonify({"ok": False, "error": "No se puede eliminar un tipo del sistema"})
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})
