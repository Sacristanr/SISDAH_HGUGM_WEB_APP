from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, Equipo, Movimiento
from sqlalchemy import distinct

bp = Blueprint("revision", __name__, url_prefix="/revision")


@bp.route("/")
@login_required
def panel():
    seccion = request.args.get("seccion", "")
    marca   = request.args.get("marca", "")
    modelo  = request.args.get("modelo", "")

    secciones = [s[0] for s in db.session.query(distinct(Equipo.seccion)).filter(
        Equipo.seccion.isnot(None)).order_by(Equipo.seccion).all()]
    marcas = [m[0] for m in db.session.query(distinct(Equipo.marca)).filter(
        Equipo.marca.isnot(None)).order_by(Equipo.marca).all()]
    modelos = []
    if marca:
        modelos = [m[0] for m in db.session.query(distinct(Equipo.modelo)).filter(
            Equipo.marca == marca, Equipo.modelo.isnot(None)).order_by(Equipo.modelo).all()]

    query = Equipo.query.filter(Equipo.estado.in_(
        ["en stock", "reservado", "averia", "reacondicionado", "ubicacion desconocida"]))
    if seccion: query = query.filter_by(seccion=seccion)
    if marca:   query = query.filter_by(marca=marca)
    if modelo:  query = query.filter_by(modelo=modelo)

    equipos = query.order_by(Equipo.seccion, Equipo.icm).all()

    return render_template("revision/panel.html",
                           equipos=equipos, secciones=secciones,
                           marcas=marcas, modelos=modelos,
                           seccion_sel=seccion, marca_sel=marca, modelo_sel=modelo,
                           total=len(equipos))


@bp.route("/verificar", methods=["POST"])
@login_required
def verificar():
    icm = request.get_json().get("icm", "").strip().upper()
    eq  = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": f"ICM '{icm}' no encontrado"})

    # Si estaba en ubicacion desconocida, restaurar a stock
    restaurado = False
    if eq.ubicacion == "Ubicacion desconocida" or eq.estado == "ubicacion desconocida":
        eq.estado    = "en stock"
        eq.ubicacion = None
        restaurado   = True
        db.session.commit()

    return jsonify({
        "ok":        True,
        "icm":       eq.icm,
        "marca":     eq.marca or "",
        "modelo":    eq.modelo or "",
        "seccion":   eq.seccion or "",
        "estado":    eq.estado,
        "sn":        eq.sn or "",
        "restaurado": restaurado,
    })


@bp.route("/cerrar", methods=["POST"])
@login_required
def cerrar():
    data        = request.get_json()
    verificados = data.get("verificados", [])
    no_escaneados = data.get("no_escaneados", [])
    mover_desconocidos = data.get("mover_desconocidos", False)

    # Registrar movimientos de los verificados
    for icm in verificados:
        db.session.add(Movimiento(
            icm=icm, tipo="revision",
            usuario_dni=current_user.dni,
            descripcion="Verificado en revision de inventario",
            pc=request.remote_addr
        ))

    movidos = []
    if mover_desconocidos and no_escaneados:
        for icm in no_escaneados:
            eq = Equipo.query.filter_by(icm=icm).first()
            if eq and eq.estado in ("en stock", "reservado", "reacondicionado"):
                eq.ubicacion = "Ubicacion desconocida"
                db.session.add(Movimiento(
                    icm=icm, tipo="revision",
                    usuario_dni=current_user.dni,
                    descripcion="No encontrado en revision — ubicacion desconocida",
                    pc=request.remote_addr
                ))
                movidos.append(icm)

    db.session.commit()
    return jsonify({
        "ok": True,
        "verificados":  len(verificados),
        "no_escaneados": len(no_escaneados),
        "movidos_desconocidos": len(movidos),
    })
