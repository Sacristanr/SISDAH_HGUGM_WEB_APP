from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import db, Solicitud, Equipo

bp = Blueprint("solicitudes", __name__, url_prefix="/solicitudes")


@bp.route("/")
@login_required
def lista():
    if current_user.es_gestor:
        pendientes = Solicitud.query.filter_by(estado="pendiente").order_by(
            Solicitud.fecha_solicitud.desc()).all()
        resueltas  = Solicitud.query.filter(
            Solicitud.estado != "pendiente").order_by(
            Solicitud.fecha_solicitud.desc()).limit(50).all()
    else:
        pendientes = Solicitud.query.filter_by(
            solicitante_dni=current_user.dni, estado="pendiente").order_by(
            Solicitud.fecha_solicitud.desc()).all()
        resueltas  = Solicitud.query.filter(
            Solicitud.solicitante_dni == current_user.dni,
            Solicitud.estado != "pendiente").order_by(
            Solicitud.fecha_solicitud.desc()).limit(30).all()
    return render_template("solicitudes/lista.html",
                           pendientes=pendientes, resueltas=resueltas)


@bp.route("/crear", methods=["POST"])
@login_required
def crear():
    data = request.get_json()
    tipo = data.get("tipo")
    if tipo not in ("stock", "reserva"):
        return jsonify({"ok": False, "error": "Tipo inválido"})

    s = Solicitud(
        tipo               = tipo,
        solicitante_dni    = current_user.dni,
        solicitante_nombre = current_user.nombre,
    )

    if tipo == "stock":
        s.tipo_equipo = (data.get("tipo_equipo") or "").strip()
        s.descripcion = (data.get("descripcion") or "").strip()
        ticket_pre    = data.get("ticket_prefijo", "INC")
        ticket_num    = (data.get("ticket_num") or "").strip()
        s.ticket      = (ticket_pre + ticket_num) if ticket_num else None
        if not s.tipo_equipo or not s.descripcion:
            return jsonify({"ok": False, "error": "Indica el tipo de equipo y la descripción"})

    elif tipo == "reserva":
        icm = (data.get("icm") or "").strip().upper()
        if not icm:
            return jsonify({"ok": False, "error": "Indica el ICM del equipo"})
        eq = Equipo.query.filter_by(icm=icm).first()
        if not eq:
            return jsonify({"ok": False, "error": f"ICM '{icm}' no encontrado"})
        s.icm           = icm
        s.justificacion = (data.get("justificacion") or "").strip()
        ticket_pre      = data.get("ticket_prefijo", "INC")
        ticket_num      = (data.get("ticket_num") or "").strip()
        s.ticket        = (ticket_pre + ticket_num) if ticket_num else None
        if not s.justificacion:
            return jsonify({"ok": False, "error": "Indica la justificación de la reserva"})

    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True, "id": s.id})


@bp.route("/<int:sid>/resolver", methods=["POST"])
@login_required
def resolver(sid):
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data     = request.get_json()
    accion   = data.get("accion")   # "aprobar" | "rechazar"
    respuesta= (data.get("respuesta") or "").strip()
    if accion not in ("aprobar", "rechazar"):
        return jsonify({"ok": False, "error": "Acción inválida"})

    s = Solicitud.query.get_or_404(sid)
    s.estado          = "aprobada" if accion == "aprobar" else "rechazada"
    s.respuesta       = respuesta
    s.gestor_dni      = current_user.dni
    s.fecha_respuesta = datetime.utcnow()

    # Si se aprueba una solicitud de reserva → poner equipo en estado reservado
    if accion == "aprobar" and s.tipo == "reserva" and s.icm:
        eq = Equipo.query.filter_by(icm=s.icm).first()
        if eq and eq.estado not in ("retirado", "papelera"):
            eq.estado = "reservado"
            from .models import Movimiento
            mov = Movimiento(
                icm=s.icm, tipo="modificacion",
                usuario_dni=current_user.dni,
                descripcion=f"Reservado por solicitud #{s.id} — {s.solicitante_nombre}",
                pc=request.remote_addr
            )
            db.session.add(mov)

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:sid>/cancelar", methods=["POST"])
@login_required
def cancelar(sid):
    s = Solicitud.query.get_or_404(sid)
    if s.solicitante_dni != current_user.dni and not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    if s.estado != "pendiente":
        return jsonify({"ok": False, "error": "Solo se pueden cancelar solicitudes pendientes"})
    s.estado = "cancelada"
    db.session.commit()
    return jsonify({"ok": True})
