import importlib.util
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook


def decode_step(text: str) -> str:
    def repl16(match):
        try:
            return bytes.fromhex(match.group(1)).decode("utf-16-be")
        except Exception:
            return match.group(0)

    def repl32(match):
        try:
            return bytes.fromhex(match.group(1)).decode("utf-32-be")
        except Exception:
            return match.group(0)

    text = re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", repl16, text)
    text = re.sub(r"\\X4\\([0-9A-Fa-f]+)\\X0\\", repl32, text)
    return text.replace("''", "'")


def quoted_args(entity: str):
    return [decode_step(s) for s in re.findall(r"'((?:''|[^'])*)'", entity)]


def inspect_xlsx(path: Path):
    wb = load_workbook(path, read_only=False, data_only=False, keep_links=True)
    sheets = []
    for ws in wb.worksheets:
        hyperlinks = []
        comments = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.hyperlink:
                    hyperlinks.append({"cell": cell.coordinate, "target": cell.hyperlink.target})
                if cell.comment:
                    comments.append({"cell": cell.coordinate, "author": cell.comment.author, "text": cell.comment.text})
        hidden_rows = [idx for idx, dim in ws.row_dimensions.items() if dim.hidden]
        hidden_cols = [idx for idx, dim in ws.column_dimensions.items() if dim.hidden]
        sheets.append({
            "name": ws.title,
            "state": ws.sheet_state,
            "max_row": ws.max_row,
            "max_column": ws.max_column,
            "merged_ranges": [str(r) for r in ws.merged_cells.ranges],
            "hidden_rows": hidden_rows,
            "hidden_cols": hidden_cols,
            "hyperlinks": hyperlinks,
            "comments": comments,
            "images": len(getattr(ws, "_images", [])),
            "charts": len(getattr(ws, "_charts", [])),
        })
    with zipfile.ZipFile(path) as zf:
        package_parts = [
            name for name in zf.namelist()
            if name.startswith(("xl/media/", "xl/drawings/", "xl/comments", "xl/threadedComments/", "xl/externalLinks/"))
            or "vmlDrawing" in name
        ]
    return {"path": str(path), "sheets": sheets, "package_parts": package_parts}


def inspect_step(path: Path):
    text = path.read_text(encoding="latin-1", errors="replace")
    decoded_text = decode_step(text)
    header_match = re.search(r"HEADER;(.*?)ENDSEC;", decoded_text, flags=re.S | re.I)
    header = header_match.group(1).strip() if header_match else ""
    entity_counts = Counter(re.findall(r"=\s*([A-Z0-9_]+)\s*\(", text))

    def entities(kind):
        return re.findall(rf"#\d+\s*=\s*{kind}\s*\((.*?)\);", decoded_text, flags=re.S | re.I)

    products = [quoted_args(x) for x in entities("PRODUCT")]
    formations = [quoted_args(x) for x in entities("PRODUCT_DEFINITION_FORMATION(?:_WITH_SPECIFIED_SOURCE)?")]
    representations = [quoted_args(x) for x in entities("(?:ADVANCED_BREP_)?SHAPE_REPRESENTATION")]
    assembly = [quoted_args(x) for x in entities("NEXT_ASSEMBLY_USAGE_OCCURRENCE")]
    product_names = []
    for args in products:
        for value in args[:2]:
            if value and value not in product_names:
                product_names.append(value)
    representation_names = []
    for args in representations:
        if args and args[0] and args[0] not in representation_names:
            representation_names.append(args[0])

    return {
        "path": str(path),
        "size": path.stat().st_size,
        "header": header,
        "schema": re.findall(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)", header, flags=re.S | re.I),
        "product_names": product_names,
        "representation_names": representation_names,
        "assembly_usage_names": [args[:3] for args in assembly],
        "counts": {k: entity_counts.get(k, 0) for k in [
            "PRODUCT", "PRODUCT_DEFINITION", "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
            "MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS", "CLOSED_SHELL", "OPEN_SHELL",
            "ADVANCED_BREP_SHAPE_REPRESENTATION", "SHAPE_REPRESENTATION",
            "SHAPE_REPRESENTATION_RELATIONSHIP", "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION",
            "MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION"
        ]},
        "top_entity_counts": entity_counts.most_common(20),
        "formation_count": len(formations),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    xlsx = Path(sys.argv[1])
    steps = [Path(p) for p in sys.argv[2:]]
    modules = ["cadquery", "OCP", "OCC", "trimesh", "build123d", "steputils", "pyvista", "vtk"]
    result = {
        "available_python_modules": {m: bool(importlib.util.find_spec(m)) for m in modules},
        "xlsx": inspect_xlsx(xlsx),
        "steps": [inspect_step(p) for p in steps],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
