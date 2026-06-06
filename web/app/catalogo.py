from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from .models import db, CatalogoItem
from functools import wraps

bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")


def solo_gestor(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_gestor:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@login_required
@solo_gestor
def index():
    items = CatalogoItem.query.order_by(
        CatalogoItem.seccion, CatalogoItem.marca, CatalogoItem.modelo
    ).all()
    # Árbol seccion → [marcas] para los selects en cascada
    tree_marcas = {}
    for it in items:
        tree_marcas.setdefault(it.seccion, set()).add(it.marca)
    tree_marcas = {s: sorted(ms) for s, ms in sorted(tree_marcas.items())}
    return render_template("admin/catalogo.html",
                           items=items, total=len(items),
                           tree_marcas=tree_marcas)


# ── Secciones ─────────────────────────────────────────────────────────────────

@bp.route("/seccion/add", methods=["POST"])
@login_required
@solo_gestor
def add_seccion():
    seccion = (request.get_json().get("seccion") or "").strip().upper()
    if not seccion:
        return jsonify({"ok": False, "error": "Nombre de sección vacío"})
    # Ya existe si hay algún item con esa sección
    if CatalogoItem.query.filter_by(seccion=seccion).first():
        return jsonify({"ok": False, "error": "La sección ya existe"})
    # Creamos un placeholder para que la sección aparezca aunque no tenga marcas todavía
    # (se borra si el usuario no añade nada; mejor: guardamos sección vacía con marca/modelo vacíos)
    # En su lugar guardamos la sección como "pendiente" con un item placeholder que el
    # usuario reemplazará cuando añada una marca. Mejor solución: tabla separada de secciones.
    # Por simplicidad, solo devolvemos ok y dejamos que el usuario añada una marca inmediatamente.
    return jsonify({"ok": True, "seccion": seccion})


@bp.route("/seccion/del", methods=["POST"])
@login_required
@solo_gestor
def del_seccion():
    seccion = (request.get_json().get("seccion") or "").strip().upper()
    if not seccion:
        return jsonify({"ok": False, "error": "Sección no indicada"})
    count = CatalogoItem.query.filter_by(seccion=seccion).delete()
    db.session.commit()
    return jsonify({"ok": True, "borrados": count})


# ── Marcas ────────────────────────────────────────────────────────────────────

@bp.route("/marca/add", methods=["POST"])
@login_required
@solo_gestor
def add_marca():
    data    = request.get_json()
    seccion = (data.get("seccion") or "").strip().upper()
    marca   = (data.get("marca")   or "").strip().upper()
    if not seccion or not marca:
        return jsonify({"ok": False, "error": "Sección y marca obligatorias"})
    if CatalogoItem.query.filter_by(seccion=seccion, marca=marca).first():
        return jsonify({"ok": False, "error": "La marca ya existe en esa sección"})
    return jsonify({"ok": True, "seccion": seccion, "marca": marca})


@bp.route("/marca/del", methods=["POST"])
@login_required
@solo_gestor
def del_marca():
    data    = request.get_json()
    seccion = (data.get("seccion") or "").strip().upper()
    marca   = (data.get("marca")   or "").strip().upper()
    count = CatalogoItem.query.filter_by(seccion=seccion, marca=marca).delete()
    db.session.commit()
    return jsonify({"ok": True, "borrados": count})


# ── Modelos ───────────────────────────────────────────────────────────────────

@bp.route("/modelo/add", methods=["POST"])
@login_required
@solo_gestor
def add_modelo():
    data    = request.get_json()
    seccion = (data.get("seccion") or "").strip().upper()
    marca   = (data.get("marca")   or "").strip().upper()
    modelo  = (data.get("modelo")  or "").strip()
    if not seccion or not marca or not modelo:
        return jsonify({"ok": False, "error": "Sección, marca y modelo son obligatorios"})
    if CatalogoItem.query.filter_by(seccion=seccion, marca=marca, modelo=modelo).first():
        return jsonify({"ok": False, "error": "El modelo ya existe"})
    item = CatalogoItem(seccion=seccion, marca=marca, modelo=modelo)
    db.session.add(item)
    db.session.commit()
    return jsonify({"ok": True, "id": item.id, "modelo": item.modelo})


@bp.route("/modelo/del/<int:mid>", methods=["POST"])
@login_required
@solo_gestor
def del_modelo(mid):
    item = CatalogoItem.query.get_or_404(mid)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


# ── API pública (usada por los selects de Registrar) ─────────────────────────

@bp.route("/api/tree")
@login_required
def api_tree():
    """Árbol completo para el frontend de gestión."""
    items = CatalogoItem.query.order_by(
        CatalogoItem.seccion, CatalogoItem.marca, CatalogoItem.modelo
    ).all()
    tree = {}
    for it in items:
        tree.setdefault(it.seccion, {}).setdefault(it.marca, []).append(
            {"id": it.id, "modelo": it.modelo}
        )
    return jsonify(tree)
