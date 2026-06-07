"""
Utilidades de saneamiento de entradas de usuario.

La app ya está protegida frente a:
  - Inyección SQL  → SQLAlchemy ORM (consultas parametrizadas)
  - XSS en plantillas → Jinja2 escapa el HTML de salida automáticamente

Este módulo añade una capa extra de defensa en profundidad:
  - Elimina caracteres de control / invisibles (previene inyección en logs
    de auditoría: un DNI o descripción con saltos de línea podría falsear
    el registro de movimientos)
  - Normaliza espacios y aplica límites de longitud antes de tocar la BD
  - Valida formatos básicos (DNI/NIE español, email)
"""
import re
import unicodedata

# Caracteres de control Unicode (incluye \n, \r, \t, NUL, etc. salvo espacio normal)
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏‪-‮]")
_MULTI_SPACE   = re.compile(r"\s+")

_RE_DNI   = re.compile(r"^[XYZ]?\d{7,8}[A-Z]$")
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_text(value, max_len=255):
    """Limpia texto libre: quita caracteres de control, colapsa espacios,
    recorta a max_len. Seguro de usar en cualquier campo de texto."""
    if value is None:
        return ""
    value = unicodedata.normalize("NFC", str(value))
    value = _CONTROL_CHARS.sub("", value)
    value = _MULTI_SPACE.sub(" ", value).strip()
    if max_len:
        value = value[:max_len]
    return value


def clean_dni(value):
    """Normaliza un DNI/NIE: mayúsculas, sin espacios ni caracteres extraños."""
    value = clean_text(value, max_len=20).upper().replace(" ", "")
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def is_valid_dni(value):
    """Valida formato de DNI/NIE español (8 dígitos + letra, o X/Y/Z + 7-8 dígitos + letra)."""
    return bool(_RE_DNI.match(value))


def clean_email(value):
    """Normaliza un email: minúsculas, sin espacios."""
    value = clean_text(value, max_len=120).lower()
    return value


def is_valid_email(value):
    if not value:
        return True  # email es opcional en la mayoría de formularios
    return bool(_RE_EMAIL.match(value))


def clean_log_field(value, max_len=300):
    """Saneamiento estricto para campos que van a la auditoría (Movimiento).
    Evita que un valor con saltos de línea 'inyecte' líneas falsas en el log."""
    value = clean_text(value, max_len=max_len)
    return value.replace("\n", " ").replace("\r", " ")
