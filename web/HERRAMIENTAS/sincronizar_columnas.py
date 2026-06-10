#!/usr/bin/env python
r"""
SISDAH — Sincronizador de columnas faltantes.

Compara los modelos SQLAlchemy con la base de datos real y añade las
columnas que falten con ALTER TABLE ... ADD COLUMN. Pensado para la BD
del hospital, que tiene un esquema antiguo y va dando errores
"Unknown column" según se usan pantallas nuevas.

Uso (desde la carpeta web\):
    python HERRAMIENTAS\sincronizar_columnas.py           # solo muestra lo que haría
    python HERRAMIENTAS\sincronizar_columnas.py --aplicar # aplica los cambios
"""
import sys, os

_web = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _web)
os.chdir(_web)

APLICAR = "--aplicar" in sys.argv

from app import create_app
from app.models import db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    insp = inspect(db.engine)
    tablas_bd = set(insp.get_table_names())
    pendientes = []

    for tabla in db.metadata.sorted_tables:
        if tabla.name not in tablas_bd:
            print(f"[AVISO] La tabla '{tabla.name}' no existe en la BD — se creará entera.")
            pendientes.append(("CREAR_TABLA", tabla))
            continue
        cols_bd = {c["name"] for c in insp.get_columns(tabla.name)}
        for col in tabla.columns:
            if col.name not in cols_bd:
                tipo = col.type.compile(db.engine.dialect)
                sql = f"ALTER TABLE {tabla.name} ADD COLUMN {col.name} {tipo} NULL"
                pendientes.append(("SQL", sql))

    if not pendientes:
        print("[OK] Todas las tablas y columnas de los modelos existen en la BD.")
        sys.exit(0)

    print()
    print("=" * 60)
    print(f"  {len(pendientes)} cambio(s) pendiente(s):")
    print("=" * 60)
    for tipo, item in pendientes:
        if tipo == "SQL":
            print(f"  {item}")
        else:
            print(f"  CREATE TABLE {item.name} (tabla completa)")
    print()

    if not APLICAR:
        print("Modo simulacion. Para aplicar los cambios ejecuta:")
        print("    python HERRAMIENTAS\\sincronizar_columnas.py --aplicar")
        sys.exit(0)

    errores = 0
    for tipo, item in pendientes:
        try:
            if tipo == "SQL":
                db.session.execute(text(item))
                db.session.commit()
                print(f"[OK] {item}")
            else:
                item.create(db.engine)
                print(f"[OK] CREATE TABLE {item.name}")
        except Exception as e:
            db.session.rollback()
            errores += 1
            print(f"[ERROR] {item if tipo == 'SQL' else item.name}: {e}")

    print()
    if errores:
        print(f"[AVISO] Terminado con {errores} error(es). Revisa arriba.")
        sys.exit(1)
    print("[OK] Base de datos sincronizada con los modelos.")
