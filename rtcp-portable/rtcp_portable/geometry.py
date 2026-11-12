"""Pure common-pivot kinematics; independent of CoreXY belt/motor mappings."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .errors import ConfigurationError
from .models import Pose, Profile, Registration, Vec3


def rx(point: Vec3, angle: float) -> Vec3:
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(point.x, c * point.y - s * point.z, s * point.y + c * point.z)


def rz(point: Vec3, angle: float) -> Vec3:
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(c * point.x - s * point.y, s * point.x + c * point.y, point.z)


@dataclass(frozen=True)
class Transform:
    profile: Profile
    registration: Registration

    def __post_init__(self) -> None:
        if not isinstance(self.profile, Profile) or not isinstance(self.registration, Registration):
            raise ConfigurationError("Transform requires Profile and Registration")

    def forward(self, logical: Pose) -> Pose:
        p = logical.xyz + self.registration.offset_mm
        p = rz(p, self.profile.v.radians(logical.v))
        p = rx(p, self.profile.u.radians(logical.u))
        return Pose(self.profile.pivot_mm + p, logical.u, logical.v)

    def inverse(self, physical: Pose) -> Pose:
        p = physical.xyz - self.profile.pivot_mm
        p = rx(p, -self.profile.u.radians(physical.u))
        p = rz(p, -self.profile.v.radians(physical.v))
        return Pose(p - self.registration.offset_mm, physical.u, physical.v)
