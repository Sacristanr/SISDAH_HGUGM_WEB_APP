import os, secrets
from datetime import timedelta
from dotenv import load_dotenv

# Cargar .env desde la carpeta de la app
_base = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base, ".env"))

def _build_uri():
    if os.getenv("USE_SQLITE", "1") == "1":
        db_path = os.path.join(r"E:\SISDAH\data", "sisdah.db")
        return f"sqlite:///{db_path}"
    user = os.getenv("DB_USER", "sisdah_app")   # nunca root en producción
    pwd  = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "sisdah")
    if not pwd:
        import warnings
        warnings.warn("SISDAH: DB_PASSWORD está vacío — inseguro en producción", stacklevel=2)
    return f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{name}"

def _get_secret_key():
    key = os.getenv("SECRET_KEY", "")
    if not key or key == "sisdah-hgugm-secret-2026":
        import warnings
        warnings.warn(
            "SISDAH: SECRET_KEY no configurada — generando clave temporal. "
            "Las sesiones no sobrevivirán un reinicio. Configura SECRET_KEY en .env",
            stacklevel=2
        )
        return secrets.token_hex(32)
    return key

class Config:
    SECRET_KEY = _get_secret_key()
    SQLALCHEMY_DATABASE_URI = _build_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Sesión segura ────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME   = timedelta(minutes=30)  # 30 min inactividad
    SESSION_COOKIE_HTTPONLY      = True    # JS no puede leer la cookie
    SESSION_COOKIE_SAMESITE      = "Lax"  # protección CSRF básica
    SESSION_COOKIE_SECURE        = os.getenv("SESSION_SECURE", "0") == "1"
    SESSION_COOKIE_NAME          = "sisdah_session"

    # ── CSRF ────────────────────────────────────────────────────
    WTF_CSRF_TIME_LIMIT          = 3600   # tokens CSRF válidos 1 hora

ROL_TECNICO  = "tecnico"
ROL_N1       = "gestor_n1"
ROL_N3       = "gestor_n3"
ROL_DEV      = "developer"
ROLES_VALIDOS  = {ROL_TECNICO, ROL_N1, ROL_N3, ROL_DEV}
ROLES_GESTOR   = {ROL_N1, ROL_N3, ROL_DEV}
ROLES_ADMIN    = {ROL_N3, ROL_DEV}

# DNI de emergencia — configurable desde .env
EMERGENCY_DNI  = os.getenv("EMERGENCY_DNI", "54421076V")
EMERGENCY_HASH = "1b79fcbf1d7303e73d48fe5be6496629b8ec1a6e98608a5ebe84017764bba0a0"

# Complejidad mínima de contraseña
MIN_PASSWORD_LEN = 10
