from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, ConfigApp
from functools import wraps
from flask import abort
import socket, platform

bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")

def solo_dev(f):
    """Solo rol developer puede acceder a herramientas de sistema."""
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.es_dev: abort(403)
        return f(*a, **kw)
    return dec

# Alias para compatibilidad
solo_admin = solo_dev


@bp.route("/")
@login_required
@solo_admin
def panel():
    smtp_host   = ConfigApp.get("smtp_host", "")
    smtp_port   = ConfigApp.get("smtp_port", "587")
    smtp_user   = ConfigApp.get("smtp_user", "")
    smtp_dest   = ConfigApp.get("smtp_dest", "")
    dept_nombre = ConfigApp.get("dept_nombre", "Departamento de Informática")
    dept_email  = ConfigApp.get("dept_email", "")
    sync_url    = ConfigApp.get("sync_url", "https://vm-pro-stock.hgugm.hggm.es")

    info = {
        "hostname": socket.gethostname(),
        "ip":       socket.gethostbyname(socket.gethostname()),
        "os":       platform.system() + " " + platform.release(),
        "python":   platform.python_version(),
    }

    return render_template("configuracion/panel.html",
                           smtp_host=smtp_host, smtp_port=smtp_port,
                           smtp_user=smtp_user, smtp_dest=smtp_dest,
                           dept_nombre=dept_nombre, dept_email=dept_email,
                           sync_url=sync_url, info=info)


# Claves de configuración permitidas (whitelist explícita)
_CLAVES_PERMITIDAS = {
    "smtp_host", "smtp_port", "smtp_user", "smtp_password",
    "smtp_dest", "dept_nombre", "dept_email", "sync_url",
}

@bp.route("/guardar", methods=["POST"])
@login_required
@solo_admin
def guardar():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "Datos inválidos"}), 400
    rechazadas = [k for k in data if k not in _CLAVES_PERMITIDAS]
    if rechazadas:
        return jsonify({"ok": False, "error": f"Claves no permitidas: {rechazadas}"}), 400
    for clave, valor in data.items():
        ConfigApp.set(clave, str(valor)[:500])  # limitar longitud
    return jsonify({"ok": True})
