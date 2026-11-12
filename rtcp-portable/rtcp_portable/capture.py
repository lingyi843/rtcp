"""Validate the GH pre-IK capture, preserving branch/index provenance."""
from __future__ import annotations

from .errors import ConfigurationError
from .models import exact_keys, number, vector


def inspect_capture(data: dict) -> dict:
    exact_keys(data, {
        "schema_version", "format", "coordinate_space", "units", "planes",
        "segment_lengths", "path_change_indices", "travel_lengths", "alignment_confirmed",
    }, "pre-IK capture")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigurationError("unsupported capture schema")
    if (
        data["format"] != "open5x_pre_ik_capture" or data["units"] != "mm"
        or data["coordinate_space"] != "model_bed_zero"
        or data["alignment_confirmed"] is not False
    ):
        raise ConfigurationError("capture must declare unverified pre-IK model-space millimetres")
    counts, paths, ranges = {}, {}, {a: [] for a in "xyz"}
    for stream in ("planes", "segment_lengths", "path_change_indices", "travel_lengths"):
        rows = data[stream]
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ConfigurationError("invalid capture branches")
        seen, count = set(), 0
        for row in rows:
            exact_keys(row, {"path", "items"}, "tree branch")
            if not isinstance(row["path"], list) or not all(type(i) is int for i in row["path"]):
                raise ConfigurationError("tree path must be integer array")
            key = tuple(row["path"])
            if key in seen:
                raise ConfigurationError("duplicate tree branch path")
            seen.add(key)
            if not isinstance(row["items"], list):
                raise ConfigurationError("tree branch items must be an array")
            count += len(row["items"])
            if count > 100000:
                raise ConfigurationError("capture stream item budget exceeded")
            for item in row["items"]:
                if stream == "planes":
                    exact_keys(item, {"xyz_mm", "normal"}, "plane")
                    point, normal = vector(item["xyz_mm"], "origin"), vector(item["normal"], "normal")
                    if number(normal.norm(), "normal length") < 1e-15:
                        raise ConfigurationError("zero plane normal")
                    for axis, value in zip("xyz", point.values()):
                        ranges[axis].append(value)
                elif stream == "path_change_indices":
                    if type(item) is not int or item < 0:
                        raise ConfigurationError("path-change index must be nonnegative integer")
                elif number(item, stream) < 0:
                    raise ConfigurationError("negative path length")
        counts[stream] = count
        paths[stream] = [list(key) for key in sorted(seen)]
    if counts["planes"] < 2:
        raise ConfigurationError("capture needs at least two planes")
    return {
        "offline_only": True, "live_supported": False,
        "capture_valid": True, "automatic_job_conversion_allowed": False,
        "counts": counts, "branch_paths": paths,
        "model_ranges_mm": {axis: [min(values), max(values)] for axis, values in ranges.items()},
        "remaining_checks": [
            "Confirm plane origins are model points before old inverse kinematics",
            "Confirm plane Z axis points outward toward nozzle holder (+Z alignment convention)",
            "Verify per-branch point/segment/E and path-change index alignment",
            "Choose explicit TCP speed and extrusion settings; do not reuse compensated legacy F",
        ],
    }
