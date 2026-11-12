from rtcp_portable.models import Interval, Pose, Profile, Rotary, Vec3
from rtcp_portable.session import OfflineSession


def profile():
    return Profile(
        "test", "simulation", Vec3(100, 120, 30),
        Rotary(1, 0, Interval(-100, 100), (260, 18)),
        Rotary(1, 0, Interval(-1080, 1080), (1, 1)),
        (Interval(-1000, 1000),) * 3,
        chord_tolerance_mm=0.02,
    )


def ready_session():
    session = OfflineSession(profile(), Pose(Vec3(150, 150, 80), 0, 0))
    session.set_xyz_homed_simulated()
    session.set_rotary_reference_simulated("u", 0)
    session.set_rotary_reference_simulated("v", 0)
    session.register_vision_zero_pose(3, -2, dz=0)
    return session
