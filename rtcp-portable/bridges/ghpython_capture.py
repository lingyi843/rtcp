"""Paste into a NEW GhPython component, not the original exporter.

Inputs P,L,I,T: Tree access; respectively pre-IK planes (relay 112), segment
lengths (113), path-changing indices (116), travel lengths (117).
Input units: Item access, explicit string "mm".
Outputs capture_json, status. This script DOES NOT write files or send commands.
GH data wrappers are unwrapped, but no expressions/scripts are evaluated.
"""
import json
import math


def scalar(value):
    value = value.Value if hasattr(value, "Value") else value
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric stream value")
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("non-finite stream value")
    return value


def tree_rows(tree, convert):
    if not hasattr(tree, "Branches") or not hasattr(tree, "Paths"):
        raise ValueError("P/L/I/T must all use Tree access; do not flatten")
    rows = []
    for index, branch in enumerate(tree.Branches):
        path = [int(i) for i in tree.Paths[index].Indices]
        rows.append({"path": path, "items": [convert(item) for item in branch]})
    return rows


def plane_record(value):
    plane = value.Value if hasattr(value, "Value") else value
    origin, normal = plane.Origin, plane.ZAxis
    return {
        "xyz_mm": [scalar(origin.X), scalar(origin.Y), scalar(origin.Z)],
        "normal": [scalar(normal.X), scalar(normal.Y), scalar(normal.Z)],
    }


def index_record(value):
    value = scalar(value)
    if value < 0 or int(value) != value:
        raise ValueError("path-change index must be a nonnegative integer")
    return int(value)


def capture(planes, lengths, changes, travel, unit_name):
    if unit_name != "mm":
        raise ValueError("Confirm Rhino model units are mm and set units='mm'")
    data = {
        "schema_version": 1,
        "format": "open5x_pre_ik_capture",
        "coordinate_space": "model_bed_zero",
        "units": "mm",
        "planes": tree_rows(planes, plane_record),
        "segment_lengths": tree_rows(lengths, scalar),
        "path_change_indices": tree_rows(changes, index_record),
        "travel_lengths": tree_rows(travel, scalar),
        "alignment_confirmed": False,
    }
    return json.dumps(data, ensure_ascii=True, allow_nan=False, indent=2)


# The guard permits importing this authored helper in plain Python tests.
# The supplied user GHX scripts are NEVER imported by the tests.
if all(name in globals() for name in ("P", "L", "I", "T", "units")):
    try:
        capture_json = capture(P, L, I, T, units)
        status = "OFFLINE capture only; stream alignment and tool-normal sign still need verification"
    except (ValueError, AttributeError, TypeError) as error:
        capture_json = ""
        status = "REJECTED: " + str(error)
