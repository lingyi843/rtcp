"""JSON diagnostics only. No G-code emitter or printer connection options."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import __version__
from .audit import audit_snapshot
from .capture import inspect_capture
from .errors import ConfigurationError, RTCPError
from .geometry import Transform
from .gcode import audit_gcode
from .ghx import inspect_ghx
from .models import (
    Registration, exact_keys, pose_from_dict, pose_to_dict, profile_from_dict, vector,
)
from .path import subdivide
from .selfcheck import run as selfcheck
from .timing import limits_from_dict, plan_job


def _pairs(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> tuple[object, str]:
    with path.open("rb") as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ConfigurationError("input exceeds 16 MiB offline limit")

    def reject_constant(value: str) -> None:
        raise ConfigurationError(f"non-finite JSON constant: {value}")

    return (
        json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=reject_constant),
        hashlib.sha256(raw).hexdigest(),
    )


def simulate(profile_path: Path, job_path: Path) -> dict:
    profile_data, profile_hash = read_json(profile_path)
    profile = profile_from_dict(profile_data)
    job, job_hash = read_json(job_path)
    exact_keys(job, {"schema_version", "registration", "points"}, "job")
    if type(job["schema_version"]) is not int or job["schema_version"] != 1:
        raise ConfigurationError("unsupported job schema_version")
    registration = exact_keys(job["registration"], {"offset_mm", "frame"}, "registration")
    if registration["frame"] != "bed_zero_pose":
        raise ConfigurationError("only bed_zero_pose registration is supported")
    points = job["points"]
    if not isinstance(points, list) or not 2 <= len(points) <= 10000:
        raise ConfigurationError("job requires 2..10000 explicit XYZUV points")
    poses = [pose_from_dict(point) for point in points]
    transform = Transform(profile, Registration(vector(registration["offset_mm"], "offset_mm")))
    blocks = []
    total_segments = 0
    for start, end in zip(poses, poses[1:]):
        path = subdivide(transform, start, end)
        total_segments += len(path.nodes) - 1
        if total_segments > profile.max_segments:
            raise ConfigurationError("whole-job segment budget exceeded")
        blocks.append({
            "max_error_bound_mm": path.max_error_bound_mm,
            "segment_error_bounds_mm": path.segment_error_bounds_mm,
            "nodes": [
                {"t": n.t, "logical": pose_to_dict(n.logical), "physical": pose_to_dict(n.physical)}
                for n in path.nodes
            ],
        })
    return {
        "schema_version": 1, "version": __version__, "offline_only": True,
        "live_supported": False, "executable_gcode": False,
        "machine_id": profile.machine_id, "purpose": profile.purpose,
        "profile_sha256": profile_hash, "job_sha256": job_hash,
        "segment_count": total_segments,
        "max_error_bound_mm": max(block["max_error_bound_mm"] for block in blocks),
        "limitations": [
            "Geometric XYZUV only; no E, feedrate, acceleration, lookahead or pressure advance",
            "Axis bounds are not collision detection or mechanical safety certification",
            "Common-pivot Rx(U)Rz(V), translation-only registration",
            "No machine reference validation; this is an offline path file",
        ],
        "blocks": blocks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="strictly validate an offline machine profile")
    validate.add_argument("profile", type=Path)
    sim = sub.add_parser("simulate", help="generate non-executable geometric JSON")
    sim.add_argument("profile", type=Path)
    sim.add_argument("job", type=Path)
    audit = sub.add_parser("audit-snapshot", help="lint previously downloaded files, without importing them")
    audit.add_argument("snapshot", type=Path)
    check = sub.add_parser("selfcheck", help="run installed-package synthetic smoke checks")
    gcode = sub.add_parser("audit-gcode", help="non-executing audit; never assumes model-space coordinates")
    gcode.add_argument("file", type=Path)
    ghx = sub.add_parser("inspect-ghx", help="static XML graph inspection; never solves Grasshopper")
    ghx.add_argument("file", type=Path)
    capture = sub.add_parser("inspect-capture", help="validate a new pre-IK plane-tree capture")
    capture.add_argument("file", type=Path)
    timed = sub.add_parser("plan-timing", help="offline rest-to-rest XYZUV/E timing, NOT production G-code")
    timed.add_argument("profile", type=Path)
    timed.add_argument("limits", type=Path)
    timed.add_argument("job", type=Path)
    timed.add_argument("--offset", type=float, nargs=3, required=True, metavar=("DX", "DY", "DZ"))
    for command in (validate, sim, audit, check, gcode, ghx, capture, timed):
        command.add_argument("--output", type=Path, help="create a NEW report; refuses overwrite")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            data, digest = read_json(args.profile)
            profile = profile_from_dict(data)
            result = {
                "valid": True, "machine_id": profile.machine_id, "purpose": profile.purpose,
                "offline_only": True, "live_supported": False, "profile_sha256": digest,
            }
        elif args.command == "simulate":
            result = simulate(args.profile, args.job)
        elif args.command == "audit-snapshot":
            result = audit_snapshot(args.snapshot)
        elif args.command == "audit-gcode":
            result = audit_gcode(args.file)
        elif args.command == "inspect-ghx":
            result = inspect_ghx(args.file)
        elif args.command == "inspect-capture":
            data, digest = read_json(args.file)
            result = inspect_capture(data)
            result["capture_sha256"] = digest
        elif args.command == "plan-timing":
            profile_data, profile_hash = read_json(args.profile)
            timing_data, timing_hash = read_json(args.limits)
            job_data, job_hash = read_json(args.job)
            transform = Transform(profile_from_dict(profile_data), Registration(vector(args.offset, "offset")))
            result = plan_job(transform, limits_from_dict(timing_data), job_data)
            result.update(profile_sha256=profile_hash, timing_sha256=timing_hash,
                          job_sha256=job_hash, registration_offset_mm=args.offset)
        else:
            result = selfcheck()
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(output)
        else:
            print(output, end="")
        return 0
    except (RTCPError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"offline RTCP rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
