"""Immutable offline contracts. Millimetres and platform degrees, never steps."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .errors import ConfigurationError, LimitError


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label}: expected a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ConfigurationError(f"{label}: expected a finite number") from exc
    if not math.isfinite(result):
        raise ConfigurationError(f"{label}: expected a finite number")
    return result


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for name in ("x", "y", "z"):
            object.__setattr__(self, name, number(getattr(self, name), name))

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scaled(self, factor: float) -> Vec3:
        factor = number(factor, "scale")
        return Vec3(self.x * factor, self.y * factor, self.z * factor)

    def norm(self) -> float:
        return math.hypot(self.x, self.y, self.z)

    def values(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


@dataclass(frozen=True)
class Pose:
    xyz: Vec3
    u: float
    v: float

    def __post_init__(self) -> None:
        if not isinstance(self.xyz, Vec3):
            raise ConfigurationError("xyz must be Vec3")
        object.__setattr__(self, "u", number(self.u, "U"))
        object.__setattr__(self, "v", number(self.v, "V"))

    def interpolate(self, other: Pose, t: float) -> Pose:
        t = number(t, "interpolation parameter")
        if not 0 <= t <= 1:
            raise ConfigurationError("interpolation parameter must lie in [0, 1]")
        # Convex sums avoid overflow of b-a for opposite extreme values.
        return Pose(
            self.xyz.scaled(1 - t) + other.xyz.scaled(t),
            self.u * (1 - t) + other.u * t,
            self.v * (1 - t) + other.v * t,
        )


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "low", number(self.low, "limit.low"))
        object.__setattr__(self, "high", number(self.high, "limit.high"))
        if self.low >= self.high:
            raise ConfigurationError("limit.low must be less than limit.high")

    def check(self, value: float, label: str) -> None:
        value = number(value, label)
        if not self.low <= value <= self.high:
            raise LimitError(f"{label}={value:g} outside [{self.low:g}, {self.high:g}]")


@dataclass(frozen=True)
class Rotary:
    sign: int
    zero_deg: float
    limits_deg: Interval
    gear_ratio: tuple[float, float]

    def __post_init__(self) -> None:
        if type(self.sign) is not int or self.sign not in (-1, 1):
            raise ConfigurationError("rotary sign must be integer +1 or -1")
        object.__setattr__(self, "zero_deg", number(self.zero_deg, "zero_deg"))
        if not isinstance(self.limits_deg, Interval):
            raise ConfigurationError("limits_deg must be Interval")
        self.limits_deg.check(self.zero_deg, "zero_deg")
        if not isinstance(self.gear_ratio, (tuple, list)) or len(self.gear_ratio) != 2:
            raise ConfigurationError("gear_ratio must contain driven and driving teeth")
        gear = tuple(number(v, "gear_ratio") for v in self.gear_ratio)
        if min(gear) <= 0:
            raise ConfigurationError("gear_ratio entries must be positive")
        object.__setattr__(self, "gear_ratio", gear)

    def radians(self, controller_deg: float) -> float:
        angle = self.sign * (number(controller_deg, "angle") - self.zero_deg)
        return math.radians(number(angle, "relative angle"))


@dataclass(frozen=True)
class Profile:
    machine_id: str
    purpose: str
    pivot_mm: Vec3
    u: Rotary
    v: Rotary
    xyz_limits_mm: tuple[Interval, Interval, Interval]
    chord_tolerance_mm: float = 0.02
    max_depth: int = 20
    max_segments: int = 100000

    def __post_init__(self) -> None:
        if not isinstance(self.machine_id, str) or not self.machine_id.strip():
            raise ConfigurationError("machine_id must be nonempty")
        if self.purpose not in ("simulation", "calibrated_offline"):
            raise ConfigurationError("purpose must be simulation or calibrated_offline")
        if not isinstance(self.pivot_mm, Vec3):
            raise ConfigurationError("pivot_mm must be Vec3")
        if not isinstance(self.u, Rotary) or not isinstance(self.v, Rotary):
            raise ConfigurationError("U/V must be Rotary")
        if not isinstance(self.xyz_limits_mm, (tuple, list)):
            raise ConfigurationError("xyz_limits_mm must contain three Intervals")
        if len(self.xyz_limits_mm) != 3 or not all(
            isinstance(v, Interval) for v in self.xyz_limits_mm
        ):
            raise ConfigurationError("xyz_limits_mm must contain three Intervals")
        object.__setattr__(self, "xyz_limits_mm", tuple(self.xyz_limits_mm))
        tolerance = number(self.chord_tolerance_mm, "chord_tolerance_mm")
        if tolerance <= 0:
            raise ConfigurationError("chord_tolerance_mm must be positive")
        object.__setattr__(self, "chord_tolerance_mm", tolerance)
        for name, minimum, maximum in (
            ("max_depth", 1, 24), ("max_segments", 1, 1000000)
        ):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ConfigurationError(f"{name} must be an integer in [{minimum}, {maximum}]")

    def check_pose(self, physical: Pose) -> None:
        for label, value, limit in zip("XYZ", physical.xyz.values(), self.xyz_limits_mm):
            limit.check(value, label)
        self.u.limits_deg.check(physical.u, "U")
        self.v.limits_deg.check(physical.v, "V")


@dataclass(frozen=True)
class Registration:
    """Translation in the bed zero-pose axes, relative to actual common pivot.

    It is NOT a machine-frame translation added after rotation. dz=0 is explicit,
    never inferred from a 2D observation made with a tilted bed.
    """

    offset_mm: Vec3

    def __post_init__(self) -> None:
        if not isinstance(self.offset_mm, Vec3):
            raise ConfigurationError("offset_mm must be Vec3")


def exact_keys(data: Any, keys: set[str], label: str) -> dict:
    if not isinstance(data, dict) or set(data) != keys:
        actual = set(data) if isinstance(data, dict) else set()
        raise ConfigurationError(
            f"{label}: fields mismatch; missing={sorted(keys-actual)}, "
            f"unexpected={sorted(actual-keys)}"
        )
    return data


def vector(data: Any, label: str) -> Vec3:
    if not isinstance(data, (list, tuple)) or len(data) != 3:
        raise ConfigurationError(f"{label}: expected three finite coordinates")
    return Vec3(*data)


def interval(data: Any) -> Interval:
    if not isinstance(data, (list, tuple)) or len(data) != 2:
        raise ConfigurationError("limits must be [minimum, maximum]")
    return Interval(*data)


def profile_from_dict(data: Any) -> Profile:
    exact_keys(data, {
        "schema_version", "machine_id", "purpose", "geometry", "pivot_mm",
        "u", "v", "xyz_limits_mm", "path",
    }, "profile")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigurationError("unsupported profile schema_version")
    if data["geometry"] != "common_pivot_rx_u_rz_v":
        raise ConfigurationError("only common_pivot_rx_u_rz_v is implemented")

    def rotary(raw: Any) -> Rotary:
        exact_keys(raw, {"sign", "zero_deg", "limits_deg", "gear_ratio"}, "rotary")
        return Rotary(raw["sign"], raw["zero_deg"], interval(raw["limits_deg"]), raw["gear_ratio"])

    limits = exact_keys(data["xyz_limits_mm"], set("xyz"), "xyz_limits_mm")
    path = exact_keys(data["path"], {
        "chord_tolerance_mm", "max_depth", "max_segments"
    }, "path")
    return Profile(
        data["machine_id"], data["purpose"], vector(data["pivot_mm"], "pivot_mm"),
        rotary(data["u"]), rotary(data["v"]),
        tuple(interval(limits[a]) for a in "xyz"), **path,
    )


def pose_from_dict(data: Any) -> Pose:
    exact_keys(data, {"xyz_mm", "u_deg", "v_deg"}, "pose")
    return Pose(vector(data["xyz_mm"], "xyz_mm"), data["u_deg"], data["v_deg"])


def pose_to_dict(pose: Pose) -> dict:
    return {"xyz_mm": list(pose.xyz.values()), "u_deg": pose.u, "v_deg": pose.v}
