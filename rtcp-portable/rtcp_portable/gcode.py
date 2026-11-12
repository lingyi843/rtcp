"""Non-executing modal audit. It intentionally cannot turn legacy code into RTCP."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re

from .errors import ConfigurationError
from .models import number

TOKEN = re.compile(r"([A-Za-z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
COMMAND = re.compile(r"^\s*([GM])\s*(\d+)(?![\d.])", re.I)
AXES = "XYZUV"


def strip_comments(line: str) -> str:
    result, depth, quoted = [], 0, False
    for char in line:
        if char == '"' and depth == 0:
            quoted = not quoted
        if not quoted:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
                continue
            if char == ")":
                if depth == 0:
                    raise ConfigurationError("unmatched ')' comment")
                depth -= 1
                continue
        if depth == 0:
            result.append(char)
    if quoted or depth:
        raise ConfigurationError("unterminated quote/comment")
    return "".join(result).strip()


def words(text: str) -> dict[str, float]:
    result = {}
    end = 0
    for match in TOKEN.finditer(text):
        if text[end:match.start()].strip():
            raise ConfigurationError("unsupported token/expression")
        key = match.group(1).upper()
        if key in result:
            raise ConfigurationError(f"duplicate word {key}")
        result[key] = number(float(match.group(2)), key)
        end = match.end()
    if text[end:].strip():
        raise ConfigurationError("unsupported token/expression/checksum")
    return result


def analyze_gcode(text: str) -> dict:
    """Independent XYZ/E modes; unknown commands invalidate all inferred state.

    This is an explicit audit dialect, not a promise that arbitrary historical
    firmware uses identical semantics. No initial position/unit/feed is guessed.
    """
    position = dict.fromkeys(AXES)
    absolute = extrusion_absolute = units = feed = extrusion = None
    counts, issues, motions, external = Counter(), [], [], []
    lexical_values = {axis: [] for axis in AXES + "EF"}
    maximum_issue_examples = 100
    issue_counts = Counter()

    def issue(code, line, message):
        issue_counts[code] += 1
        if len(issues) < maximum_issue_examples:
            issues.append({"code": code, "line": line, "message": message})

    def invalidate():
        nonlocal absolute, extrusion_absolute, units, feed, extrusion
        absolute = extrusion_absolute = units = feed = extrusion = None
        for axis in AXES:
            position[axis] = None

    for line_number, original in enumerate(text.splitlines(), 1):
        if len(original) > 16384:
            raise ConfigurationError(f"line {line_number} exceeds audit size limit")
        try:
            code = strip_comments(original)
        except ConfigurationError as exc:
            issue("syntax", line_number, str(exc))
            invalidate()
            continue
        if not code:
            continue
        match = COMMAND.match(code)
        if match is None:
            issue("unsupported_command", line_number, code[:200])
            external.append({"line": line_number, "text": code[:500]})
            invalidate()
            continue
        command = match.group(1).upper() + str(int(match.group(2)))
        counts[command] += 1
        remainder = code[match.end():]
        if command == "M98":
            external.append({"line": line_number, "text": code})
            issue("external_macro", line_number, "Macro body unknown; all modal/position state invalidated")
            invalidate()
            continue
        try:
            params = words(remainder)
            allowed = {
                "G0": set(AXES + "EF"), "G1": set(AXES + "EF"), "G92": set(AXES + "E"),
                "G90": set(), "G91": set(), "G21": set(), "G20": set(),
                "M82": set(), "M83": set(),
                "M104": {"S", "T"}, "M109": {"S", "R", "T"}, "M140": {"S"},
                "M190": {"S", "R"}, "M106": {"S", "P"}, "M107": set(), "M400": set(),
            }.get(command)
            if allowed is None or set(params) - allowed:
                raise ConfigurationError(f"unsupported command/fields: {command}")
        except ConfigurationError as exc:
            issue("syntax_or_unsupported", line_number, str(exc))
            invalidate()
            continue
        if command == "G90":
            absolute = True
        elif command == "G91":
            absolute = False
        elif command == "M82":
            extrusion_absolute = True
        elif command == "M83":
            extrusion_absolute = False
        elif command == "G21":
            units = "mm"
        elif command == "G20":
            units = "inch"
            issue("inch_not_supported", line_number, "No implicit inch conversion")
        elif command == "G92":
            issue("coordinate_relabel", line_number, "G92 is not homing or mechanical reference establishment")
            for axis, value in params.items():
                if axis == "E":
                    extrusion = value if units == "mm" else None
                else:
                    position[axis] = value if units == "mm" else None
        elif command in ("G0", "G1"):
            for key, value in params.items():
                if key in lexical_values:
                    lexical_values[key].append(value)
            if "F" in params:
                if params["F"] <= 0:
                    issue("invalid_feed", line_number, "F must be positive")
                    feed = None
                else:
                    feed = params["F"]
            start = position.copy()
            reasons = []
            if units != "mm":
                reasons.append("units_unknown_or_not_mm")
            if absolute is None and any(axis in params for axis in AXES):
                reasons.append("distance_mode_unknown")
            for axis in AXES:
                if axis in params:
                    if units != "mm" or absolute is None:
                        position[axis] = None
                    elif absolute:
                        position[axis] = params[axis]
                    elif position[axis] is not None:
                        position[axis] = number(position[axis] + params[axis], axis)
            delta_e = 0.0
            if "E" in params:
                if units != "mm" or extrusion_absolute is None:
                    delta_e, extrusion = None, None
                    reasons.append("extrusion_mode_or_units_unknown")
                elif extrusion_absolute:
                    delta_e = None if extrusion is None else number(params["E"] - extrusion, "E delta")
                    extrusion = params["E"]
                    if delta_e is None:
                        reasons.append("extrusion_start_unknown")
                else:
                    delta_e = params["E"]
                    extrusion = None if extrusion is None else number(extrusion + delta_e, "E")
            if any(value is None for value in start.values()):
                reasons.append("start_pose_unknown")
            if any(value is None for value in position.values()):
                reasons.append("end_pose_unknown")
            if feed is None:
                reasons.append("feed_unknown")
            motions.append({
                "line": line_number, "command": command, "words": params,
                "start": start, "end": position.copy(), "e_delta_mm": delta_e,
                "feed_word": feed, "unresolved": reasons,
            })
        # Known thermal/fan/wait words are recorded in counts only, NEVER executed.
    ranges = {
        key: {"minimum": min(values), "maximum": max(values), "count": len(values)}
        for key, values in lexical_values.items() if values
    }
    spatial = [move for move in motions if all(a in move["words"] for a in AXES)]
    xy_zero = sum(move["words"]["X"] == 0 and move["words"]["Y"] == 0 for move in spatial)
    if spatial and xy_zero / len(spatial) > .95:
        issue("possible_post_ik_coordinates", spatial[0]["line"],
              "Most explicit XYZUV records have X=Y=0; do not assume model-space coordinates")
    return {
        "schema_version": 1, "offline_only": True, "live_supported": False,
        "automatic_rtcp_import_allowed": False,
        "audit_dialect": "explicit independent XYZ/E modes; unsupported commands invalidate state",
        "line_count": len(text.splitlines()), "command_counts": dict(counts),
        "motion_count": len(motions), "raw_word_ranges": ranges,
        "explicit_xyzuv_count": len(spatial), "explicit_xyzuv_xy_zero_count": xy_zero,
        "motion_records_with_unresolved_state": sum(bool(m["unresolved"]) for m in motions),
        "known_signed_e_sum_mm": sum(m["e_delta_mm"] for m in motions if m["e_delta_mm"] is not None),
        "unknown_e_delta_count": sum(m["e_delta_mm"] is None for m in motions),
        "issue_counts": dict(issue_counts), "issue_examples": issues,
        "external_commands": external, "motions": motions,
        "limitations": [
            "Raw word ranges are lexical, not certified physical axis travel",
            "Unknown macro side effects are not silently assumed away",
            "Feed words have no certified TCP meaning; no duration is inferred",
        ],
    }


def audit_gcode(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        raise ConfigurationError("G-code exceeds 32 MiB audit limit")
    report = analyze_gcode(raw.decode("utf-8-sig"))
    moves = report.pop("motions")
    report["motion_examples"] = moves[:3] + moves[-3:]
    report["filename"] = path.name
    report["sha256"] = hashlib.sha256(raw).hexdigest()
    return report
