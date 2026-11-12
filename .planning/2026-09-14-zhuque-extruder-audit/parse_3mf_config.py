import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def metadata_map(element):
    return {
        child.attrib.get("key"): child.attrib.get("value", (child.text or "").strip())
        for child in element
        if child.tag.rsplit("}", 1)[-1] == "metadata"
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1])
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("Metadata/model_settings.config"))

    objects = {}
    for obj in root.findall("object"):
        meta = metadata_map(obj)
        parts = []
        for part in obj.findall("part"):
            pm = metadata_map(part)
            parts.append({"id": part.attrib.get("id"), "subtype": part.attrib.get("subtype"), **pm})
        objects[obj.attrib["id"]] = {"id": obj.attrib["id"], **meta, "parts": parts}

    plates = []
    for plate in root.findall("plate"):
        meta = metadata_map(plate)
        ids = []
        for inst in plate.findall("model_instance"):
            im = metadata_map(inst)
            if "object_id" in im:
                ids.append(im["object_id"])
        plates.append({**meta, "object_ids": ids})

    keywords = ("挤出", "热端", "喷嘴", "齿轮", "摆臂", "风扇", "风道", "气动")
    output = []
    for object_id, obj in objects.items():
        text = json.dumps(obj, ensure_ascii=False)
        if not any(k in text for k in keywords):
            continue
        plate_names = [p.get("plater_name") for p in plates if object_id in p["object_ids"]]
        output.append({"object": obj, "plates": plate_names})
    print(json.dumps({"matches": output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
