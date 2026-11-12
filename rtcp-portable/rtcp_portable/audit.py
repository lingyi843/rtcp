"""Read-only static lint of a previously downloaded snapshot. Never imports it.

These are narrow compatibility checks, NOT a live status check or a general
Klipper configuration/include resolver. A clean lint is never deployment approval.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re

from .errors import ConfigurationError


def audit_snapshot(root: Path) -> dict:
    files = {
        name: root / "source" / name
        for name in ("corexy_uv.py", "toolhead.py", "force_move.py", "laser_motion.py")
    }
    files["machine_functions.cfg"] = root / "config" / "machine_functions.cfg"
    final_config = root / "config_final" / "printer.cfg"
    files["printer.cfg"] = final_config if final_config.is_file() else root / "config" / "printer.cfg"
    text: dict[str, str] = {}
    hashes = {}
    for name, path in files.items():
        if not path.is_file():
            raise ConfigurationError(f"snapshot missing {path}")
        raw = path.read_bytes()
        hashes[str(path.relative_to(root)).replace("\\", "/")] = hashlib.sha256(raw).hexdigest()
        text[name] = raw.decode("utf-8-sig")
    trees = {}
    for name, source in text.items():
        if name.endswith(".py"):
            try:
                trees[name] = ast.parse(source, filename=name)
            except SyntaxError as exc:
                raise ConfigurationError(f"cannot statically parse {name}: {exc}") from exc

    def definitions(name: str) -> set[str]:
        return {
            node.name for node in ast.walk(trees[name])
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    issues: list[dict] = []

    def issue(code: str, message: str, name: str, marker: str) -> None:
        lines = [i for i, line in enumerate(text[name].splitlines(), 1) if marker in line]
        issues.append({"code": code, "message": message, "file": name, "lines": lines})

    if (
        "set_extra_axis_position(" in text["corexy_uv.py"]
        and "set_extra_axis_position" not in definitions("toolhead.py")
    ):
        issue("missing_reference_host_method",
              "Rotary reference calls a method not defined in this toolhead snapshot.",
              "corexy_uv.py", "set_extra_axis_position(")
    reference_calls = [
        node for tree in trees.values() for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_reference"
    ]
    if "set_reference" in definitions("corexy_uv.py") and not reference_calls:
        issue("no_reference_caller_in_scanned_sources",
              "No set_reference caller in the four scanned Python files; inspect integration.",
              "corexy_uv.py", "def set_reference")
    macro = text["machine_functions.cfg"]
    if re.search(r"SET_KINEMATIC_POSITION\s+[UV]=", macro):
        issue("uv_reference_macro_requires_verification",
              "SET_U/V use SET_KINEMATIC_POSITION; check the installed parser supports UV.",
              "machine_functions.cfg", "SET_KINEMATIC_POSITION")
    checks = [
        node for node in ast.walk(trees["corexy_uv.py"])
        if isinstance(node, ast.FunctionDef) and node.name == "check_move"
    ]
    check_text = "\n".join(ast.get_source_segment(text["corexy_uv.py"], node) or "" for node in checks)
    if checks and not any(marker in check_text for marker in ("position_min", "position_max", "limits")):
        issue("rotary_range_guard_not_found",
              "No recognized min/max angle guard in check_move; heuristic, not a proof of absence.",
              "corexy_uv.py", "def check_move")
    if "manual_stepper " in text["laser_motion.py"]:
        issue("legacy_laser_manual_stepper",
              "Laser module still looks up manual_stepper; native rotary compatibility needs review.",
              "laser_motion.py", "manual_stepper ")
    if (
        "move_generation" in text["laser_motion.py"]
        and "move_generation" not in text["toolhead.py"]
    ):
        issue("legacy_laser_generation",
              "Laser module expects move_generation absent from this toolhead source.",
              "laser_motion.py", "move_generation")
    section = re.search(
        r"(?ms)^\[stepper_u\]\s*\n(.*?)(?=^\[|\Z)", text["printer.cfg"]
    )
    gear = None
    if section:
        match = re.search(r"(?m)^\s*gear_ratio\s*:\s*([^#\n]+)", section.group(1))
        if match:
            gear = match.group(1).strip()
    try:
        driven, driving = (float(v) for v in (gear or "").split(":"))
        matches = driving > 0 and abs(driven / driving - 260 / 18) < 1e-9
    except ValueError:
        matches = False
    if not matches:
        issue("u_gear_mismatch_or_unknown",
              f"Snapshot U gear={gear!r}; requested hardware ratio is 260:18. No file changed.",
              "printer.cfg", "gear_ratio")
    return {
        "schema_version": 1,
        "offline_only": True,
        "live_supported": False,
        "deployment_ready": False,
        "scope": "Static lint of supplied local files, not current machine state or include resolution",
        "sha256": hashes,
        "observed_u_gear": gear,
        "issues": issues,
    }
