"""Geometric subdivision, NOT a feedrate/extrusion/step scheduling planner."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .errors import LimitError
from .geometry import Transform
from .models import Pose, number


@dataclass(frozen=True)
class Node:
    t: float
    logical: Pose
    physical: Pose


@dataclass(frozen=True)
class Path:
    nodes: tuple[Node, ...]
    segment_error_bounds_mm: tuple[float, ...]

    @property
    def max_error_bound_mm(self) -> float:
        return max(self.segment_error_bounds_mm, default=0.0)


def chord_bound(transform: Transform, a: Pose, b: Pose) -> float:
    """||q - linear(q0,q1)|| <= sup||q''|| / 8 for segment parameter [0,1].

    q=Rx(u)Rz(v)w; w is affine. With s=|du|+|dv|,
    sup||q''|| <= s*s*max(||w0||,||w1||)+2*s*||dw||.
    The bound can overestimate error, but cannot miss multi-turn arcs like a
    midpoint-only check. Floating-point arithmetic is not formal interval math.
    """
    s = math.radians(abs(b.u - a.u) + abs(b.v - a.v))
    radius = max(
        (a.xyz + transform.registration.offset_mm).norm(),
        (b.xyz + transform.registration.offset_mm).norm(),
    )
    travel = (b.xyz - a.xyz).norm()
    return number((s * s * radius + 2 * s * travel) / 8, "chord error bound")


def subdivide(transform: Transform, start: Pose, end: Pose) -> Path:
    profile = transform.profile
    first = Node(0.0, start, transform.forward(start))
    last = Node(1.0, end, transform.forward(end))
    profile.check_pose(first.physical)
    profile.check_pose(last.physical)
    nodes = [first]
    errors: list[float] = []
    visited = 0

    def recurse(a: Node, b: Node, depth: int) -> None:
        nonlocal visited
        visited += 1
        # All work is local and discarded on error; never partially submit a path.
        if visited > 2 * profile.max_segments:
            raise LimitError("subdivision work budget exhausted; no path accepted")
        error = chord_bound(transform, a.logical, b.logical)
        inside = all(
            min(x, y) - error >= limit.low and max(x, y) + error <= limit.high
            for x, y, limit in zip(
                a.physical.xyz.values(), b.physical.xyz.values(), profile.xyz_limits_mm
            )
        )
        if error <= profile.chord_tolerance_mm and inside:
            if len(errors) >= profile.max_segments:
                raise LimitError("max_segments exceeded; no path accepted")
            nodes.append(b)
            errors.append(error)
            return
        if depth >= profile.max_depth:
            raise LimitError("cannot certify geometry/axis limits within max_depth")
        t = (a.t + b.t) / 2
        logical = start.interpolate(end, t)
        mid = Node(t, logical, transform.forward(logical))
        profile.check_pose(mid.physical)
        recurse(a, mid, depth + 1)
        recurse(mid, b, depth + 1)

    recurse(first, last, 0)
    return Path(tuple(nodes), tuple(errors))
