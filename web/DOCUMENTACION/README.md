# SISDAH — Sistema de Archivo Hospitalario HGUGM

Sistema web de gestión de inventario TI para el **Departamento de Informática del Hospital General Universitario Gregorio Marañón (HGUGM)**.

Desarrollado internamente por el equipo de informática del hospital.

---

## Descripción

SISDAH permite gestionar de forma centralizada todo el equipamiento tecnológico del hospital: ordenadores, teléfonos IP, puntos de acceso WiFi, licencias de software, piezas de repuesto y complementos.

## Funcionalidades principales

- **Inventario de hardware** — alta, baja y seguimiento de equipos con código ICM
- **Retiradas** — registro de salidas de equipos a planta con código de ticket INC/REQ
- **Teléfonos IP** — gestión de extensiones Cisco con MAC, IP y ubicación
- **Puntos de acceso WiFi** — inventario de APs con estado y localización
- **Piezas y complementos** — stock de repuestos y accesorios
- **Licencias de software** — control de claves, caducidades y unidades
- **Sistema de solicitudes** — técnicos solicitan reservas o material; gestores aprueban
- **Historial de movimientos** — trazabilidad completa por equipo
- **Estadísticas** — métricas de uso, retiradas y averías
- **Etiquetas** — generación de códigos de barras Code128 y QR
- **Panel de seguridad** — auditoría de accesos y monitorización (rol developer)

## Roles de usuario

| Rol | Permisos |
|---|---|
| `tecnico` | Consultar inventario, registrar averías, solicitar material |
| `gestor_n1` | Gestión completa de inventario y retiradas |
| `gestor_n3` | Gestión + administración de usuarios |
| `developer` | Acceso total + panel de seguridad y monitorización |

## Stack tecnológico

- **Backend:** Python 3.12 + Flask 3.1 + SQLAlchemy
- **Base de datos:** MySQL (XAMPP en local)
- **Frontend:** Bootstrap 5.3 + Bootstrap Icons
- **Autenticación:** Flask-Login + Flask-WTF (CSRF)
- **Despliegue:** Python portable + scripts `.bat` para Windows

## Requisitos

- Windows 10/11
- Python 3.12 portable (carpeta `python/` junto a `web/`)
- MySQL / XAMPP con base de datos `sisdah`

## Instalación

```
1. Copiar la carpeta completa al equipo destino
2. Ejecutar: web\INSTALAR.bat
3. Configurar: web\.env  (credenciales de BD y SECRET_KEY)
4. Ejecutar migración: python migrar_seguridad.py
5. Arrancar: web\INICIAR_SERVIDOR.bat
```

Acceder en el navegador: `http://localhost:5000`

## Configuración (.env)

Copiar `.env.example` como `.env` y rellenar:

```env
SECRET_KEY=<clave aleatoria de 32 bytes>
DB_HOST=localhost
DB_USER=sisdah_app
DB_PASSWORD=<contraseña>
DB_NAME=sisdah
FLASK_DEBUG=0
```

## Estructura del proyecto

```
web/
├── app/
│   ├── templates/       # Plantillas Jinja2
│   ├── static/          # CSS, imágenes
│   ├── models.py        # Modelos SQLAlchemy
│   ├── auth.py          # Autenticación y seguridad
│   ├── version.py       # Control de versiones
│   └── *.py             # Blueprints por módulo
├── config.py
├── run.py
├── requirements.txt
├── sisdah_mysql.sql     # Esquema de base de datos
└── INSTALAR.bat
```

## Seguridad

- Contraseñas cifradas con **scrypt** (werkzeug)
- **Rate limiting** por IP: 5 intentos → bloqueo 15 min
- **Lockout** por cuenta tras fallos repetidos
- Headers de seguridad: CSP, X-Frame-Options, HSTS
- Protección CSRF en todos los formularios
- Sesión deslizante con timeout de 30 minutos
- Auditoría completa de accesos y cambios de administración

---

HGUGM — Departamento de Informática · Madrid
