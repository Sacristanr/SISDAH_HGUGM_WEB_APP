# SISDAH — Manual de Mantenimiento
### Sistema de Archivo Hospitalario · HGUGM — Departamento de Informática
*Documento técnico para el personal de informática responsable del despliegue y mantenimiento de la aplicación.*

---

## 1. Arquitectura general

| Componente | Tecnología |
|---|---|
| Backend | Python 3 + Flask 3.1 |
| ORM / Base de datos | Flask-SQLAlchemy + Flask-Migrate (Alembic) |
| Base de datos | MySQL (producción) / SQLite (desarrollo, `USE_SQLITE=1`) |
| Autenticación | Flask-Login + Flask-WTF (CSRF) |
| Front-end | Plantillas Jinja2 + Bootstrap 5.3 + CSS propio (`static/css/sisdah.css`) |
| Etiquetas | `python-barcode` (Code128) + `qrcode` + `Pillow` |
| Exportaciones | `openpyxl` (Excel) |

La aplicación se organiza en **blueprints** (un archivo `.py` por módulo
funcional dentro de `app/`), cada uno con sus rutas, su lógica y su carpeta
de plantillas en `app/templates/<módulo>/`.

```
web/
├── run.py                  ← punto de entrada (arranca el servidor)
├── config.py               ← configuración (lee variables de entorno / .env)
├── requirements.txt        ← dependencias Python
├── app/
│   ├── __init__.py         ← create_app(): registro de blueprints, extensiones
│   ├── models.py           ← modelos de base de datos (SQLAlchemy)
│   ├── auth.py             ← login/logout, rate-limiting, sesiones
│   ├── dashboard.py        ← estadísticas del panel principal
│   ├── inventario.py       ← listado y ficha de equipos
│   ├── retiradas.py        ← retiradas y cambios de estado
│   ├── registrar.py        ← alta de equipos (manual / cámara / TEM)
│   ├── etiquetas.py        ← generación de etiquetas Code128 + QR
│   ├── desaparecidos.py    ← panel de equipos en "ubicación desconocida"
│   ├── admin.py            ← gestión de usuarios, panel de administración
│   ├── catalogo.py         ← catálogo de marcas/modelos/secciones (solo Admin N3)
│   ├── ...                 ← resto de módulos (telefonos, licencias, piezas…)
│   ├── sanitize.py         ← limpieza/validación de entradas (anti-inyección)
│   ├── static/css/sisdah.css ← estilos globales + responsive móvil
│   └── templates/          ← plantillas Jinja2, una carpeta por módulo
├── migrations/             ← migraciones de base de datos (Alembic)
└── *.bat                   ← scripts de instalación/arranque para Windows
```

---

## 2. Requisitos del entorno

- **Python 3.11+** (recomendado)
- **MySQL** en producción (o SQLite para pruebas locales)
- Paquetes listados en `requirements.txt`:
  ```
  flask, flask-login, flask-sqlalchemy, flask-migrate, flask-wtf,
  mysql-connector-python, werkzeug, python-dotenv, openpyxl, pillow
  ```
  Adicionalmente, para la generación de etiquetas (códigos de barras/QR):
  `python-barcode`, `qrcode` (se cargan de forma opcional — si faltan, la
  función de etiquetas se desactiva sin romper el resto de la app).

### Instalación

En Windows, los scripts `.bat` automatizan los pasos típicos:

| Script | Qué hace |
|---|---|
| `INSTALAR.bat` | Crea el entorno virtual e instala dependencias |
| `CAMBIAR_A_MYSQL.bat` | Cambia la configuración de SQLite a MySQL |
| `INICIAR_SERVIDOR.bat` | Arranca el servidor de desarrollo |
| `INSTALAR_SERVICIO.bat` | Instala SISDAH como servicio de Windows (arranque automático) |
| `ABRIR_FIREWALL.bat` | Crea la regla de firewall necesaria para acceso en red local |
| `DESPLIEGUE_HOSPITAL.bat` | Script de despliegue completo para el entorno del hospital |

Consulta también `DESPLIEGUE.md` para instrucciones detalladas paso a paso.

---

## 3. Configuración (`config.py` y `.env`)

La configuración se lee desde un archivo `.env` ubicado en `app/`. Variables
relevantes:

| Variable | Descripción | Por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firmar sesiones — **obligatoria en producción** | genera una temporal con aviso si falta |
| `USE_SQLITE` | `1` = usa SQLite (desarrollo), `0` = usa MySQL | `1` |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Credenciales de conexión a MySQL | — |
| `SESSION_SECURE` | `1` fuerza cookies de sesión solo por HTTPS | `0` |
| `PORT` | Puerto del servidor | `5000` |
| `FLASK_DEBUG` | `1` activa modo debug + autorecarga | `1` |

> ⚠️ **Importante**: en producción, configura siempre `SECRET_KEY` con un
> valor fijo y aleatorio en `.env`. Si no lo haces, la app genera una clave
> temporal en cada arranque y **todas las sesiones activas se invalidan al
> reiniciar el servidor**.

> ⚠️ Nunca uses el usuario `root` de MySQL para `DB_USER` — crea un usuario
> dedicado (`sisdah_app`) con permisos limitados a la base de datos `sisdah`.

### Seguridad de sesión (ya configurada)

```python
PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)  # cierre por inactividad
SESSION_COOKIE_HTTPONLY    = True   # JS no puede leer la cookie
SESSION_COOKIE_SAMESITE    = "Lax"  # mitigación CSRF básica
SESSION_COOKIE_SECURE      = solo si SESSION_SECURE=1
```

El valor de **15 minutos de inactividad** se eligió deliberadamente porque
el equipo del almacén es de uso compartido entre varios técnicos — si en
algún momento se necesita ajustar, está en `config.py`, línea
`PERMANENT_SESSION_LIFETIME`.

---

## 4. Arranque del servidor

### Desarrollo
```bash
python run.py
```
Arranca en `http://0.0.0.0:5000` (accesible desde toda la red local). El modo
debug (`FLASK_DEBUG=1`) recarga el servidor automáticamente al detectar
cambios en el código — **desactívalo en producción** (`FLASK_DEBUG=0`).

### Producción / servicio Windows
Usa `INSTALAR_SERVICIO.bat` para registrar SISDAH como servicio de Windows,
de forma que arranque solo con el sistema y se reinicie ante un fallo.

### Acceso desde otros dispositivos en red
1. Verifica que el servidor escucha en `0.0.0.0` (ya configurado en `run.py`).
2. Asegúrate de que la regla de firewall está activa — `ABRIR_FIREWALL.bat`
   crea la regla "SISDAH Web" (entrante, todos los perfiles, puerto 5000).
3. Comprueba que el adaptador de red está en categoría **Privada** (Windows),
   no Pública — si no, las reglas de firewall pueden no aplicarse igual.
4. Accede desde el móvil/otro PC con `http://<IP-del-servidor>:5000`.

> 💡 Si "no carga" desde otro dispositivo y todo lo anterior está bien,
> revisa primero que la IP escrita sea la correcta — es el fallo más común
> (typo en el último octeto de la IP).

---

## 5. Base de datos

### Modelos principales (`app/models.py`)
- `Equipo` — inventario principal (ICM, marca, modelo, estado, ubicación…)
- `Movimiento` — histórico de acciones sobre cada equipo (auditoría)
- `Usuario` — cuentas de acceso (técnico / gestor_n1 / gestor_n3 / developer)
- `ConfigApp` — configuración persistente clave-valor (p. ej. TEMs usados)
- Modelos específicos de cada módulo (teléfonos, licencias, piezas, etc.)

### Migraciones (Alembic / Flask-Migrate)
Cuando cambies el esquema de un modelo:
```bash
flask db migrate -m "descripción del cambio"
flask db upgrade
```
Las migraciones quedan versionadas en `migrations/` — **no las borres**, son
necesarias para llevar cualquier base de datos existente a la última versión
del esquema sin perder datos.

### Migración SQLite → MySQL
`CAMBIAR_A_MYSQL.bat` automatiza el cambio de configuración. El archivo
`sisdah_mysql.sql` contiene el volcado/esquema base para MySQL.

### Copias de seguridad
Programa copias periódicas de la base de datos MySQL (`mysqldump`). Si usas
SQLite en desarrollo, basta con copiar el archivo `.db` (ruta configurada en
`config.py`, por defecto `E:\SISDAH\data\sisdah.db`).

---

## 6. Roles de usuario y permisos

Definidos en `Usuario` (`app/models.py`):

| Rol | `es_gestor` | `es_admin` | `es_dev` | Acceso típico |
|---|:---:|:---:|:---:|---|
| `tecnico` | ❌ | ❌ | ❌ | Login solo con DNI; consulta de fichas, incidencias, reacondicionado |
| `gestor_n1` | ✅ | ❌ | ❌ | Gestión operativa (inventario, retiradas, registrar…) |
| `gestor_n3` | ✅ | ✅ | ❌ | Todo lo de N1 + administración (usuarios, catálogo, configuración) |
| `developer` | ✅ | ✅ | ✅ | Todo lo anterior + menú "Dev" (catálogo, configuración avanzada) |

Al añadir una nueva herramienta sensible, decide su nivel de acceso y
protégela tanto en la **plantilla** (ocultar el enlace del menú con
`{% if current_user.es_xxx %}`) como en el **backend** (decorador tipo
`@solo_gestor` / comprobación `current_user.es_admin` dentro de la ruta).
**La protección del backend es la que realmente importa** — ocultar un
enlace no impide acceder por URL directa.

---

## 7. Autenticación — puntos clave (`app/auth.py`)

- **Rate limiting** en memoria (`_login_attempts`): máximo 5 intentos en 5
  minutos, bloqueo de 15 minutos. Es por proceso — si despliegas con varios
  workers, cada uno lleva su propio contador (a tener en cuenta si se migra
  a un servidor con múltiples procesos).
- **`_safe_next()`**: valida el parámetro `next` para evitar *open redirect*
  (solo permite rutas internas que empiecen por `/`).
- **Flujo QR → login → ficha**: `etiquetas.py` genera el QR con la URL
  directa a `/inventario/<icm>`; si el usuario no está autenticado,
  Flask-Login le redirige al login con `?next=...` y, tras identificarse,
  vuelve automáticamente a la ficha.
- **Importante — no "atajar" sesiones activas en `POST`**: el método
  `login()` solo redirige automáticamente a quien ya está autenticado en
  peticiones `GET`. En `POST` siempre se procesa el formulario desde cero
  (cerrando antes cualquier sesión previa) — esto evita que una sesión
  "zombi" permita entrar sin validar credenciales. **No reintroduzcas** un
  `if current_user.is_authenticated: return redirect(...)` antes del
  bloque `if request.method == "POST":` sin tener esto en cuenta.

---

## 8. Generación de etiquetas (`app/etiquetas.py`)

- Etiquetas pensadas para impresora térmica **Epson LM-90** (cinta de hasta
  36mm), renderizadas a 300dpi con `Pillow`.
- Cada etiqueta combina **Code128** (lectura con escáner físico del almacén)
  y **QR** (lectura con móvil → ficha técnica autenticada).
- El QR codifica la URL `url_for('inventario.detalle', icm=..., _external=True)`;
  si no hay contexto de petición disponible (generación en lote fuera de
  request), cae a un payload JSON de respaldo.
- Si `barcode`/`qrcode`/`Pillow` no están instalados, `LABELS_OK = False` y
  las rutas devuelven un error controlado sin tumbar el resto de la app.

---

## 9. Escáner de cámara (registro de equipos en móvil)

`templates/registrar/_scripts_lote.html` implementa el escaneo de
ICM/QR/Code128 desde la cámara del móvil:

- **Chrome/Edge**: usa la API nativa `BarcodeDetector`.
- **Safari/iOS** (no soporta `BarcodeDetector`): se carga **ZXing**
  (`@zxing/library`, vía CDN bajo demanda) como librería de respaldo,
  capaz de decodificar los mismos formatos por software.
- Si quieres anclar la versión de ZXing o servirla localmente (en vez de
  CDN, p. ej. por políticas de red del hospital), cambia la URL en la
  función `_cargarZXing()`.

---

## 10. Front-end y responsive (móvil)

Todo el ajuste para pantallas pequeñas vive dentro de
`@media (max-width: 767px) { ... }` en `static/css/sisdah.css`. Bloques
relevantes (con comentarios explicativos en el propio archivo):

- **Menú colapsado** (`navbar-collapse`): los desplegables (`Teleco`, `Dev`)
  se muestran integrados y estáticos en vez de flotantes; el badge de
  "Solicitudes pendientes" y el pie del menú (buscador + botón Salir) se
  reorganizan a ancho completo.
- **Tarjetas del dashboard** (`admin-tile-card`): versión compacta, sin
  descripciones largas, con feedback de pulsación (`:active { scale(0.97) }`)
  y un indicador `›` de navegación.
- **Tablas → tarjetas apiladas** (`tabla-mobile-cards`): un script en
  `base.html` recorre automáticamente cualquier `<table class="table">`
  dentro de `<main>`, copia el texto de cada `<th>` como `data-label` en
  las celdas, y la CSS las convierte en tarjetas verticales — **no hace
  falta tocar cada plantilla** para que una tabla nueva se beneficie de
  esto; basta con que use la clase `table` estándar de Bootstrap dentro de
  un `<thead>`/`<tbody>` bien formado.

> 💡 Si añades una tabla nueva y no se convierte en tarjetas en móvil,
> revisa que tenga `<thead><tr><th>...</th></tr></thead>` — el script
> depende de esa estructura para generar las etiquetas automáticamente.

---

## 11. Tareas habituales de mantenimiento

| Tarea | Dónde / cómo |
|---|---|
| Crear/editar usuarios | `Admin → Usuarios del sistema` (gestores N3) |
| Cambiar el tiempo de cierre de sesión | `config.py` → `PERMANENT_SESSION_LIFETIME` |
| Añadir marcas/modelos/secciones al catálogo | `Admin → Dev → Catálogo` (solo Admin N3 / developer) |
| Revisar logs de acceso (auditoría de login) | Tabla `movimientos`, registros con `icm="AUTH"` (ver `_log_acceso` en `auth.py`) |
| Vaciar/echar un vistazo a la papelera | Módulo `papelera.py` / panel "Papelera" |
| Exportar datos a Excel | Módulo `exports.py` (usa `openpyxl`) |
| Comprobar equipos sin ubicación conocida | Panel "Desaparecidos" (`desaparecidos.py`) |

---

## 12. Buenas prácticas al modificar el código

1. **Sanitiza siempre la entrada de usuario** — usa las funciones de
   `app/sanitize.py` (`clean_dni`, `clean_text`, `clean_log_field`…) antes
   de guardar o mostrar datos que vengan de un formulario.
2. **CSRF**: todos los formularios deben incluir
   `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
   y las peticiones `fetch` deben usar el helper `_fetch()` de `base.html`,
   que añade automáticamente la cabecera `X-CSRFToken`.
3. **No mezcles lógica de permisos solo en el front-end** — protege siempre
   la ruta en el backend (`@login_required`, comprobaciones de rol).
4. **Usa migraciones** para cualquier cambio de esquema — nunca edites la
   base de datos de producción a mano sin una migración registrada.
5. **Cuidado con la codificación de texto** — el proyecto ha sufrido bugs de
   "doble UTF-8" (mojibake) al copiar/pegar texto con tildes desde ciertas
   fuentes. Si ves caracteres extraños tipo `Ã“` o `Ã¡`, sospecha de
   doble-codificación y verifica a nivel de bytes antes de "corregir" el
   texto visualmente (un `replace` de cadena puede no encontrar el patrón
   real).
6. **Prueba siempre en móvil real** los cambios de interfaz táctil — el
   emulador de DevTools no siempre refleja el comportamiento de Safari/iOS
   (p. ej. `BarcodeDetector` no existe ahí).

---

## 13. Diagnóstico de problemas frecuentes

| Síntoma | Causas probables / qué revisar |
|---|---|
| No se puede acceder desde el móvil | IP incorrecta (lo más común), firewall, perfil de red "Pública" en vez de "Privada", servidor no escuchando en `0.0.0.0` |
| Las sesiones se cierran al reiniciar el servidor | `SECRET_KEY` no configurada en `.env` (se genera una nueva en cada arranque) |
| El escáner de cámara no funciona en iPhone | Verifica que ZXing se carga correctamente (consola del navegador); puede deberse a falta de conexión a internet la primera vez (CDN) |
| Las etiquetas no se generan | Comprueba que `barcode`, `qrcode` y `Pillow` están instalados (`LABELS_OK`) |
| Texto con caracteres raros (`Ã±`, `Ã“`...) | Mojibake por doble codificación UTF-8 — inspeccionar a nivel de bytes |
| Un usuario "vuelve a entrar" tras caducar su sesión sin validar credenciales | Asegúrate de que `login()` no redirige automáticamente en `POST` para usuarios ya autenticados (ver sección 7) |

---

*HGUGM — Departamento de Informática · SISDAH — Documento de mantenimiento técnico*
