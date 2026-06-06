# Catálogo gestionado desde la BD (tabla `catalogo`).
# Las funciones devuelven listas igual que antes para no romper ningún consumidor.

# ── Datos iniciales (seed) ────────────────────────────────────────────────────
CATALOGO_SEED = {
    "PORTÁTILES": {
        "LENOVO": [
            "ThinkPad L14 Gen2", "ThinkPad L14 Gen3", "ThinkPad L14 Gen4",
            "ThinkPad E14 Gen3", "ThinkPad E14 Gen4", "ThinkPad E15 Gen3",
            "ThinkPad X1 Carbon", "IdeaPad 3", "IdeaPad 5",
        ],
        "HP": [
            "ProBook 450 G8", "ProBook 450 G9", "ProBook 450 G10",
            "EliteBook 840 G8", "EliteBook 840 G9", "EliteBook 650 G9",
            "Laptop 15s", "ZBook Fury",
        ],
        "DELL": [
            "Latitude 5420", "Latitude 5520", "Latitude 5530",
            "Inspiron 15", "Precision 3570",
        ],
        "ACER": ["Aspire 5", "TravelMate P2", "TravelMate P4"],
        "ASUS": ["ExpertBook B1", "ExpertBook B2", "VivoBook 15"],
        "MICROSOFT": ["Surface Pro 9", "Surface Laptop 5"],
    },
    "SOBREMESA": {
        "LENOVO": [
            "ThinkCentre M70s", "ThinkCentre M80s", "ThinkCentre M90s",
            "ThinkCentre M70q", "ThinkCentre Neo 50s",
        ],
        "HP": [
            "ProDesk 400 G7", "ProDesk 600 G6", "EliteDesk 800 G6",
            "EliteDesk 805 G8", "ProOne 440 G6",
        ],
        "DELL": ["OptiPlex 3090", "OptiPlex 5090", "OptiPlex 7090"],
        "ACER": ["Veriton X2", "Veriton N4"],
    },
    "IMPRESORAS": {
        "BROTHER": [
            "HL-5215DN", "HL-L5100DN", "HL-L6300DW",
            "MFC-L5700DN", "MFC-L6800DW", "DCP-L5500DN",
        ],
        "HP": [
            "LaserJet Pro M404dn", "LaserJet Pro M428fdw",
            "LaserJet Enterprise M507dn", "Color LaserJet M454dn",
        ],
        "RICOH": ["SP 3710DN", "IM 350F", "MP 305+"],
        "CANON": ["LBP6030", "LBP6230dn", "MF543x"],
        "KYOCERA": ["ECOSYS P3145dn", "ECOSYS M3645dn"],
        "KONICA MINOLTA": ["bizhub 4702P", "bizhub 4020i"],
    },
    "MONITORES": {
        "HP": ["E24 G4", "E27 G4", "P24h G4", "Z24n G3"],
        "DELL": ["P2422H", "P2722H", "U2422H", "S2421HS"],
        "LENOVO": ["ThinkVision T24i", "ThinkVision E24-28", "ThinkVision P27"],
        "LG": ["27BN650", "24MK430H", "27UK850"],
        "PHILIPS": ["243V7", "272V8A"],
        "AOC": ["24B2XH", "27B2H"],
    },
    "PERIFÉRICOS": {
        "LOGITECH": [
            "MK270 Kit", "MK295 Kit", "MK540 Kit",
            "M100 Ratón", "K120 Teclado", "B100 Ratón",
        ],
        "HP": ["Kit 300", "Kit 330", "Ratón X500"],
        "MICROSOFT": ["Kit 600", "Arc Mouse", "Sculpt Ergonomic"],
        "CHERRY": ["KC 1000 Kit", "DW 9000 Kit"],
    },
    "SERVIDORES": {
        "HP": [
            "ProLiant DL360 Gen10", "ProLiant DL380 Gen10",
            "ProLiant ML110 Gen10", "ProLiant DL20 Gen10",
        ],
        "DELL": [
            "PowerEdge R440", "PowerEdge R540", "PowerEdge T140",
        ],
        "LENOVO": ["ThinkSystem SR530", "ThinkSystem SR650"],
        "IBM": ["Power S1014", "Power S1022"],
    },
    "TELÉFONOS": {
        "CISCO": [
            "CP-7942G", "CP-7945G", "CP-7962G",
            "CP-8841", "CP-8851", "CP-8861", "CP-8865",
        ],
        "YEALINK": ["T41S", "T42S", "T46S", "T48S"],
        "POLYCOM": ["VVX 311", "VVX 411", "VVX 501"],
    },
    "TABLETS": {
        "APPLE": ["iPad 9", "iPad 10", "iPad Air 5", "iPad Pro 11"],
        "SAMSUNG": ["Galaxy Tab A8", "Galaxy Tab S7", "Galaxy Tab S8"],
        "MICROSOFT": ["Surface Pro 9", "Surface Go 3"],
        "LENOVO": ["Tab P11 Pro", "Tab M10 Plus"],
    },
}


def seed_catalogo(db, CatalogoItem):
    """Inserta datos iniciales si la tabla está vacía."""
    if CatalogoItem.query.count() > 0:
        return
    for seccion, marcas in CATALOGO_SEED.items():
        for marca, modelos in marcas.items():
            for modelo in modelos:
                db.session.add(CatalogoItem(
                    seccion=seccion.upper(),
                    marca=marca.upper(),
                    modelo=modelo,
                ))
    db.session.commit()


# ── API pública (misma firma que antes) ──────────────────────────────────────

def get_secciones():
    from .models import CatalogoItem
    rows = CatalogoItem.query.with_entities(CatalogoItem.seccion).distinct().all()
    return sorted(r.seccion for r in rows)


def get_marcas(seccion):
    from .models import CatalogoItem
    rows = (CatalogoItem.query
            .filter(CatalogoItem.seccion == seccion.upper())
            .with_entities(CatalogoItem.marca).distinct().all())
    return sorted(r.marca for r in rows)


def get_modelos(seccion, marca):
    from .models import CatalogoItem
    rows = (CatalogoItem.query
            .filter(CatalogoItem.seccion == seccion.upper(),
                    CatalogoItem.marca == marca.upper())
            .with_entities(CatalogoItem.modelo)
            .order_by(CatalogoItem.modelo).all())
    return [r.modelo for r in rows]
