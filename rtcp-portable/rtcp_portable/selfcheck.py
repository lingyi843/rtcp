"""Small installed-package smoke check; full regression suite lives in tests/."""
from __future__ import annotations

from .geometry import Transform
from .models import Interval, Pose, Profile, Registration, Rotary, Vec3
from .path import subdivide
from .session import Mode, OfflineSession


def run() -> dict:
    profile = Profile(
        "BUILTIN-SYNTHETIC", "simulation", Vec3(100, 120, 30),
        Rotary(1, 0, Interval(-100, 100), (260, 18)),
        Rotary(1, 0, Interval(-720, 720), (1, 1)),
        (Interval(-200, 400),) * 3,
    )
    transform = Transform(profile, Registration(Vec3(2, 3, 0)))
    source = Pose(Vec3(10, 20, 30), 35, 70)
    recovered = transform.inverse(transform.forward(source))
    if (recovered.xyz - source.xyz).norm() > 1e-10:
        raise RuntimeError("round-trip selfcheck failed")
    path = subdivide(transform, Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 90))
    if len(path.nodes) < 3 or path.max_error_bound_mm > profile.chord_tolerance_mm:
        raise RuntimeError("arc selfcheck failed")
    initial = Pose(Vec3(150, 150, 50), 0, 0)
    session = OfflineSession(profile, initial)
    session.set_xyz_homed_simulated()
    session.set_rotary_reference_simulated("u", 0)
    session.set_rotary_reference_simulated("v", 0)
    session.register_vision_zero_pose(2, 3, dz=0)
    session.begin()
    session.pause()
    session.resume()
    session.end()
    if session.physical != initial or session.mode != Mode.DISABLED:
        raise RuntimeError("no-jump selfcheck failed")
    return {
        "ok": True, "offline_only": True, "live_supported": False,
        "checks": ["nonzero_pivot_roundtrip", "bounded_arc", "no_jump_lifecycle"],
        "arc_segments": len(path.nodes) - 1,
    }
