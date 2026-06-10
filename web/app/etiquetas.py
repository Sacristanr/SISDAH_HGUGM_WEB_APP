"""
Generador de etiquetas Code128 + QR para SISDAH
Produce PNG en memoria lista para imprimir o mostrar en web
"""
from flask import Blueprint, send_file, request, jsonify, render_template, url_for
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


# ─── Generación de etiquetas para Epson TM-L90 ───────────────────────────────
# Papel: "1inch Label" troquelado 60 × 25.4 mm
# Área imprimible real: 55.6 × 25.4 mm (el driver no llega a los bordes)
# Resolución nativa de la impresora: 180 dpi → generamos a 360 dpi (2x)
# para nitidez y que el navegador escale limpio.
#
# Cada código produce DOS etiquetas consecutivas:
#   1ª) solo Code128 grande (máxima legibilidad para el lector láser/CCD)
#   2ª) solo QR + datos (para escanear con el móvil)
# Meter ambos códigos en 55×25mm los hace demasiado pequeños y no se leen.

LABEL_W_MM = 55.6    # área imprimible
LABEL_H_MM = 25.4
LABEL_DPI  = 360

def _label_canvas():
    W = int(LABEL_W_MM / 25.4 * LABEL_DPI)   # ≈ 788 px
    H = int(LABEL_H_MM / 25.4 * LABEL_DPI)   # ≈ 360 px
    img  = Image.new("RGB", (W, H), (255, 255, 255))
    return img, ImageDraw.Draw(img), W, H

def _font(size):
    for nombre in ("arialbd.ttf", "arial.ttf", "Arial.ttf",
                   "C:/Windows/Fonts/arialbd.ttf",
                   "C:/Windows/Fonts/arial.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _save_png(img):
    buf = BytesIO()
    img.save(buf, format="PNG", dpi=(LABEL_DPI, LABEL_DPI))
    buf.seek(0)
    return buf


def generar_etiqueta_code128_png(icm: str, marca: str = "", modelo: str = "") -> BytesIO:
    """Etiqueta 1: SOLO Code128 a lo ancho + número debajo."""
    if not LABELS_OK:
        raise ImportError("Librerías de etiquetas no disponibles")

    img, draw, W, H = _label_canvas()
    NEGRO = (0, 0, 0)
    PAD   = int(LABEL_DPI * 0.04)            # ~1mm de margen

    f_num  = _font(int(H * 0.17))
    f_tiny = _font(int(H * 0.11))

    # Barcode ocupa todo el ancho y ~65% del alto
    bar_w = W - 2 * PAD
    bar_h = int(H * 0.62)
    try:
        CODE    = barcode.get_barcode_class("code128")
        buf_bar = BytesIO()
        opts = {
            "module_width":  0.25,           # se reescala después; >0.2 evita barras de 1px
            "module_height": 12,
            "background":    "white",
            "foreground":    "black",
            "write_text":    False,
            "quiet_zone":    1.0,            # quiet zone la damos nosotros con PAD
            "font_size":     0,
        }
        CODE(icm, writer=ImageWriter()).write(buf_bar, opts)
        buf_bar.seek(0)
        bar_src = Image.open(buf_bar).convert("L")
        # Recortar bordes blancos del generador para controlar el tamaño exacto
        bbox = Image.eval(bar_src, lambda p: 0 if p > 128 else 255).getbbox()
        if bbox:
            bar_src = bar_src.crop(bbox)
        # NEAREST mantiene las barras a ancho entero de píxel (sin grises de
        # antialiasing que confunden al lector)
        bar_src = bar_src.resize((bar_w, bar_h), Image.NEAREST).convert("RGB")
        img.paste(bar_src, (PAD, PAD))
    except Exception:
        draw.text((PAD, PAD), icm, font=f_num, fill=NEGRO)

    # Número centrado debajo, grande
    ty = PAD + bar_h + int(H * 0.03)
    tw = draw.textlength(icm, font=f_num)
    draw.text(((W - tw) // 2, ty), icm, font=f_num, fill=NEGRO)

    # Marca/modelo en pequeño abajo si cabe
    extra = f"{marca} {modelo}".strip()
    if extra:
        ty2 = ty + f_num.size + 2
        if ty2 + f_tiny.size <= H - 2:
            tw2 = draw.textlength(extra[:40], font=f_tiny)
            draw.text(((W - tw2) // 2, ty2), extra[:40], font=f_tiny, fill=(70, 70, 70))

    return _save_png(img)


def generar_etiqueta_qr_png(icm: str, marca: str = "", modelo: str = "",
                            sn: str = "") -> BytesIO:
    """Etiqueta 2: QR grande a la izquierda + datos a la derecha."""
    if not LABELS_OK:
        raise ImportError("Librerías de etiquetas no disponibles")

    img, draw, W, H = _label_canvas()
    NEGRO = (0, 0, 0)
    PAD   = int(LABEL_DPI * 0.04)

    # El QR enlaza a la ficha del equipo; sin contexto de petición cae a JSON
    try:
        qr_data = url_for("inventario.detalle", icm=icm, _external=True)
    except Exception:
        qr_data = json.dumps({"icm": icm, "sn": sn, "s": "SISDAH"},
                             ensure_ascii=False, separators=(',', ':'))

    qr = qrcode.QRCode(box_size=10, border=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img  = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = H - 2 * PAD                    # QR cuadrado a toda la altura
    # NEAREST: módulos del QR a píxel entero, sin antialiasing
    qr_img  = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    img.paste(qr_img, (PAD, PAD))

    # Datos a la derecha del QR
    tx = PAD + qr_size + int(W * 0.03)
    f_icm   = _font(int(H * 0.16))
    f_small = _font(int(H * 0.11))
    f_tiny  = _font(int(H * 0.09))

    ty = PAD + 2
    draw.text((tx, ty), icm, font=f_icm, fill=NEGRO)
    ty += f_icm.size + 6
    if marca:
        draw.text((tx, ty), marca[:22], font=f_small, fill=(40, 40, 40))
        ty += f_small.size + 3
    if modelo:
        draw.text((tx, ty), modelo[:24], font=f_small, fill=(40, 40, 40))
        ty += f_small.size + 3
    if sn:
        draw.text((tx, ty), f"SN: {sn}"[:26], font=f_tiny, fill=(80, 80, 80))
        ty += f_tiny.size + 3

    fecha = datetime.now().strftime("%d/%m/%Y")
    draw.text((tx, H - f_tiny.size - PAD), f"HGUGM · {fecha}", font=f_tiny,
              fill=(130, 130, 130))

    return _save_png(img)


def generar_etiqueta_png(icm: str, marca: str = "", modelo: str = "",
                          sn: str = "", seccion: str = "",
                          ancho_mm: int = 36) -> BytesIO:
    """Compatibilidad: la etiqueta 'principal' ahora es la de Code128.
    ancho_mm se ignora (el papel es fijo: 60×25.4mm troquelado)."""
    return generar_etiqueta_code128_png(icm, marca, modelo)


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
        if request.args.get("tipo") == "qr":
            buf = generar_etiqueta_qr_png(icm, marca, modelo, sn)
        else:
            buf = generar_etiqueta_code128_png(icm, marca, modelo)
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
                 "imagen_b64": None, "qr_b64": None}
        if LABELS_OK:
            try:
                buf = generar_etiqueta_code128_png(
                    item["tem"], item.get("marca",""), item.get("modelo",""))
                entry["imagen_b64"] = base64.b64encode(buf.getvalue()).decode()
                buf2 = generar_etiqueta_qr_png(
                    item["tem"], item.get("marca",""), item.get("modelo",""),
                    item.get("sn",""))
                entry["qr_b64"] = base64.b64encode(buf2.getvalue()).decode()
            except Exception:
                pass
        lote.append(entry)

    return render_template("etiquetas/lote_print.html", lote=lote)
