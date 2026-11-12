"""Static GHX graph inspection. Never opens Rhino or executes embedded scripts."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zlib

from .errors import ConfigurationError


def inspect_ghx(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        raise ConfigurationError("GHX exceeds 32 MiB inspection limit")
    text = raw.decode("utf-8-sig")
    if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.I):
        raise ConfigurationError("DTD/entities are not accepted in GHX")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ConfigurationError(f"invalid GHX XML: {exc}") from exc
    objects = []
    ports = {}

    def items(chunk):
        return {item.get("name"): item.text or "" for item in chunk.findall("./items/item")
                if not list(item)}

    for obj in root.findall(".//chunk[@name='DefinitionObjects']/chunks/chunk[@name='Object']"):
        container = obj.find("./chunks/chunk[@name='Container']")
        if container is None:
            continue
        values = items(container)
        entry = {
            "index": int(obj.get("index", "-1")),
            "guid": values.get("InstanceGuid"),
            "type": values.get("Name"), "nickname": values.get("NickName"),
            "values": {k: v for k, v in values.items() if k in (
                "UserText", "ScriptSource", "CodeInput", "AdditionalSource",
                "Description", "Locked", "Expression",
            )},
            "ports": [],
            "scalars": [],
            "clusters": [],
        }
        if entry["guid"]:
            ports[entry["guid"]] = {"object_index": entry["index"], "port": "self"}
        for chunk in container.iter("chunk"):
            data = items(chunk)
            if "InstanceGuid" in data:
                sources = [i.text for i in chunk.findall("./items/item[@name='Source']")]
                port = {
                    "kind": chunk.get("name"), "index": chunk.get("index"),
                    "name": data.get("Name"), "guid": data["InstanceGuid"],
                    "sources": sources, "expression": data.get("Expression"),
                    "description": data.get("Description"),
                }
                entry["ports"].append(port)
                ports[port["guid"]] = {"object_index": entry["index"], "port": port["name"]}
            for item in chunk.findall("./items/item"):
                if item.get("name") in ("Value", "Expression") and not list(item):
                    value = item.text or ""
                    if len(value) < 500:
                        entry["scalars"].append({
                            "chunk": chunk.get("name"), "name": item.get("name"),
                            "type": item.get("type_name"), "value": value,
                        })
        for item in container.findall(".//item[@name='ClusterDocument']"):
            stream = item.find("stream")
            if stream is None:
                continue
            try:
                packed = base64.b64decode(re.sub(r"\s+", "", stream.text or ""), validate=True)
            except ValueError as exc:
                raise ConfigurationError("invalid cluster base64") from exc
            cluster = {"bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest(),
                       "executed": False, "binary_semantics_resolved": False}
            try:
                decoder = zlib.decompressobj(-15)
                decoded = decoder.decompress(packed, 8 * 1024 * 1024 + 1)
                if len(decoded) > 8 * 1024 * 1024 or not decoder.eof:
                    cluster["inspection_note"] = "compressed cluster exceeds limit or is incomplete"
                else:
                    # Strings are evidence snippets only, not a reconstruction of binary graph order.
                    strings = [
                        value.decode("utf-8", errors="replace")
                        for value in re.findall(rb"[\x20-\x7e\r\n\t]{5,}", decoded)
                    ]
                    cluster["decompressed_bytes"] = len(decoded)
                    cluster["string_evidence"] = strings
            except zlib.error:
                cluster["inspection_note"] = "cluster compression not recognized as raw DEFLATE"
            entry["clusters"].append(cluster)
        objects.append(entry)
    if not objects:
        raise ConfigurationError("no GHX DefinitionObjects found")
    for entry in objects:
        for port in entry["ports"]:
            port["upstream"] = [ports.get(guid, {"unresolved_guid": guid}) for guid in port["sources"]]
    return {
        "schema_version": 1, "offline_only": True, "live_supported": False,
        "filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
        "object_count": len(objects), "embedded_code_executed": False,
        "limitations": [
            "Graph metadata only, not a Grasshopper solution",
            "Cluster string evidence is not full binary graph reconstruction",
            "Saved GHX and historical G-code are not assumed to be a matched export",
        ],
        "objects": objects,
    }
