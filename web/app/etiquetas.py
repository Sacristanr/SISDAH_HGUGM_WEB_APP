"""
Generador de etiquetas Code128 + QR para SISDAH
Produce PNG en memoria lista para imprimir o mostrar en web
"""
from flask import Blueprint, send_file, request, jsonify, render_template
from flask_login import login_required, current_user
from .models import db, Equipo, Movimiento, ConfigApp
from io import BytesIO
from datetime import datetime
import hashlib, os, json

bp = Blueprint("etiquetas", __name__, url_prefix="/etiquetas")

try:
    import barcode
    from barcode.writer import ImageWriter
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    LABELS_OK = True
except ImportError:
    LABELS_OK = False


# ─── Generación de ICM temporal único ────────────────────────────────────────
def _get_tem_usados():
    raw = ConfigApp.get("tem_usados", "[]")
    try:
        return set(json.loads(raw))
    except Exception:
        return set()


def _save_tem_usados(usados):
    ConfigApp.set("tem_usados", json.dumps(sorted(usados)))


def generar_tem_unico():
    """Genera un código TEM de 8 dígitos garantizado único."""
    usados  = _get_tem_usados()
    # También verificar contra BD
    en_bd   = {e.icm for e in Equipo.query.filter(Equipo.icm.like("TEM%")).all()}
    usados  = usados | en_bd

    import random
    for _ in range(10000):
        num = random.randint(10000000, 99999999)
        tem = f"TEM{num}"
        if tem not in usados:
            usados.add(tem)
            _save_tem_usados(usados)
            return tem
    raise ValueError("No se pudo generar un TEM único")


# ─── Generación de etiqueta para Epson LM-90 ─────────────────────────────────
# LM-90: cinta hasta 36mm ancho, impresión térmica, 180dpi
# Formato: horizontal, blanco/negro puro, sin rellenos de color
#
# Layout a 180dpi:
#   36mm × 90mm  →  255px × 638px  (vertical)
#   24mm × 88mm  →  170px × 622px  (cinta 24mm)
#
# Usamos 300dpi para mayor nitidez al escalar para pantalla:
#   36mm × 90mm  →  425px × 1063px
#
# Orientación: LANDSCAPE (girado 90°) para que el código de barras
# sea lo más largo posible en la dirección de la cinta.

def generar_etiqueta_png(icm: str, marca: str = "", modelo: str = "",
                          sn: str = "", seccion: str = "",
                          ancho_mm: int = 36) -> BytesIO:
    """
    Etiqueta optimizada para Epson LM-90.
    Blanco/negro puro, sin color (la cinta solo imprime en negro).
    Formato horizontal (landscape) para aprovechar la longitud de la cinta.
    """
    if not LABELS_OK:
        raise ImportError("Librerías de etiquetas no disponibles")

    DPI    = 300
    # Dimensiones reales a 300dpi
    # 36mm ancho × ~88mm largo  →  425 × 1040px
    # En landscape: H = ancho de cinta, W = longitud
    H = int(ancho_mm / 25.4 * DPI)   # altura = ancho de cinta (36mm)
    W = int(88      / 25.4 * DPI)    # longitud 88mm

    NEGRO  = (0, 0, 0)
    BLANCO = (255, 255, 255)
    GRIS   = (180, 180, 180)

    img  = Image.new("RGB", (W, H), BLANCO)
    draw = ImageDraw.Draw(img)

    # Fuentes — busca Arial, cae a default si no está
    def font(size):
        for nombre in ("arial.ttf", "Arial.ttf",
                       "C:/Windows/Fonts/arial.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(nombre, size)
            except Exception:
                pass
        return ImageFont.load_default()

    f_icm    = font(int(H * 0.18))   # ICM grande
    f_normal = font(int(H * 0.12))
    f_small  = font(int(H * 0.09))
    f_tiny   = font(int(H * 0.07))

    PAD = 4  # margen exterior

    # ── QR pequeño en esquina derecha ─────────────────────────────────────────
    # QR ocupa ~28% del ancho total — suficiente para leerlo con móvil
    qr_size = int(H * 0.80)
    qr_x    = W - qr_size - PAD
    qr_y    = (H - qr_size) // 2

    qr_data = json.dumps({
        "icm": icm, "marca": marca, "modelo": modelo,
        "sn": sn, "s": "SISDAH"
    }, ensure_ascii=False, separators=(',', ':'))
    qr = qrcode.QRCode(version=2, box_size=3, border=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    img.paste(qr_img, (qr_x, qr_y))

    # Separador fino antes del QR
    draw.line([(qr_x - 5, PAD), (qr_x - 5, H - PAD)], fill=GRIS, width=1)

    # ── Zona del Code128 ──────────────────────────────────────────────────────
    # El barcode ocupa ~75% del ancho y ~75% del alto → máxima escaneabilidad
    bar_zona_w = qr_x - 12         # ancho disponible para barcode + texto
    bar_h      = int(H * 0.72)     # alto del barcode (deja margen para texto)
    bar_y      = PAD + 2

    try:
        CODE    = barcode.get_barcode_class("code128")
        buf_bar = BytesIO()
        opts = {
            "module_width":  0.20,
            "module_height": bar_h / DPI * 25.4 * 0.90,
            "font_size":     0,        # SIN número bajo el barcode
            "text_distance": 1.0,
            "background":    "white",
            "foreground":    "black",
            "write_text":    False,    # El número lo ponemos nosotros más pequeño
            "quiet_zone":    2.5,
        }
        CODE(icm, writer=ImageWriter()).write(buf_bar, opts)
        buf_bar.seek(0)
        bar_src = Image.open(buf_bar).convert("RGB")
        bar_src = bar_src.resize((bar_zona_w, bar_h), Image.LANCZOS)
        img.paste(bar_src, (PAD, bar_y))
    except Exception:
        draw.text((PAD + 4, bar_y + 4), icm, font=f_normal, fill=NEGRO)

    # ── Texto debajo del barcode — todo pequeño ───────────────────────────────
    ty = bar_y + bar_h + 3

    # ICM — fuente mediana (no gigante)
    draw.text((PAD + 2, ty), icm, font=f_normal, fill=NEGRO)
    ty += f_normal.size + 1

    # Marca / Modelo en una línea compacta
    if marca or modelo:
        draw.text((PAD + 2, ty), f"{marca} {modelo}".strip(), font=f_small, fill=(50, 50, 50))
        ty += f_small.size + 1

    # S/N muy pequeño si hay espacio
    if sn and ty + f_tiny.size < H - 2:
        draw.text((PAD + 2, ty), f"SN:{sn}", font=f_tiny, fill=(100, 100, 100))

    # Pie derecho
    fecha = datetime.now().strftime("%d/%m/%Y")
    draw.text((PAD + 2, H - f_tiny.size - 2), f"HGUGM·{fecha}", font=f_tiny, fill=GRIS)

    # Borde exterior
    draw.rectangle([0, 0, W-1, H-1], outline=NEGRO, width=1)

    buf = BytesIO()
    img.save(buf, format="PNG", dpi=(DPI, DPI))
    buf.seek(0)
    return buf


# ─── Rutas Flask ──────────────────────────────────────────────────────────────
@bp.route("/generar")
@login_required
def generar():
    """GET /etiquetas/generar?icm=XXX&mm=36  → PNG de la etiqueta"""
    icm     = request.args.get("icm", "").strip().upper()
    marca   = request.args.get("marca", "")
    modelo  = request.args.get("modelo", "")
    sn      = request.args.get("sn", "")
    seccion = request.args.get("seccion", "")
    ancho   = int(request.args.get("mm", 36))

    if icm:
        eq = Equipo.query.filter_by(icm=icm).first()
        if eq:
            marca   = eq.marca or marca
            modelo  = eq.modelo or modelo
            sn      = eq.sn or sn
            seccion = eq.seccion or seccion

    if not icm:
        return jsonify({"error": "ICM requerido"}), 400

    if not LABELS_OK:
        return jsonify({"error": "Librerias de etiquetas no instaladas"}), 500

    try:
        buf = generar_etiqueta_png(icm, marca, modelo, sn, seccion, ancho_mm=ancho)
        return send_file(buf, mimetype="image/png",
                         download_name=f"etiqueta_{icm}.png",
                         as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/descargar")
@login_required
def descargar():
    """Igual que generar pero fuerza descarga del PNG."""
    icm     = request.args.get("icm", "").strip().upper()
    eq      = Equipo.query.filter_by(icm=icm).first()
    marca   = eq.marca if eq else ""
    modelo  = eq.modelo if eq else ""
    sn      = eq.sn if eq else ""
    seccion = eq.seccion if eq else ""

    if not icm or not LABELS_OK:
        return jsonify({"error": "ICM requerido o librerías no disponibles"}), 400

    try:
        buf = generar_etiqueta_png(icm, marca, modelo, sn, seccion)
        return send_file(buf, mimetype="image/png",
                         download_name=f"etiqueta_{icm}.png",
                         as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/tem/generar", methods=["POST"])
@login_required
def generar_tem():
    """Genera uno o varios TEM únicos con sus etiquetas."""
    import base64
    data    = request.get_json() or {}
    cantidad = min(int(data.get("cantidad", 1)), 200)   # máx 200 de golpe
    marca   = data.get("marca", "")
    modelo  = data.get("modelo", "")
    seccion = data.get("seccion", "")
    ancho   = int(data.get("mm", 36))
    sns     = data.get("sns", [])   # lista de S/N opcionales (uno por equipo)

    resultados = []
    for i in range(cantidad):
        tem = generar_tem_unico()
        sn  = sns[i] if i < len(sns) else ""
        item = {"tem": tem, "sn": sn, "imagen_b64": None}
        if LABELS_OK:
            try:
                buf = generar_etiqueta_png(tem, marca, modelo, sn, seccion, ancho_mm=ancho)
                item["imagen_b64"] = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                pass
        resultados.append(item)

    return jsonify({"ok": True, "tems": resultados, "total": len(resultados)})


@bp.route("/panel")
@login_required
def panel():
    """Página de gestión de etiquetas."""
    return render_template("etiquetas/panel.html", labels_ok=LABELS_OK)


@bp.route("/guardar_lote", methods=["POST"])
@login_required
def guardar_lote():
    """Guarda solo los TEMs y S/N en sesión (sin imágenes — las genera el servidor al imprimir)."""
    from flask import session
    data = request.get_json() or {}
    lote_raw = data.get("lote", [])
    ancho    = int(data.get("mm", 36))
    # Guardar solo lo ligero: tem, sn, marca, modelo
    lote_min = [{"tem": item["tem"], "sn": item.get("sn",""),
                 "marca": item.get("marca",""), "modelo": item.get("modelo","")}
                for item in lote_raw]
    session["lote_etiquetas"] = lote_min
    session["lote_mm"]        = ancho
    session.modified = True
    return jsonify({"ok": True, "url": "/etiquetas/imprimir_lote"})


@bp.route("/imprimir_lote")
@login_required
def imprimir_lote():
    """Genera las imágenes server-side y muestra la página de impresión."""
    import base64
    from flask import session
    lote_min = session.pop("lote_etiquetas", [])
    ancho    = session.pop("lote_mm", 36)
    session.modified = True

    lote = []
    for item in lote_min:
        entry = {"tem": item["tem"], "sn": item.get("sn",""),
                 "imagen_b64": None}
        if LABELS_OK:
            try:
                buf = generar_etiqueta_png(
                    item["tem"], item.get("marca",""), item.get("modelo",""),
                    item.get("sn",""), seccion="", ancho_mm=ancho
                )
                entry["imagen_b64"] = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                pass
        lote.append(entry)

    return render_template("etiquetas/lote_print.html", lote=lote)
