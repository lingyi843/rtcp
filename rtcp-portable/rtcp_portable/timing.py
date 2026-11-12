"""Offline rest-to-rest timing feasibility. No lookahead, step output or PA.

Every chord shares one normalized trapezoid across XYZUV/E and CoreXY A/B.
Stopping at EVERY chord is deliberately conservative and unsuitable as a final
printing planner. Bounds apply to the piecewise-linear approximation, not to an
unimplemented continuous interpolator.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .errors import ConfigurationError
from .geometry import Transform
from .models import Pose, exact_keys, number, pose_from_dict, pose_to_dict
from .path import subdivide

AXIS_NAMES = ("x", "y", "z", "u", "v", "e", "corexy_a", "corexy_b")


@dataclass(frozen=True)
class RateLimit:
    velocity: float
    acceleration: float

    def __post_init__(self):
        for key in ("velocity", "acceleration"):
            value = number(getattr(self, key), key)
            if value <= 0:
                raise ConfigurationError(f"{key} must be positive")
            object.__setattr__(self, key, value)


@dataclass(frozen=True)
class TimingLimits:
    axes: tuple[RateLimit, ...]

    def __post_init__(self):
        if len(self.axes) != len(AXIS_NAMES) or not all(isinstance(a, RateLimit) for a in self.axes):
            raise ConfigurationError("timing limits require XYZUV/E and CoreXY A/B limits")
        object.__setattr__(self, "axes", tuple(self.axes))


def limits_from_dict(raw: dict) -> TimingLimits:
    exact_keys(raw, {"schema_version", "purpose", "axes"}, "timing limits")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ConfigurationError("unsupported timing schema")
    if raw["purpose"] not in ("simulation", "calibrated_offline"):
        raise ConfigurationError("invalid timing purpose")
    values = exact_keys(raw["axes"], set(AXIS_NAMES), "timing axes")
    limits = []
    for name in AXIS_NAMES:
        item = exact_keys(values[name], {"velocity", "acceleration"}, name)
        limits.append(RateLimit(**item))
    return TimingLimits(tuple(limits))


def trapezoid(deltas: tuple[float, ...], limits: TimingLimits, command_min_seconds: float) -> dict:
    """Normalized displacement is 1; physical axis i displacement is deltas[i]."""
    command_min_seconds = number(command_min_seconds, "command_min_seconds")
    if command_min_seconds < 0 or len(deltas) != len(AXIS_NAMES):
        raise ConfigurationError("invalid timing inputs")
    magnitudes = tuple(abs(number(d, "axis delta")) for d in deltas)
    active = [(d, limit) for d, limit in zip(magnitudes, limits.axes) if d > 0]
    if not active:
        raise ConfigurationError("zero-motion timing block")
    vmax = min(limit.velocity / d for d, limit in active)
    accel = min(limit.acceleration / d for d, limit in active)
    if command_min_seconds > 0:
        vmax = min(vmax, 1 / command_min_seconds)
    vmax, accel = number(vmax, "normalized velocity"), number(accel, "normalized acceleration")
    if vmax <= 0 or accel <= 0:
        raise ConfigurationError("timing underflow")
    peak = min(vmax, math.sqrt(accel))
    ramp = peak / accel
    cruise = max(0.0, 1 / peak - ramp)
    duration = number(2 * ramp + cruise, "duration")
    return {
        "duration_s": duration, "accel_s": ramp, "cruise_s": cruise, "decel_s": ramp,
        "normalized_peak_velocity": peak, "normalized_acceleration": accel,
        "axis_peak_velocity": {k: number(d * peak, k) for k, d in zip(AXIS_NAMES, magnitudes)},
        "axis_acceleration": {k: number(d * accel, k) for k, d in zip(AXIS_NAMES, magnitudes)},
    }


def axis_deltas(start: Pose, end: Pose, e_delta: float) -> tuple[float, ...]:
    dx, dy, dz = (end.xyz - start.xyz).values()
    return dx, dy, dz, end.u - start.u, end.v - start.v, e_delta, dx + dy, dx - dy


def plan_job(transform: Transform, limits: TimingLimits, raw: dict) -> dict:
    """Consume a NEW explicit contract, never infer it from legacy G-code."""
    exact_keys(raw, {
        "schema_version", "coordinate_space", "angle_convention", "initial_pose", "events"
    }, "timed job")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 2:
        raise ConfigurationError("timed job requires schema_version=2")
    if raw["coordinate_space"] != "model_bed_zero":
        raise ConfigurationError("already transformed/unknown coordinates are forbidden")
    if raw["angle_convention"] != "rx_u_rz_v_controller_degrees":
        raise ConfigurationError("explicit Rx(U)Rz(V) angle convention required")
    current = pose_from_dict(raw["initial_pose"])
    transform.profile.check_pose(transform.forward(current))
    if not isinstance(raw["events"], list) or not 1 <= len(raw["events"]) <= 10000:
        raise ConfigurationError("job requires 1..10000 explicit events")
    result, elapsed, cumulative_e = [], 0.0, 0.0
    for index, event in enumerate(raw["events"]):
        if not isinstance(event, dict):
            raise ConfigurationError("event must be an object")
        kind = event.get("kind")
        if kind == "move":
            exact_keys(event, {"kind", "target", "e_delta_mm", "tcp_feed_mm_min"}, "move event")
            target = pose_from_dict(event["target"])
            e_delta = number(event["e_delta_mm"], "E delta")
            metric = (target.xyz - current.xyz).norm()
            feed = number(event["tcp_feed_mm_min"], "TCP feed")
            if metric == 0:
                raise ConfigurationError("zero model-length move: use orient/extrude event")
        elif kind == "orient":
            exact_keys(event, {"kind", "u_deg", "v_deg", "angular_feed_deg_min"}, "orient event")
            target = Pose(current.xyz, event["u_deg"], event["v_deg"])
            e_delta = 0.0
            metric = max(abs(target.u - current.u), abs(target.v - current.v))
            feed = number(event["angular_feed_deg_min"], "max-axis angular feed")
        elif kind == "extrude":
            exact_keys(event, {"kind", "e_delta_mm", "filament_feed_mm_min"}, "extrude event")
            target = current
            e_delta = number(event["e_delta_mm"], "E delta")
            metric = abs(e_delta)
            feed = number(event["filament_feed_mm_min"], "filament feed")
        else:
            raise ConfigurationError("unsupported event; thermal/macros/mode changes cannot pass through")
        if metric <= 0 or feed <= 0:
            raise ConfigurationError("event metric and feed must be positive")
        path = subdivide(transform, current, target)
        if len(result) + len(path.nodes) - 1 > transform.profile.max_segments:
            raise ConfigurationError("whole timed-job segment budget exceeded")
        used_e = 0.0
        event_e_start = cumulative_e
        for segment, (a, b) in enumerate(zip(path.nodes, path.nodes[1:])):
            last = segment == len(path.nodes) - 2
            piece_e = e_delta - used_e if last else e_delta * (b.t - a.t)
            piece_e = number(piece_e, "subsegment E")
            used_e += piece_e
            timing = trapezoid(
                axis_deltas(a.physical, b.physical, piece_e), limits,
                number(metric * (b.t - a.t) * 60 / feed, "command duration"),
            )
            cumulative_e = number(event_e_start + used_e, "cumulative E")
            result.append({
                "event": index, "kind": kind, "t0": a.t, "t1": b.t,
                "start_time_s": elapsed, "timing": timing,
                "logical_start": pose_to_dict(a.logical), "logical_end": pose_to_dict(b.logical),
                "physical_start": pose_to_dict(a.physical), "physical_end": pose_to_dict(b.physical),
                "e_delta_mm": piece_e, "cumulative_e_mm": cumulative_e,
                "chord_error_bound_mm": path.segment_error_bounds_mm[segment],
            })
            elapsed = number(elapsed + timing["duration_s"], "total duration")
        current = target
    return {
        "schema_version": 2, "offline_only": True, "live_supported": False,
        "executable_gcode": False, "timing_model": "rest_to_rest_every_chord",
        "duration_s": elapsed, "net_e_mm": cumulative_e, "segment_count": len(result),
        "machine_id": transform.profile.machine_id, "purpose": transform.profile.purpose,
        "segments": result,
        "limitations": [
            "No lookahead, pressure advance, thermal checks, collision checking or MCU submission",
            "Stops at every chord: feasibility reference, not production-quality continuous printing",
            "CoreXY A/B displacement convention is dx+dy / dx-dy in motor-equivalent mm",
            "All axes share a normalized trapezoid; no claim of physical-machine verification",
        ],
    }
