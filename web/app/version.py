# ══════════════════════════════════════════════════════════════
#  SISDAH — Control de versiones
#  Editar este fichero cada vez que se publique una nueva versión
# ══════════════════════════════════════════════════════════════

VERSION      = "3.1.0"
BUILD_DATE   = "2026-06-06"
RELEASE_NAME = "Seguridad & Dev Center"

# ── Historial de versiones ─────────────────────────────────────
# Tipos de cambio: "feature" | "fix" | "security" | "breaking" | "perf"
CHANGELOG = [
    {
        "version":  "3.1.0",
        "fecha":    "2026-06-06",
        "nombre":   "Seguridad & Dev Center",
        "cambios": [
            ("security", "Hardening completo: scrypt, rate limiting, CSRF, headers, CSP, session fixation"),
            ("security", "Lockout por cuenta: bloqueo automático tras 5 intentos fallidos"),
            ("security", "Política de contraseñas: mínimo 10 chars, mayús, minús, número, especial"),
            ("security", "Migración automática de hashes SHA-256 legacy a scrypt en el siguiente login"),
            ("security", "Auditoría completa de login/logout/cambios admin en tabla movimientos"),
            ("feature",  "Panel de Seguridad exclusivo DEV: logs, alertas, estado del sistema, usuarios bloqueados"),
            ("feature",  "Home DEV exclusivo: monitorización, métricas de seguridad, accesos rápidos"),
            ("feature",  "Errores 500 registrados automáticamente en BD con traceback"),
            ("feature",  "Páginas de error personalizadas (404, 500)"),
            ("feature",  "Sistema de Solicitudes: técnicos solicitan stock o reserva de activo"),
            ("feature",  "Técnicos pueden registrar averías y cambios de estado desde el detalle"),
            ("feature",  "Retirar piezas y complementos como técnico (fix botón modal data-*)"),
            ("feature",  "Piezas y complementos accesibles desde Retiradas como tile"),
            ("fix",      "NameError request en __init__.py (after_request sin import)"),
            ("fix",      "ImportError solo_gestor en retiradas.py"),
            ("fix",      "ICMs de auditoría AUTH/ADMIN no son clicables en historial"),
            ("fix",      "INICIAR_SERVIDOR.bat fallaba con caracteres Unicode en echo"),
            ("perf",     "Tipografía: tamaño base 15px, tablas más legibles, badges más visibles"),
            ("security", "Script migrar_seguridad.py: añade columnas BD sin pasar por Flask"),
        ],
    },
    {
        "version":  "3.0.0",
        "fecha":    "2026-05-01",
        "nombre":   "Lanzamiento Web",
        "cambios": [
            ("feature", "Versión web completa: Flask + MySQL + Bootstrap 5.3"),
            ("feature", "Inventario de hardware con ICM, historial de movimientos"),
            ("feature", "Registro y retirada de equipos con ticket INC/REQ"),
            ("feature", "Teléfonos IP Cisco y puntos de acceso WiFi"),
            ("feature", "Licencias de software"),
            ("feature", "Piezas de repuesto y complementos"),
            ("feature", "Estadísticas y exportación Excel/CSV"),
            ("feature", "Roles: técnico, gestor_n1, gestor_n3, developer"),
            ("feature", "Panel de administración de usuarios"),
            ("feature", "Fichas técnicas por modelo"),
            ("feature", "Etiquetas Code128 y QR"),
            ("feature", "Exproveedores: detección automática de marcas en desuso"),
        ],
    },
]
