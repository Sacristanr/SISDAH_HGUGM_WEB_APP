from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib, re

db = SQLAlchemy()

# ── Política de contraseñas ──────────────────────────────────────────────────
_PASS_MIN_LEN    = 10
_PASS_RE_UPPER   = re.compile(r'[A-Z]')
_PASS_RE_LOWER   = re.compile(r'[a-z]')
_PASS_RE_DIGIT   = re.compile(r'\d')
_PASS_RE_SPECIAL = re.compile(r'[^A-Za-z0-9]')

def validar_password(plain: str) -> tuple[bool, str]:
    """Devuelve (ok, mensaje). Aplica política sanitaria mínima."""
    if len(plain) < _PASS_MIN_LEN:
        return False, f"Mínimo {_PASS_MIN_LEN} caracteres"
    if not _PASS_RE_UPPER.search(plain):
        return False, "Debe incluir al menos una mayúscula"
    if not _PASS_RE_LOWER.search(plain):
        return False, "Debe incluir al menos una minúscula"
    if not _PASS_RE_DIGIT.search(plain):
        return False, "Debe incluir al menos un número"
    if not _PASS_RE_SPECIAL.search(plain):
        return False, "Debe incluir al menos un carácter especial (!@#…)"
    return True, ""


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id            = db.Column(db.Integer, primary_key=True)
    dni           = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    rol           = db.Column(db.String(20), nullable=False, default="tecnico")
    activo        = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(256), nullable=True)  # ampliado para bcrypt
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta   = db.Column(db.DateTime, nullable=True)

    def set_password(self, plain):
        """Hash seguro con PBKDF2-SHA256 (werkzeug)."""
        self.password_hash = generate_password_hash(plain)  # scrypt por defecto (werkzeug ≥ 2.3)

    def check_password(self, plain):
        """Verifica contraseña. Migra hashes SHA-256 legacy automáticamente."""
        if not self.password_hash:
            return False
        # Hash legacy: hex de 64 chars (SHA-256 sin sal)
        if len(self.password_hash) == 64 and all(c in '0123456789abcdef'
                                                   for c in self.password_hash):
            if self.password_hash == hashlib.sha256(plain.encode()).hexdigest():
                # Migrar a hash seguro en el mismo login
                self.set_password(plain)
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return True
            return False
        return check_password_hash(self.password_hash, plain)

    @property
    def es_gestor(self):
        return self.rol in ("gestor_n1", "gestor_n3", "developer")

    @property
    def es_admin(self):
        return self.rol in ("gestor_n3", "developer")

    @property
    def es_dev(self):
        return self.rol == "developer"


class Equipo(db.Model):
    __tablename__ = "stock"
    id             = db.Column(db.Integer, primary_key=True)
    icm            = db.Column(db.String(50), unique=True, nullable=False, index=True)
    marca          = db.Column(db.String(60))
    modelo         = db.Column(db.String(100))
    seccion        = db.Column(db.String(80), index=True)
    estado         = db.Column(db.String(20), default="en stock", index=True)
    sn             = db.Column(db.String(100), index=True)
    fecha_entrada  = db.Column(db.String(20))
    fecha_retiro   = db.Column(db.String(20))
    retirado_por   = db.Column(db.String(50))
    codigo_ticket  = db.Column(db.String(30))
    garantia_fin   = db.Column(db.String(20))
    numero_pedido  = db.Column(db.String(50))
    ubicacion      = db.Column(db.String(100))
    notas          = db.Column(db.Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Movimiento(db.Model):
    __tablename__ = "movimientos"
    id           = db.Column(db.Integer, primary_key=True)
    icm          = db.Column(db.String(50), nullable=False, index=True)
    tipo         = db.Column(db.String(30), nullable=False)
    usuario_dni  = db.Column(db.String(20))
    descripcion  = db.Column(db.Text)
    fecha        = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    pc           = db.Column(db.String(60))


class Localizacion(db.Model):
    """Catálogo de localizaciones físicas del hospital."""
    __tablename__ = "localizaciones"
    id          = db.Column(db.Integer, primary_key=True)
    edificio    = db.Column(db.String(80), nullable=False)
    planta      = db.Column(db.String(40), nullable=False)
    zona        = db.Column(db.String(80))          # descripción libre opcional
    activa      = db.Column(db.Boolean, default=True)

    def label(self):
        parts = [self.edificio, self.planta]
        if self.zona:
            parts.append(self.zona)
        return " · ".join(parts)

    def to_dict(self):
        return {
            "id": self.id,
            "edificio": self.edificio,
            "planta": self.planta,
            "zona": self.zona or "",
            "label": self.label(),
        }


class Telefono(db.Model):
    __tablename__ = "telefonos"
    id              = db.Column(db.Integer, primary_key=True)
    extension       = db.Column(db.String(20), unique=True, nullable=True, index=True)
    modelo          = db.Column(db.String(60))
    ns              = db.Column(db.String(100), index=True)   # Número de serie
    mac             = db.Column(db.String(20))
    ip              = db.Column(db.String(20))
    servicio        = db.Column(db.String(100))               # servicio/departamento
    # Ubicación estructurada
    ubicacion_id    = db.Column(db.Integer, db.ForeignKey("localizaciones.id"), nullable=True)
    ubicacion_libre = db.Column(db.String(150))               # texto libre de respaldo
    ubicacion_rel   = db.relationship("Localizacion", foreign_keys=[ubicacion_id])
    # Campos heredados
    seccion         = db.Column(db.String(80))
    estado          = db.Column(db.String(20), default="activo")
    notas           = db.Column(db.Text)
    fecha_alta      = db.Column(db.String(20))

    @property
    def ubicacion(self):
        if self.ubicacion_rel:
            return self.ubicacion_rel.label()
        return self.ubicacion_libre or ""

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d["ubicacion"] = self.ubicacion
        return d


class ApWifi(db.Model):
    """Puntos de acceso WiFi del hospital."""
    __tablename__ = "ap_wifi"
    id              = db.Column(db.Integer, primary_key=True)
    nombre          = db.Column(db.String(80))                # nombre/referencia del AP
    ns              = db.Column(db.String(100), index=True)   # Número de serie
    mac             = db.Column(db.String(20), index=True)
    ip              = db.Column(db.String(20))
    modelo          = db.Column(db.String(80))
    servicio        = db.Column(db.String(100))
    # Ubicación estructurada
    ubicacion_id    = db.Column(db.Integer, db.ForeignKey("localizaciones.id"), nullable=True)
    ubicacion_libre = db.Column(db.String(150))
    ubicacion_rel   = db.relationship("Localizacion", foreign_keys=[ubicacion_id])
    estado          = db.Column(db.String(20), default="activo")
    notas           = db.Column(db.Text)
    fecha_alta      = db.Column(db.String(20))

    @property
    def ubicacion(self):
        if self.ubicacion_rel:
            return self.ubicacion_rel.label()
        return self.ubicacion_libre or ""

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d["ubicacion"] = self.ubicacion
        return d


class CatalogoItem(db.Model):
    """Un modelo del catálogo: seccion + marca + modelo (nombre del modelo)."""
    __tablename__ = "catalogo"
    id      = db.Column(db.Integer, primary_key=True)
    seccion = db.Column(db.String(80),  nullable=False, index=True)
    marca   = db.Column(db.String(80),  nullable=False, index=True)
    modelo  = db.Column(db.String(120), nullable=False)
    __table_args__ = (
        db.UniqueConstraint("seccion", "marca", "modelo", name="uq_catalogo_smm"),
    )

    def to_dict(self):
        return {"id": self.id, "seccion": self.seccion,
                "marca": self.marca, "modelo": self.modelo}


class Licencia(db.Model):
    __tablename__ = "licencias"
    id           = db.Column(db.Integer, primary_key=True)
    software     = db.Column(db.String(100), nullable=False)
    clave        = db.Column(db.String(200))
    tipo         = db.Column(db.String(40))   # OEM, volumen, suscripcion
    cantidad     = db.Column(db.Integer, default=1)
    usadas       = db.Column(db.Integer, default=0)
    caducidad    = db.Column(db.String(20))
    proveedor    = db.Column(db.String(100))
    notas        = db.Column(db.Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Pieza(db.Model):
    __tablename__ = "piezas"
    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), nullable=False)
    referencia   = db.Column(db.String(60))
    cantidad     = db.Column(db.Integer, default=0)
    ubicacion    = db.Column(db.String(100))
    compatible   = db.Column(db.String(200))  # modelos compatibles
    notas        = db.Column(db.Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Complemento(db.Model):
    __tablename__ = "complementos"
    id           = db.Column(db.Integer, primary_key=True)
    tipo         = db.Column(db.String(40))   # teclado, raton, cable, monitor...
    marca        = db.Column(db.String(60))
    modelo       = db.Column(db.String(100))
    cantidad     = db.Column(db.Integer, default=0)
    estado       = db.Column(db.String(20), default="en stock")
    icm_asociado = db.Column(db.String(50))
    notas        = db.Column(db.Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Solicitud(db.Model):
    """Solicitudes de activos (stock o reserva) generadas por técnicos."""
    __tablename__ = "solicitudes"
    id                 = db.Column(db.Integer, primary_key=True)
    tipo               = db.Column(db.String(20), nullable=False)   # "stock" | "reserva"
    # Solicitud de stock (equipo que no existe en el inventario)
    tipo_equipo        = db.Column(db.String(100))   # "portátil", "teclado", etc.
    descripcion        = db.Column(db.Text)           # qué necesita exactamente
    ticket             = db.Column(db.String(30))     # INC12345678 / REQ12345678
    # Solicitud de reserva (equipo concreto ya en inventario)
    icm                = db.Column(db.String(50))
    justificacion      = db.Column(db.Text)
    # Estado y auditoría
    estado             = db.Column(db.String(20), default="pendiente", index=True)
    solicitante_dni    = db.Column(db.String(20), nullable=False)
    solicitante_nombre = db.Column(db.String(100))
    gestor_dni         = db.Column(db.String(20))
    respuesta          = db.Column(db.Text)
    fecha_solicitud    = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    fecha_respuesta    = db.Column(db.DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Reserva(db.Model):
    __tablename__ = "reservas"
    id           = db.Column(db.Integer, primary_key=True)
    icm          = db.Column(db.String(50), nullable=False, index=True)
    reservado_por= db.Column(db.String(50))
    motivo       = db.Column(db.Text)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin    = db.Column(db.String(20))
    activa       = db.Column(db.Boolean, default=True)


class TipoRetirada(db.Model):
    """Tipos de retirada configurables desde admin (Hardware, Teléfonos, AP WiFi…)."""
    __tablename__ = "tipos_retirada"
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(60), nullable=False)
    descripcion = db.Column(db.String(150))
    icono       = db.Column(db.String(50), default="bi-box-arrow-right")
    panel_clave = db.Column(db.String(30))   # 'hardware' | 'telefono' | 'ap_wifi' | custom
    activo      = db.Column(db.Boolean, default=True)
    orden       = db.Column(db.Integer, default=0)
    sistema     = db.Column(db.Boolean, default=False)  # True = no se puede borrar


class MovimientoRed(db.Model):
    """Log de retiradas de Teléfonos y AP WiFi."""
    __tablename__ = "movimientos_red"
    id              = db.Column(db.Integer, primary_key=True)
    tipo_equipo     = db.Column(db.String(20))   # 'telefono' | 'ap_wifi'
    equipo_id       = db.Column(db.Integer)
    ns              = db.Column(db.String(100))
    mac             = db.Column(db.String(20))
    ubicacion_salida= db.Column(db.String(200))
    ticket          = db.Column(db.String(30))
    tecnico_dni     = db.Column(db.String(20))
    usuario_id      = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    fecha           = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    accion          = db.Column(db.String(30), default="retirada")


class ConfigApp(db.Model):
    __tablename__ = "config_app"
    id    = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(60), unique=True, nullable=False)
    valor = db.Column(db.Text)

    @classmethod
    def get(cls, clave, default=""):
        r = cls.query.filter_by(clave=clave).first()
        return r.valor if r else default

    @classmethod
    def set(cls, clave, valor):
        r = cls.query.filter_by(clave=clave).first()
        if r:
            r.valor = valor
        else:
            db.session.add(cls(clave=clave, valor=valor))
        db.session.commit()
