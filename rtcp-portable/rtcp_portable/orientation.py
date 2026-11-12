"""Explicit normal-to-platform-angle solver for NEW pre-IK model exports."""
from __future__ import annotations

import math

from .errors import ConfigurationError, LimitError
from .models import Profile, Rotary, Vec3, number


def _nearest_equivalent(base: float, previous: float, axis: Rotary) -> float | None:
    low = math.ceil((axis.limits_deg.low - base) / 360)
    high = math.floor((axis.limits_deg.high - base) / 360)
    if low > high:
        return None
    turns = max(low, min(high, round((previous - base) / 360)))
    return number(base + 360 * turns, "continuous controller angle")


def normal_to_uv(
    normal: Vec3, profile: Profile, previous_u: float, previous_v: float, *,
    max_step_deg: float,
) -> tuple[float, float]:
    """Align surface outward normal to machine +Z with Rx(U)Rz(V).

    This is an explicit branch/turn selection policy for a new orientation
    export, NOT automatic wrapping of user-supplied G-code angles.
    Tool-axis roll is unconstrained; this does not solve a full 3-DOF orientation.
    """
    previous_u, previous_v = number(previous_u, "previous U"), number(previous_v, "previous V")
    profile.u.limits_deg.check(previous_u, "previous U")
    profile.v.limits_deg.check(previous_v, "previous V")
    max_step_deg = number(max_step_deg, "max_step_deg")
    if max_step_deg <= 0:
        raise ConfigurationError("max_step_deg must be positive")
    length = number(normal.norm(), "normal length")
    if length < 1e-15:
        raise ConfigurationError("normal is zero or numerically degenerate")
    n = normal.scaled(1 / length)
    radius = math.hypot(n.x, n.y)
    tilt = math.degrees(math.atan2(radius, n.z))
    spin = math.degrees(math.atan2(n.x, n.y))
    candidates = []
    for u_angle, v_angle in ((tilt, spin), (-tilt, spin + 180)):
        u = _nearest_equivalent(profile.u.zero_deg + profile.u.sign * u_angle, previous_u, profile.u)
        if radius < 1e-12:
            v = previous_v  # At the pole, spin has no normal-alignment meaning.
        else:
            v = _nearest_equivalent(profile.v.zero_deg + profile.v.sign * v_angle, previous_v, profile.v)
        if u is not None and v is not None:
            if max(abs(u - previous_u), abs(v - previous_v)) <= max_step_deg:
                candidates.append((u, v))
    if not candidates:
        raise LimitError("normal has no permitted continuous UV branch; no automatic rewind")
    return min(candidates, key=lambda uv: (uv[0] - previous_u)**2 + (uv[1] - previous_v)**2)
