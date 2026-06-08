from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from .models import db, Equipo, Movimiento

bp = Blueprint("inventario", __name__, url_prefix="/inventario")


@bp.route("/")
@login_required
def lista():
    q      = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    seccion= request.args.get("seccion", "")
    page   = request.args.get("page", 1, type=int)

    query = Equipo.query
    # Los equipos en "ubicacion desconocida" tienen su propio dashboard
    # (/desaparecidos/) y no deben mezclarse con el stock general.
    query = query.filter(
        db.or_(Equipo.ubicacion.is_(None), Equipo.ubicacion != "Ubicacion desconocida")
    )
    if q:
        query = query.filter(
            Equipo.icm.ilike(f"%{q}%") |
            Equipo.sn.ilike(f"%{q}%") |
            Equipo.modelo.ilike(f"%{q}%") |
            Equipo.marca.ilike(f"%{q}%")
        )
    if estado:
        query = query.filter_by(estado=estado)
    if seccion:
        query = query.filter_by(seccion=seccion)

    equipos = query.order_by(Equipo.fecha_entrada.desc()).paginate(page=page, per_page=50)
    secciones = db.session.query(Equipo.seccion).distinct().filter(
        Equipo.seccion.isnot(None)).all()

    return render_template("inventario/lista.html",
                           equipos=equipos, q=q, estado=estado,
                           seccion=seccion, secciones=[s[0] for s in secciones])


@bp.route("/averias")
@login_required
def averia():
    """Vista filtrada de equipos en avería."""
    return redirect(url_for("inventario.lista", estado="averia"))


@bp.route("/editar", methods=["POST"])
@login_required
def editar():
    from flask_login import current_user
    from .models import Movimiento
    from datetime import datetime
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"})
    data = request.get_json()
    icm  = data.get("icm", "").strip().upper()
    eq   = Equipo.query.filter_by(icm=icm).first()
    if not eq:
        return jsonify({"ok": False, "error": "ICM no encontrado"})
    cambios = []
    for campo, val in [("marca", data.get("marca")), ("modelo", data.get("modelo")),
                       ("seccion", data.get("seccion")), ("sn", data.get("sn")),
                       ("garantia_fin", data.get("garantia")),
                       ("ubicacion", data.get("ubicacion")), ("notas", data.get("notas"))]:
        nuevo = (val or "").strip() or None
        if getattr(eq, campo) != nuevo:
            cambios.append(campo)
            setattr(eq, campo, nuevo)
    if cambios:
        mov = Movimiento(icm=icm, tipo="modificacion",
                         usuario_dni=current_user.dni,
                         descripcion="Editado: " + ", ".join(cambios),
                         pc=request.remote_addr)
        db.session.add(mov)
        db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<icm>")
@login_required
def detalle(icm):
    from .exproveedores import es_exproveedor
    equipo   = Equipo.query.filter_by(icm=icm.upper()).first_or_404()
    historial= Movimiento.query.filter_by(icm=icm.upper()).order_by(
        Movimiento.fecha.desc()).limit(50).all()
    exproveedor = es_exproveedor(equipo.marca or "", equipo.modelo or "")
    return render_template("inventario/detalle.html",
                           equipo=equipo, historial=historial,
                           exproveedor=exproveedor)
