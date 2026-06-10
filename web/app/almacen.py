"""
SISDAH — Operaciones de almacén de campo (N2)

- Sustitución en un paso: retirar el equipo averiado y entregar el de
  stock con un solo ticket, en una sola operación.
- Stock mínimo por sección con alertas (evitar roturas de stock).
- Vista de trabajos por ticket: todo lo que se movió con un ticket.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from .models import db, Equipo, Movimiento, MovimientoRed, ConfigApp

bp = Blueprint("almacen", __name__, url_prefix="/almacen")

ESTADOS_DISPONIBLES = ("en stock", "reacondicionado")


# ─── Stock mínimo ─────────────────────────────────────────────────────────────

def _get_minimos() -> dict:
    try:
        return {k: int(v) for k, v in
                json.loads(ConfigApp.get("stock_minimos", "{}")).items()}
    except Exception:
        return {}


def stock_por_seccion() -> dict:
    """Unidades disponibles (en stock + reacondicionado) por sección."""
    from sqlalchemy import func
    rows = (db.session.query(Equipo.seccion, func.count(Equipo.id))
            .filter(Equipo.estado.in_(ESTADOS_DISPONIBLES))
            .group_by(Equipo.seccion).all())
    return {(s or "Sin sección"): c for s, c in rows}


def alertas_stock() -> list:
    """Secciones cuyo stock está por debajo del mínimo configurado."""
    minimos = _get_minimos()
    if not minimos:
        return []
    stock = stock_por_seccion()
    alertas = []
    for seccion, minimo in minimos.items():
        actual = stock.get(seccion, 0)
        if actual < minimo:
            alertas.append({"seccion": seccion, "stock": actual, "minimo": minimo})
    alertas.sort(key=lambda a: a["stock"] - a["minimo"])
    return alertas


@bp.route("/stock")
@login_required
def stock():
    """Panel de control de stock con mínimos y alertas."""
    minimos = _get_minimos()
    stock   = stock_por_seccion()
    # Unión de todas las secciones conocidas
    secciones = sorted(set(stock) | set(minimos))
    filas = [{"seccion": s,
              "stock": stock.get(s, 0),
              "minimo": minimos.get(s, 0),
              "alerta": stock.get(s, 0) < minimos.get(s, 0)}
             for s in secciones]
    return render_template("almacen/stock.html", filas=filas,
                           es_gestor=current_user.es_gestor)


@bp.route("/api/stock-minimos", methods=["POST"])
@login_required
def guardar_minimos():
    """Guarda los umbrales de stock mínimo (solo gestores)."""
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"}), 403
    data = request.get_json() or {}
    minimos = {}
    for seccion, valor in (data.get("minimos") or {}).items():
        try:
            v = int(valor)
            if v > 0:
                minimos[seccion.strip()] = v
        except (TypeError, ValueError):
            continue
    ConfigApp.set("stock_minimos", json.dumps(minimos, ensure_ascii=False))
    return jsonify({"ok": True, "alertas": alertas_stock()})


# ─── Sustitución en un paso ───────────────────────────────────────────────────

@bp.route("/sustitucion")
@login_required
def sustitucion():
    return render_template("almacen/sustitucion.html")


@bp.route("/api/buscar-equipo")
@login_required
def buscar_equipo():
    """Busca un ICM y devuelve su ficha + si es válido como entrega o retirada."""
    icm = request.args.get("icm", "").strip().upper()
    if not icm:
        return jsonify({"ok": False, "error": "ICM vacío"})
    eq = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": True, "existe": False, "icm": icm})
    return jsonify({"ok": True, "existe": True, "equipo": eq.to_dict(),
                    "disponible": eq.estado in ESTADOS_DISPONIBLES})


@bp.route("/api/sustituir", methods=["POST"])
@login_required
def sustituir():
    """
    Operación atómica de sustitución:
      - El equipo ENTREGADO (de stock) pasa a 'retirado' con ticket y DNI.
      - El equipo AVERIADO vuelve al almacén como 'averia'.
        Si no estaba inventariado, se registra con los datos mínimos.
    """
    data = request.get_json() or {}
    icm_ent  = (data.get("icm_entregado") or "").strip().upper()
    icm_av   = (data.get("icm_averiado") or "").strip().upper()
    ticket   = (data.get("ticket") or "").strip().upper()
    dni      = (data.get("dni") or "").strip().upper()
    ubicacion= (data.get("ubicacion") or "").strip()
    sintoma  = (data.get("sintoma") or "").strip()

    if not icm_ent or not ticket:
        return jsonify({"ok": False, "error": "Equipo a entregar y ticket son obligatorios"})
    if icm_ent == icm_av:
        return jsonify({"ok": False, "error": "El equipo entregado y el averiado no pueden ser el mismo"})

    # ── Validar equipo a entregar ──
    ent = Equipo.query.filter_by(icm=icm_ent).first()
    if not ent:
        return jsonify({"ok": False, "error": f"'{icm_ent}' no está en el inventario"})
    if ent.estado not in ESTADOS_DISPONIBLES:
        return jsonify({"ok": False,
                        "error": f"'{icm_ent}' no está disponible (estado: {ent.estado})"})

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    # ── Entregar ──
    ent.estado        = "retirado"
    ent.retirado_por  = dni
    ent.codigo_ticket = ticket
    ent.fecha_retiro  = fecha_hoy
    if ubicacion:
        ent.ubicacion = ubicacion
    db.session.add(Movimiento(
        icm=icm_ent, tipo="sustitucion",
        usuario_dni=current_user.dni,
        descripcion=f"ENTREGADO en sustitución. Ticket: {ticket}. "
                    f"Sustituye a: {icm_av or 'equipo no inventariado'}. "
                    f"Ubicación: {ubicacion or '—'}",
        pc=request.remote_addr))

    # ── Recoger averiado ──
    averiado_creado = False
    if icm_av:
        av = Equipo.query.filter_by(icm=icm_av).first()
        if not av:
            # Equipo que nunca se inventarió: lo damos de alta como avería
            av = Equipo(icm=icm_av, estado="averia",
                        seccion=ent.seccion,           # misma familia que el sustituto
                        fecha_entrada=fecha_hoy,
                        ubicacion="Almacén",
                        notas=f"Alta automática por sustitución (ticket {ticket})")
            db.session.add(av)
            averiado_creado = True
        else:
            av.estado    = "averia"
            av.ubicacion = "Almacén"
        db.session.add(Movimiento(
            icm=icm_av, tipo="sustitucion",
            usuario_dni=current_user.dni,
            descripcion=f"RECOGIDO averiado. Ticket: {ticket}. "
                        f"Sustituido por: {icm_ent}. "
                        + (f"Síntoma: {sintoma}" if sintoma else ""),
            pc=request.remote_addr))

    db.session.commit()
    return jsonify({"ok": True, "ticket": ticket,
                    "entregado": icm_ent, "averiado": icm_av or None,
                    "averiado_creado": averiado_creado,
                    "alertas": alertas_stock()})


# ─── Trabajos por ticket ──────────────────────────────────────────────────────

@bp.route("/ticket")
@bp.route("/ticket/<codigo>")
@login_required
def ticket(codigo=None):
    """Todo lo que se movió con un ticket: equipos, teléfonos, APs."""
    resultado = None
    if codigo:
        codigo = codigo.strip().upper()
        equipos = Equipo.query.filter_by(codigo_ticket=codigo).all()
        movs = (Movimiento.query
                .filter(Movimiento.descripcion.ilike(f"%{codigo}%"))
                .order_by(Movimiento.fecha.desc()).limit(100).all())
        movs_red = (MovimientoRed.query.filter_by(ticket=codigo)
                    .order_by(MovimientoRed.id.desc()).all())
        resultado = {"codigo": codigo, "equipos": equipos,
                     "movimientos": movs, "movimientos_red": movs_red}
    return render_template("almacen/ticket.html", resultado=resultado)
