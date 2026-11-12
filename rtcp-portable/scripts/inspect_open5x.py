"""Static GHX inspection helper; creates a new JSON report without running code."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rtcp_portable.ghx import inspect_ghx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("ghx", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
report = inspect_ghx(args.ghx)
with args.output.open("x", encoding="utf-8") as output:
    json.dump(report, output, ensure_ascii=False, indent=2)
for obj in report["objects"]:
    if obj["type"] == "Group":
        continue
    print(json.dumps({
        "index": obj["index"], "type": obj["type"], "nickname": obj["nickname"],
        "text": obj["values"].get("UserText", "")[:120],
        "inputs": [{"name": p["name"], "from": p["upstream"]}
                   for p in obj["ports"] if p["sources"]],
        "clusters": [{k: v for k, v in c.items() if k != "string_evidence"} for c in obj["clusters"]],
    }, ensure_ascii=True))
