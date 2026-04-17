#!/usr/bin/env python3
"""
Gestión de datos inmobiliarios.
Recibe datos de propiedades, los agrupa, almacena en CSV y genera un XLSX formateado.
"""

import argparse
import csv
import os
import sys
import traceback
from datetime import datetime


# ── Error helpers ───────────────────────────────────────────────────────────
# All non-fatal warnings go to stderr with a [WARN] prefix.
# All fatal errors go to stderr with an [ERROR] prefix and exit with code != 0.
# Success messages go to stdout with an [OK] prefix.
# This makes it easy for the model to tell success from failure when it
# captures combined output with `2>&1`.

def log_ok(msg: str) -> None:
    print(f"[OK] {msg}", file=sys.stdout, flush=True)

def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr, flush=True)

def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)

def die(msg: str, code: int = 1) -> None:
    log_error(msg)
    sys.exit(code)


try:
    import xlsxwriter
except ImportError:
    print("[INFO] Instalando xlsxwriter...", file=sys.stderr, flush=True)
    rc = os.system(f"{sys.executable} -m pip install xlsxwriter --break-system-packages -q")
    if rc != 0:
        die("No se pudo instalar xlsxwriter. Revisa el venv y la conexión.", 2)
    import xlsxwriter


# ── Column mapping ──────────────────────────────────────────────────────────
HEADERS_EN = [
    "id", "property_type", "transaction_type", "price",
    "m2_terrain", "m2_construction", "bedrooms", "baths",
    "garage", "location", "address", "file_path"
]

HEADERS_ES = [
    "ID", "Tipo de propiedad", "Tipo de transacción", "Precio propiedad",
    "Metros cuadrados superficie", "Metros cuadrados construcción",
    "Número de cuartos", "Número de baños", "Cochera número espacios",
    "Zona", "Dirección", "Folder"
]

PROPERTY_TYPES = [
    "casa", "departamento", "loft", "penthouse", "terreno",
    "lote", "bodega", "local", "oficina", "consultorio"
]

TRANSACTION_TYPES = ["venta", "renta"]


# ── Data helpers ────────────────────────────────────────────────────────────
def validate_property(data: dict) -> list[str]:
    errors = []
    if data.get("property_type", "").lower() not in PROPERTY_TYPES:
        errors.append(f"Tipo de propiedad inválido: '{data.get('property_type')}'. "
                      f"Opciones: {', '.join(PROPERTY_TYPES)}")
    if data.get("transaction_type", "").lower() not in TRANSACTION_TYPES:
        errors.append(f"Tipo de transacción inválido: '{data.get('transaction_type')}'. "
                      f"Opciones: {', '.join(TRANSACTION_TYPES)}")
    for field in ("price", "m2_terrain", "m2_construction", "bedrooms", "baths", "garage"):
        try:
            val = float(data.get(field, 0))
            if val < 0:
                errors.append(f"{field} no puede ser negativo.")
        except (ValueError, TypeError):
            errors.append(f"{field} debe ser numérico.")
    return errors


def save_to_csv(records: list[dict], csv_path: str) -> None:
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS_EN)
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)


def load_from_csv(csv_path: str) -> list[dict]:
    if not os.path.isfile(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_by(records: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in records:
        k = r.get(key, "Sin definir").strip().capitalize()
        groups.setdefault(k, []).append(r)
    return dict(sorted(groups.items()))


# ── XLSX generation ─────────────────────────────────────────────────────────
def generate_xlsx(records: list[dict], xlsx_path: str) -> None:
    wb = xlsxwriter.Workbook(xlsx_path)

    # ── Formats ──
    title_fmt = wb.add_format({
        "bold": True, "font_size": 18, "font_name": "Arial",
        "font_color": "#FFFFFF", "bg_color": "#2E4057",
        "align": "center", "valign": "vcenter", "bottom": 2,
    })
    subtitle_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_name": "Arial",
        "font_color": "#555555", "align": "center", "valign": "vcenter",
    })
    header_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_name": "Arial",
        "font_color": "#FFFFFF", "bg_color": "#3B6FA0",
        "align": "center", "valign": "vcenter",
        "border": 1, "text_wrap": True,
    })
    text_fmt = wb.add_format({
        "font_size": 10, "font_name": "Arial",
        "align": "left", "valign": "vcenter",
        "border": 1, "text_wrap": True,
    })
    text_center_fmt = wb.add_format({
        "font_size": 10, "font_name": "Arial",
        "align": "center", "valign": "vcenter", "border": 1,
    })
    money_fmt = wb.add_format({
        "font_size": 10, "font_name": "Arial",
        "num_format": "$#,##0.00", "align": "right",
        "valign": "vcenter", "border": 1,
    })
    number_fmt = wb.add_format({
        "font_size": 10, "font_name": "Arial",
        "num_format": "#,##0.00", "align": "center",
        "valign": "vcenter", "border": 1,
    })
    int_fmt = wb.add_format({
        "font_size": 10, "font_name": "Arial",
        "num_format": "#,##0", "align": "center",
        "valign": "vcenter", "border": 1,
    })
    group_header_fmt = wb.add_format({
        "bold": True, "font_size": 12, "font_name": "Arial",
        "font_color": "#2E4057", "bg_color": "#D6E4F0",
        "align": "left", "valign": "vcenter", "bottom": 1,
    })
    summary_label_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_name": "Arial",
        "align": "right", "valign": "vcenter", "border": 1,
        "bg_color": "#EAF0F6",
    })
    summary_value_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_name": "Arial",
        "num_format": "$#,##0.00", "align": "right",
        "valign": "vcenter", "border": 1, "bg_color": "#EAF0F6",
    })
    summary_int_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_name": "Arial",
        "num_format": "#,##0", "align": "center",
        "valign": "vcenter", "border": 1, "bg_color": "#EAF0F6",
    })

    col_widths = [8, 18, 18, 20, 16, 16, 14, 14, 14, 20, 30, 30]

    # ── Helper to write one table block ──
    def write_table(ws, start_row, data_rows):
        for i, w in enumerate(col_widths):
            ws.set_column(i, i, w)
        for col_i, h in enumerate(HEADERS_ES):
            ws.write(start_row, col_i, h, header_fmt)
        row = start_row + 1
        first_data = row
        for rec in data_rows:
            ws.write(row, 0, rec.get("id", ""), text_center_fmt)
            ws.write(row, 1, rec.get("property_type", "").capitalize(), text_center_fmt)
            ws.write(row, 2, rec.get("transaction_type", "").capitalize(), text_center_fmt)
            try:
                ws.write_number(row, 3, float(rec.get("price", 0)), money_fmt)
            except (ValueError, TypeError):
                ws.write(row, 3, rec.get("price", ""), text_fmt)
            try:
                ws.write_number(row, 4, float(rec.get("m2_terrain", 0)), number_fmt)
            except (ValueError, TypeError):
                ws.write(row, 4, rec.get("m2_terrain", ""), text_fmt)
            try:
                ws.write_number(row, 5, float(rec.get("m2_construction", 0)), number_fmt)
            except (ValueError, TypeError):
                ws.write(row, 5, rec.get("m2_construction", ""), text_fmt)
            for ci, field in ((6, "bedrooms"), (7, "baths"), (8, "garage")):
                try:
                    ws.write_number(row, ci, int(float(rec.get(field, 0))), int_fmt)
                except (ValueError, TypeError):
                    ws.write(row, ci, rec.get(field, ""), text_fmt)
            ws.write(row, 9, rec.get("location", ""), text_fmt)
            ws.write(row, 10, rec.get("address", ""), text_fmt)
            ws.write(row, 11, rec.get("file_path", ""), text_fmt)
            row += 1
        last_data = row - 1

        # Summary row
        ws.write(row, 2, "Total / Promedio:", summary_label_fmt)
        if last_data >= first_data:
            ws.write_formula(row, 3,
                f"=SUM(D{first_data+1}:D{last_data+1})", summary_value_fmt)
            ws.write_formula(row, 4,
                f"=AVERAGE(E{first_data+1}:E{last_data+1})", summary_int_fmt)
            ws.write_formula(row, 5,
                f"=AVERAGE(F{first_data+1}:F{last_data+1})", summary_int_fmt)
            ws.write_formula(row, 6,
                f"=SUM(G{first_data+1}:G{last_data+1})", summary_int_fmt)
            ws.write_formula(row, 7,
                f"=SUM(H{first_data+1}:H{last_data+1})", summary_int_fmt)
            ws.write_formula(row, 8,
                f"=SUM(I{first_data+1}:I{last_data+1})", summary_int_fmt)
        return row + 2

    # ── Sheet 1: Resumen General ──
    ws_all = wb.add_worksheet("Resumen General")
    ws_all.hide_gridlines(2)
    ws_all.set_row(0, 40)
    ws_all.merge_range(0, 0, 0, len(HEADERS_ES) - 1,
                       "Reporte Inmobiliario General", title_fmt)
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws_all.merge_range(1, 0, 1, len(HEADERS_ES) - 1,
                       f"Generado: {timestamp}  —  Total propiedades: {len(records)}",
                       subtitle_fmt)
    write_table(ws_all, 3, records)
    ws_all.autofilter(3, 0, 3 + len(records), len(HEADERS_ES) - 1)
    ws_all.freeze_panes(4, 0)

    # ── Sheet 2: Agrupado por Tipo de Propiedad ──
    groups_prop = group_by(records, "property_type")
    ws_prop = wb.add_worksheet("Por Tipo Propiedad")
    ws_prop.hide_gridlines(2)
    ws_prop.set_row(0, 40)
    ws_prop.merge_range(0, 0, 0, len(HEADERS_ES) - 1,
                        "Propiedades Agrupadas por Tipo", title_fmt)
    row = 2
    for gname, rows in groups_prop.items():
        ws_prop.merge_range(row, 0, row, len(HEADERS_ES) - 1,
                            f"{gname}  ({len(rows)} propiedades)", group_header_fmt)
        row = write_table(ws_prop, row + 1, rows)

    # ── Sheet 3: Agrupado por Tipo de Transacción ──
    groups_tx = group_by(records, "transaction_type")
    ws_tx = wb.add_worksheet("Por Transacción")
    ws_tx.hide_gridlines(2)
    ws_tx.set_row(0, 40)
    ws_tx.merge_range(0, 0, 0, len(HEADERS_ES) - 1,
                      "Propiedades Agrupadas por Transacción", title_fmt)
    row = 2
    for gname, rows in groups_tx.items():
        ws_tx.merge_range(row, 0, row, len(HEADERS_ES) - 1,
                          f"{gname}  ({len(rows)} propiedades)", group_header_fmt)
        row = write_table(ws_tx, row + 1, rows)

    # ── Sheet 4: Agrupado por Zona ──
    groups_loc = group_by(records, "location")
    ws_loc = wb.add_worksheet("Por Zona")
    ws_loc.hide_gridlines(2)
    ws_loc.set_row(0, 40)
    ws_loc.merge_range(0, 0, 0, len(HEADERS_ES) - 1,
                       "Propiedades Agrupadas por Zona", title_fmt)
    row = 2
    for gname, rows in groups_loc.items():
        ws_loc.merge_range(row, 0, row, len(HEADERS_ES) - 1,
                           f"{gname}  ({len(rows)} propiedades)", group_header_fmt)
        row = write_table(ws_loc, row + 1, rows)

    wb.close()


# ── Interactive CLI ─────────────────────────────────────────────────────────
def prompt_property() -> dict:
    print("\n── Nueva Propiedad ──")
    data = {}
    data["id"] = input("  ID: ").strip()
    print(f"  Tipos válidos: {', '.join(PROPERTY_TYPES)}")
    data["property_type"] = input("  Tipo de propiedad: ").strip().lower()
    print(f"  Transacciones válidas: {', '.join(TRANSACTION_TYPES)}")
    data["transaction_type"] = input("  Tipo de transacción: ").strip().lower()
    data["price"] = input("  Precio propiedad: ").strip()
    data["m2_terrain"] = input("  Metros cuadrados superficie: ").strip()
    data["m2_construction"] = input("  Metros cuadrados construcción: ").strip()
    data["bedrooms"] = input("  Número de cuartos: ").strip()
    data["baths"] = input("  Número de baños: ").strip()
    data["garage"] = input("  Cochera número espacios: ").strip()
    data["location"] = input("  Zona: ").strip()
    data["address"] = input("  Dirección: ").strip()
    data["file_path"] = input("  Folder (ruta archivos): ").strip()
    return data


SAMPLE_DATA = [
    {"id": "001", "property_type": "casa", "transaction_type": "venta",
     "price": "3500000", "m2_terrain": "250", "m2_construction": "180",
     "bedrooms": "3", "baths": "2", "garage": "2",
     "location": "Polanco", "address": "Av. Horacio 1020, CDMX",
     "file_path": "/docs/prop_001"},
    {"id": "002", "property_type": "departamento", "transaction_type": "renta",
     "price": "18000", "m2_terrain": "0", "m2_construction": "85",
     "bedrooms": "2", "baths": "1", "garage": "1",
     "location": "Roma Norte", "address": "Calle Orizaba 45, CDMX",
     "file_path": "/docs/prop_002"},
    {"id": "003", "property_type": "oficina", "transaction_type": "renta",
     "price": "45000", "m2_terrain": "0", "m2_construction": "120",
     "bedrooms": "0", "baths": "2", "garage": "3",
     "location": "Santa Fe", "address": "Av. Vasco de Quiroga 3800, CDMX",
     "file_path": "/docs/prop_003"},
    {"id": "004", "property_type": "terreno", "transaction_type": "venta",
     "price": "8500000", "m2_terrain": "500", "m2_construction": "0",
     "bedrooms": "0", "baths": "0", "garage": "0",
     "location": "Coyoacán", "address": "Calle Francisco Sosa 200, CDMX",
     "file_path": "/docs/prop_004"},
    {"id": "005", "property_type": "penthouse", "transaction_type": "venta",
     "price": "12000000", "m2_terrain": "0", "m2_construction": "320",
     "bedrooms": "4", "baths": "3", "garage": "3",
     "location": "Polanco", "address": "Campos Elíseos 218, CDMX",
     "file_path": "/docs/prop_005"},
    {"id": "006", "property_type": "local", "transaction_type": "renta",
     "price": "35000", "m2_terrain": "0", "m2_construction": "60",
     "bedrooms": "0", "baths": "1", "garage": "0",
     "location": "Roma Norte", "address": "Av. Álvaro Obregón 130, CDMX",
     "file_path": "/docs/prop_006"},
    {"id": "007", "property_type": "casa", "transaction_type": "venta",
     "price": "5200000", "m2_terrain": "300", "m2_construction": "220",
     "bedrooms": "4", "baths": "3", "garage": "2",
     "location": "Coyoacán", "address": "Av. Universidad 1500, CDMX",
     "file_path": "/docs/prop_007"},
    {"id": "008", "property_type": "loft", "transaction_type": "renta",
     "price": "22000", "m2_terrain": "0", "m2_construction": "75",
     "bedrooms": "1", "baths": "1", "garage": "1",
     "location": "Condesa", "address": "Calle Tamaulipas 90, CDMX",
     "file_path": "/docs/prop_008"},
    {"id": "009", "property_type": "bodega", "transaction_type": "renta",
     "price": "55000", "m2_terrain": "800", "m2_construction": "600",
     "bedrooms": "0", "baths": "1", "garage": "5",
     "location": "Azcapotzalco", "address": "Calz. Vallejo 1200, CDMX",
     "file_path": "/docs/prop_009"},
    {"id": "010", "property_type": "consultorio", "transaction_type": "renta",
     "price": "15000", "m2_terrain": "0", "m2_construction": "40",
     "bedrooms": "0", "baths": "1", "garage": "1",
     "location": "Santa Fe", "address": "Av. Santa Fe 482, CDMX",
     "file_path": "/docs/prop_010"},
]


# ── argparse setup ──────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inmobiliaria",
        description="Sistema de Gestión Inmobiliaria — almacena propiedades en CSV y genera reportes XLSX.",
        epilog=(
            "Ejemplos:\n"
            "  %(prog)s agregar --id 011 --tipo casa --transaccion venta --precio 4500000 \\\n"
            "           --superficie 200 --construccion 150 --cuartos 3 --banos 2 --cochera 2 \\\n"
            "           --zona Polanco --direccion 'Av. Horacio 500' --folder /docs/011\n\n"
            "  %(prog)s agregar --id 012 --tipo departamento --transaccion renta --precio 25000 \\\n"
            "           --superficie 0 --construccion 90 --cuartos 2 --banos 1 --cochera 1 \\\n"
            "           --zona 'Roma Norte' --direccion 'Orizaba 80' --folder /docs/012\n\n"
            "  %(prog)s reporte\n"
            "  %(prog)s reporte --csv datos.csv --xlsx salida.xlsx\n"
            "  %(prog)s resumen\n"
            "  %(prog)s ejemplo\n"
            "  %(prog)s interactivo\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--csv", default="propiedades.csv",
                        help="Ruta al archivo CSV (default: propiedades.csv)")
    parser.add_argument("--xlsx", default="reporte_inmobiliario.xlsx",
                        help="Ruta al archivo XLSX de salida (default: reporte_inmobiliario.xlsx)")

    sub = parser.add_subparsers(dest="comando", help="Comando a ejecutar")

    # ── agregar ──
    add_p = sub.add_parser("agregar", help="Agregar una propiedad vía flags",
                           formatter_class=argparse.RawDescriptionHelpFormatter)
    add_p.add_argument("--id", required=True, help="ID de la propiedad")
    add_p.add_argument("--tipo", required=True, choices=PROPERTY_TYPES,
                       metavar="TIPO", help=f"Tipo de propiedad: {', '.join(PROPERTY_TYPES)}")
    add_p.add_argument("--transaccion", required=True, choices=TRANSACTION_TYPES,
                       metavar="TRANSACCION", help=f"Tipo de transacción: {', '.join(TRANSACTION_TYPES)}")
    add_p.add_argument("--precio", required=True, type=float, help="Precio de la propiedad")
    add_p.add_argument("--superficie", required=True, type=float,
                       help="Metros cuadrados de superficie / terreno")
    add_p.add_argument("--construccion", required=True, type=float,
                       help="Metros cuadrados de construcción")
    add_p.add_argument("--cuartos", required=True, type=int, help="Número de cuartos")
    add_p.add_argument("--banos", required=True, type=int, help="Número de baños")
    add_p.add_argument("--cochera", required=True, type=int, help="Cochera: número de espacios")
    add_p.add_argument("--zona", required=True, help="Zona / ubicación")
    add_p.add_argument("--direccion", required=True, help="Dirección completa")
    add_p.add_argument("--folder", required=True, help="Ruta a los archivos de la propiedad")
    add_p.add_argument("--force", action="store_true",
                       help="Guardar aunque haya errores de validación")

    # ── agregar-lote (batch from JSON) ──
    batch_p = sub.add_parser("agregar-lote",
                             help="Agregar múltiples propiedades desde un archivo JSON")
    batch_p.add_argument("--archivo", required=True,
                         help="Ruta al archivo JSON con lista de propiedades")
    batch_p.add_argument("--force", action="store_true",
                         help="Guardar aunque haya errores de validación")

    # ── reporte ──
    sub.add_parser("reporte", help="Generar reporte XLSX a partir del CSV actual")

    # ── resumen ──
    sub.add_parser("resumen", help="Mostrar resumen del CSV actual en terminal")

    # ── ejemplo ──
    sub.add_parser("ejemplo", help="Cargar datos de ejemplo al CSV")

    # ── interactivo ──
    sub.add_parser("interactivo", help="Iniciar el menú interactivo")

    return parser


# ── Subcommand handlers ─────────────────────────────────────────────────────
def cmd_agregar(args) -> None:
    prop = {
        "id": args.id,
        "property_type": args.tipo,
        "transaction_type": args.transaccion,
        "price": str(args.precio),
        "m2_terrain": str(args.superficie),
        "m2_construction": str(args.construccion),
        "bedrooms": str(args.cuartos),
        "baths": str(args.banos),
        "garage": str(args.cochera),
        "location": args.zona,
        "address": args.direccion,
        "file_path": args.folder,
    }
    errors = validate_property(prop)
    if errors and not args.force:
        log_error("Errores de validación en los datos de la propiedad:")
        for e in errors:
            log_error(f"  - {e}")
        log_error("Usa --force para guardar de todos modos.")
        sys.exit(1)
    if errors:
        log_warn("Guardando con advertencias:")
        for e in errors:
            log_warn(f"  - {e}")
    try:
        save_to_csv([prop], args.csv)
    except OSError as exc:
        die(f"No pude escribir el CSV en '{args.csv}': {exc}", 3)
    log_ok(f"Propiedad {args.id} guardada en {args.csv}")


def cmd_agregar_lote(args) -> None:
    import json
    try:
        with open(args.archivo, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        die(f"No existe el archivo JSON: {args.archivo}", 4)
    except json.JSONDecodeError as exc:
        die(f"El archivo JSON está mal formado ({args.archivo}): {exc}", 5)
    if not isinstance(data, list):
        die("El archivo JSON debe contener una lista de objetos.", 6)
    saved = 0
    for i, item in enumerate(data, 1):
        prop = {k: str(item.get(k, "")) for k in HEADERS_EN}
        errors = validate_property(prop)
        if errors and not args.force:
            log_warn(f"Propiedad #{i} (ID={prop.get('id','?')}): errores de validación — omitida")
            for e in errors:
                log_warn(f"    - {e}")
            continue
        try:
            save_to_csv([prop], args.csv)
        except OSError as exc:
            die(f"No pude escribir el CSV en '{args.csv}': {exc}", 3)
        saved += 1
    log_ok(f"{saved}/{len(data)} propiedades guardadas en {args.csv}")


def cmd_reporte(args) -> None:
    records = load_from_csv(args.csv)
    if not records:
        die(f"No hay datos en {args.csv}. Agrega propiedades primero.", 7)
    try:
        generate_xlsx(records, args.xlsx)
    except OSError as exc:
        die(f"No pude escribir el XLSX en '{args.xlsx}': {exc}", 3)
    log_ok(f"Reporte generado: {args.xlsx}")
    print(f"       Hojas: Resumen General, Por Tipo Propiedad, Por Transacción, Por Zona")
    print(f"       Total propiedades: {len(records)}")


def cmd_resumen(args) -> None:
    records = load_from_csv(args.csv)
    if not records:
        die(f"No hay datos en {args.csv}.", 7)
    print(f"\n  Propiedades en CSV: {len(records)}")
    print(f"\n  Por tipo de propiedad:")
    for g, rows in group_by(records, "property_type").items():
        print(f"    {g}: {len(rows)}")
    print(f"\n  Por tipo de transacción:")
    for g, rows in group_by(records, "transaction_type").items():
        print(f"    {g}: {len(rows)}")
    print(f"\n  Por zona:")
    for g, rows in group_by(records, "location").items():
        print(f"    {g}: {len(rows)}")


def cmd_ejemplo(args) -> None:
    try:
        save_to_csv(SAMPLE_DATA, args.csv)
    except OSError as exc:
        die(f"No pude escribir el CSV en '{args.csv}': {exc}", 3)
    log_ok(f"{len(SAMPLE_DATA)} propiedades de ejemplo guardadas en {args.csv}")


def interactive_loop(csv_path: str, xlsx_path: str) -> None:
    print("=" * 60)
    print("   SISTEMA DE GESTIÓN INMOBILIARIA")
    print("=" * 60)

    while True:
        print("\nOpciones:")
        print("  1. Agregar propiedad")
        print("  2. Agregar múltiples propiedades (datos de ejemplo)")
        print("  3. Generar reporte XLSX")
        print("  4. Ver resumen CSV actual")
        print("  5. Salir")
        choice = input("\nSeleccione una opción: ").strip()

        if choice == "1":
            prop = prompt_property()
            errors = validate_property(prop)
            if errors:
                print("\n⚠ Errores de validación:")
                for e in errors:
                    print(f"   - {e}")
                if input("  ¿Guardar de todos modos? (s/n): ").strip().lower() != "s":
                    continue
            save_to_csv([prop], csv_path)
            print(f"✓ Propiedad guardada en {csv_path}")

        elif choice == "2":
            save_to_csv(SAMPLE_DATA, csv_path)
            print(f"✓ {len(SAMPLE_DATA)} propiedades de ejemplo guardadas en {csv_path}")

        elif choice == "3":
            records = load_from_csv(csv_path)
            if not records:
                print("⚠ No hay datos en el CSV. Agregue propiedades primero.")
                continue
            generate_xlsx(records, xlsx_path)
            print(f"✓ Reporte generado: {xlsx_path}")
            print(f"  Hojas: Resumen General, Por Tipo Propiedad, Por Transacción, Por Zona")
            print(f"  Total propiedades: {len(records)}")

        elif choice == "4":
            records = load_from_csv(csv_path)
            if not records:
                print("⚠ No hay datos en el CSV.")
                continue
            print(f"\n  Propiedades en CSV: {len(records)}")
            groups = group_by(records, "property_type")
            for g, rows in groups.items():
                print(f"    {g}: {len(rows)}")

        elif choice == "5":
            print("¡Hasta luego!")
            break
        else:
            print("Opción no válida.")


# ── Entrypoint ──────────────────────────────────────────────────────────────
def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.comando is None:
        # No subcommand → show help
        parser.print_help()
        print("\n💡 Para el menú interactivo use: inmobiliaria interactivo")
        sys.exit(0)

    dispatch = {
        "agregar": cmd_agregar,
        "agregar-lote": cmd_agregar_lote,
        "reporte": cmd_reporte,
        "resumen": cmd_resumen,
        "ejemplo": cmd_ejemplo,
    }

    if args.comando == "interactivo":
        interactive_loop(args.csv, args.xlsx)
    elif args.comando in dispatch:
        dispatch[args.comando](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        log_error("Interrumpido por el usuario.")
        sys.exit(130)
    except Exception as exc:
        log_error(f"Error inesperado: {type(exc).__name__}: {exc}")
        log_error("Traza completa:")
        traceback.print_exc(file=sys.stderr)
        sys.exit(99)
