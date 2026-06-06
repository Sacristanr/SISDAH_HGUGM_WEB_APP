from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db
from sqlalchemy import Column, Integer, String, Text
from . import db as _db
from datetime import datetime

bp = Blueprint("fichas", __name__, url_prefix="/fichas")


class FichaTecnica(_db.Model):
    __tablename__ = "fichas_tecnicas"
    id            = Column(Integer, primary_key=True)
    seccion       = Column(String(80), index=True)
    marca         = Column(String(60))
    modelo        = Column(String(100), nullable=False)
    procesador    = Column(String(100))
    ram           = Column(String(40))
    almacenamiento= Column(String(60))
    pantalla      = Column(String(60))
    so            = Column(String(80))
    bios_version  = Column(String(40))
    bios_pass     = Column(String(100))
    admin_user    = Column(String(60))
    admin_pass    = Column(String(100))
    drivers_url   = Column(Text)
    manual_url    = Column(Text)
    notas         = Column(Text)
    actualizado   = Column(String(20))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


@bp.route("/")
@login_required
def lista():
    secciones = db.session.query(FichaTecnica.seccion).distinct().filter(
        FichaTecnica.seccion.isnot(None)).order_by(FichaTecnica.seccion).all()
    seccion = request.args.get("seccion", "")
    q       = request.args.get("q", "")
    query   = FichaTecnica.query
    if seccion:
        query = query.filter_by(seccion=seccion)
    if q:
        query = query.filter(
            FichaTecnica.modelo.ilike(f"%{q}%") |
            FichaTecnica.marca.ilike(f"%{q}%")
        )
    fichas = query.order_by(FichaTecnica.seccion, FichaTecnica.marca, FichaTecnica.modelo).all()
    return render_template("fichas/lista.html", fichas=fichas,
                           secciones=[s[0] for s in secciones],
                           seccion=seccion, q=q)


@bp.route("/<int:fid>")
@login_required
def detalle(fid):
    ficha = FichaTecnica.query.get_or_404(fid)
    # Ocultar contraseñas a técnicos
    mostrar_pass = current_user.es_gestor
    return render_template("fichas/detalle.html", ficha=ficha, mostrar_pass=mostrar_pass)


@bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    if not current_user.es_gestor:
        return jsonify({"ok": False, "error": "Sin permisos"})
    data  = request.get_json()
    fid   = data.get("id")
    ficha = FichaTecnica.query.get(fid) if fid else FichaTecnica()
    if not fid:
        db.session.add(ficha)
    for campo in ["seccion","marca","modelo","procesador","ram","almacenamiento",
                  "pantalla","so","bios_version","bios_pass","admin_user","admin_pass",
                  "drivers_url","manual_url","notas"]:
        setattr(ficha, campo, data.get(campo, "").strip() or None)
    ficha.actualizado = datetime.now().strftime("%d/%m/%Y")
    db.session.commit()
    return jsonify({"ok": True, "id": ficha.id})


@bp.route("/eliminar/<int:fid>", methods=["POST"])
@login_required
def eliminar(fid):
    if not current_user.es_admin:
        return jsonify({"ok": False, "error": "Sin permisos"})
    db.session.delete(FichaTecnica.query.get_or_404(fid))
    db.session.commit()
    return jsonify({"ok": True})
