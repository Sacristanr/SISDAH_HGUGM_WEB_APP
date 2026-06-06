from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, ConfigApp
from .catalogo_data import get_secciones, get_marcas, get_modelos
import json

bp = Blueprint("exproveedores", __name__, url_prefix="/exproveedores")


def _get_lista():
    raw = ConfigApp.get("exproveedores", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def _save_lista(lista):
    ConfigApp.set("exproveedores", json.dumps(lista))


@bp.route("/")
@login_required
def panel():
    exproveedores = _get_lista()
    secciones = get_secciones()
    # Construir árbol para el JS del panel
    catalogo = {s: {m: get_modelos(s, m) for m in get_marcas(s)} for s in secciones}
    return render_template("exproveedores/panel.html",
                           exproveedores=exproveedores,
                           secciones=secciones,
                           catalogo_json=json.dumps(catalogo))


def es_exproveedor(marca: str, modelo: str = None) -> bool:
    """Comprueba si una marca o modelo concreto está en la lista de exproveedores."""
    if not marca:
        return False
    lista = _get_lista()
    for e in lista:
        if e["marca"].upper() == marca.upper():
            if e.get("modelo") is None:
                return True  # Toda la marca es exproveedor
            if modelo and e["modelo"].upper() == modelo.upper():
                return True  # Modelo concreto es exproveedor
    return False


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


@bp.route("/agregar", methods=["POST"])
@login_required
def agregar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"})
    data   = request.get_json()
    seccion = data.get("seccion", "").strip()
    marca   = data.get("marca", "").strip().upper()
    modelo  = data.get("modelo", "").strip()

    if not marca:
        return jsonify({"ok": False, "error": "Marca obligatoria"})

    lista = _get_lista()
    entrada = {"seccion": seccion, "marca": marca, "modelo": modelo or None}

    # Evitar duplicados
    if any(e["marca"] == marca and e.get("modelo") == (modelo or None) for e in lista):
        return jsonify({"ok": False, "error": "Ya esta en la lista"})

    lista.append(entrada)
    _save_lista(lista)
    return jsonify({"ok": True})


@bp.route("/eliminar", methods=["POST"])
@login_required
def eliminar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"})
    data   = request.get_json()
    marca  = data.get("marca", "").strip().upper()
    modelo = data.get("modelo", None)

    lista = _get_lista()
    lista = [e for e in lista
             if not (e["marca"] == marca and e.get("modelo") == modelo)]
    _save_lista(lista)
    return jsonify({"ok": True})
