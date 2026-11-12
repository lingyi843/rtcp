import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def decode_step(text: str) -> str:
    def repl16(match):
        try:
            return bytes.fromhex(match.group(1)).decode("utf-16-be")
        except Exception:
            return match.group(0)
    return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", repl16, text).replace("''", "'")


def quoted_args(entity: str):
    return [decode_step(s) for s in re.findall(r"'((?:''|[^'])*)'", entity)]


def extract_entities(text: str, kind: str):
    return re.findall(rf"#\d+\s*=\s*{kind}\s*\((.*?)\);", text, flags=re.S | re.I)


def inspect_assembly(path: Path):
    raw = path.read_text(encoding="latin-1", errors="replace")
    text = decode_step(raw)
    products = [quoted_args(x) for x in extract_entities(text, "PRODUCT")]
    usages = [quoted_args(x) for x in extract_entities(text, "NEXT_ASSEMBLY_USAGE_OCCURRENCE")]
    product_names = []
    for args in products:
        for value in args[:2]:
            if value and value not in product_names:
                product_names.append(value)
    keywords = ("挤出", "热端", "喷嘴", "喉管", "齿轮", "摆臂", "风扇", "风道", "气动", "电机", "TT", "V6", "E3D", "BMG", "Titan", "泰坦")
    matching_products = [x for x in product_names if any(k.lower() in x.lower() for k in keywords)]
    matching_usages = [x for x in usages if any(k.lower() in " ".join(x).lower() for k in keywords)]
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "product_count": len(products),
        "unique_product_name_count": len(product_names),
        "assembly_usage_count": len(usages),
        "matching_products": matching_products,
        "matching_usages": matching_usages,
    }


def inspect_3mf(path: Path):
    records = []
    package_names = []
    with zipfile.ZipFile(path) as zf:
        package_names = zf.namelist()
        model_files = [n for n in package_names if n.lower().endswith(".model")]
        for model_file in model_files:
            root = ET.fromstring(zf.read(model_file))
            for elem in root.iter():
                local = elem.tag.rsplit("}", 1)[-1]
                if local in {"object", "item", "metadata"}:
                    row = {"model_file": model_file, "kind": local}
                    row.update({k.rsplit("}", 1)[-1]: v for k, v in elem.attrib.items()})
                    if elem.text and elem.text.strip():
                        row["text"] = elem.text.strip()
                    records.append(row)
    keywords = ("挤出", "热端", "喷嘴", "齿轮", "摆臂", "风扇", "风道", "气动", "TT")
    matches = [r for r in records if any(k.lower() in json.dumps(r, ensure_ascii=False).lower() for k in keywords)]
    return {
        "path": str(path),
        "package_file_count": len(package_names),
        "model_files": [n for n in package_names if n.lower().endswith(".model")],
        "record_count": len(records),
        "matches": matches,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    assembly = Path(sys.argv[1])
    three_mf = Path(sys.argv[2])
    step_dir = Path(sys.argv[3])
    result = {
        "assembly": inspect_assembly(assembly),
        "three_mf": inspect_3mf(three_mf),
        "step_files": sorted(p.name for p in step_dir.glob("*.STEP")),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
