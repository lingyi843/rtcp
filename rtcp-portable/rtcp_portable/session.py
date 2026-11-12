"""Offline lifecycle model. drain_simulated() is NOT a machine stop/queue API.

No transport, timers, firmware imports or serialized homing/session state.
All new instances are disabled and unreferenced.
"""
from __future__ import annotations

from enum import Enum

from .errors import StateError
from .geometry import Transform
from .models import Pose, Profile, Registration, Vec3, number
from .path import Path, subdivide


class Mode(str, Enum):
    DISABLED = "disabled"
    ACTIVE = "active"
    PAUSED = "paused"
    FAULT = "fault"


class OfflineSession:
    def __init__(self, profile: Profile, initial_physical: Pose):
        profile.check_pose(initial_physical)
        self._profile = profile
        self._physical = initial_physical
        self._mode = Mode.DISABLED
        self._xyz_homed = False
        self._references: set[str] = set()
        self._generation = 0
        self._registration: Registration | None = None
        self._registration_generation: int | None = None
        self._transform: Transform | None = None
        self._logical: Pose | None = None
        self._pending: list[Path] = []

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def physical(self) -> Pose:
        """Last executed simulated position, NOT the last queued endpoint."""
        return self._physical

    @property
    def logical(self) -> Pose | None:
        """Scheduled endpoint while active; None in raw-machine mode."""
        return self._logical

    @property
    def reference_generation(self) -> int:
        return self._generation

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def _idle(self) -> None:
        if self._pending:
            raise StateError("requires an empty simulated queue")

    def _disabled_idle(self) -> None:
        if self._mode != Mode.DISABLED:
            raise StateError("requires RTCP disabled")
        self._idle()

    def _invalidate_registration(self) -> None:
        self._generation += 1
        self._registration = None
        self._registration_generation = None

    def set_xyz_homed_simulated(self) -> None:
        self._disabled_idle()
        self._xyz_homed = True
        # Homing may redefine machine coordinates/calibration association.
        self._invalidate_registration()

    def set_rotary_reference_simulated(self, axis: str, coordinate_deg: float) -> None:
        self._disabled_idle()
        if axis not in ("u", "v"):
            raise StateError("axis must be 'u' or 'v'; legacy A/C not accepted")
        coordinate_deg = number(coordinate_deg, "reference")
        getattr(self._profile, axis).limits_deg.check(coordinate_deg, axis.upper())
        self._physical = Pose(
            self._physical.xyz,
            coordinate_deg if axis == "u" else self._physical.u,
            coordinate_deg if axis == "v" else self._physical.v,
        )
        self._references.add(axis)
        self._invalidate_registration()

    def register_vision_zero_pose(self, dx: float, dy: float, *, dz: float) -> None:
        """Explicit dz is required, including when the chosen assumption is zero."""
        self._disabled_idle()
        if not self._xyz_homed or self._references != {"u", "v"}:
            raise StateError("XYZ and both rotary references required before registration")
        if (
            abs(self._physical.u - self._profile.u.zero_deg) > 1e-9
            or abs(self._physical.v - self._profile.v.zero_deg) > 1e-9
        ):
            raise StateError("2D vision registration requires the defined U/V zero pose")
        registration = Registration(Vec3(dx, dy, dz))
        self._registration = registration
        self._registration_generation = self._generation

    def begin(self) -> Pose:
        self._disabled_idle()
        if not self._xyz_homed or self._references != {"u", "v"}:
            raise StateError("XYZ and U/V references are not valid")
        if self._registration is None or self._registration_generation != self._generation:
            raise StateError("missing/stale work registration")
        self._profile.check_pose(self._physical)
        transform = Transform(self._profile, self._registration)
        logical = transform.inverse(self._physical)
        self._transform, self._logical = transform, logical
        self._mode = Mode.ACTIVE
        return logical

    def queue_move(self, target: Pose) -> Path:
        if self._mode != Mode.ACTIVE:
            raise StateError("moves require ACTIVE state")
        assert self._transform is not None and self._logical is not None
        if len(self._pending) >= 1024:
            raise StateError("offline pending block budget exceeded")
        path = subdivide(self._transform, self._logical, target)
        if sum(len(p.nodes) - 1 for p in self._pending) + len(path.nodes) - 1 > self._profile.max_segments:
            raise StateError("offline pending segment budget exceeded")
        self._pending.append(path)
        self._logical = target
        return path

    def drain_simulated(self) -> None:
        if self._mode != Mode.ACTIVE:
            raise StateError("simulated drain requires ACTIVE state")
        if self._pending:
            self._physical = self._pending[-1].nodes[-1].physical
            self._pending.clear()

    def pause(self) -> None:
        if self._mode != Mode.ACTIVE:
            raise StateError("pause requires ACTIVE state")
        self._idle()
        self._mode = Mode.PAUSED

    def resume(self) -> None:
        if self._mode != Mode.PAUSED:
            raise StateError("resume requires PAUSED state")
        self._mode = Mode.ACTIVE

    def end(self) -> Pose:
        if self._mode not in (Mode.ACTIVE, Mode.PAUSED):
            raise StateError("end requires ACTIVE or PAUSED state")
        self._idle()
        # Expose already-executed machine coordinates; do NOT inverse them again.
        self._logical, self._transform = None, None
        self._mode = Mode.DISABLED
        return self._physical

    def guard_machine_operation(self, name: str) -> None:
        """Future adapter must call this for homing/leveling/G92/reference edits."""
        if self._mode != Mode.DISABLED:
            raise StateError(f"{name} is forbidden while RTCP is {self._mode.value}")
        self._idle()

    def _lose_position(self) -> None:
        self._pending.clear()
        self._logical, self._transform = None, None
        self._references.clear()
        self._xyz_homed = False
        self._invalidate_registration()

    def fault(self) -> None:
        self._lose_position()
        self._mode = Mode.FAULT

    def motors_disabled_simulated(self) -> None:
        """Open-loop positions cease to be trusted; never retain an armed job."""
        self.fault()

    def reset(self) -> None:
        """Simulation reset only: cannot stop hardware or certify physical position."""
        self._lose_position()
        self._mode = Mode.DISABLED

    def cancel_after_stop_simulated(self, stopped_physical: Pose, *, motion_stopped: bool) -> None:
        if self._mode not in (Mode.ACTIVE, Mode.PAUSED, Mode.FAULT):
            raise StateError("no active/faulted session to cancel")
        if motion_stopped is not True:
            raise StateError("explicit simulated stop acknowledgement required")
        self._profile.check_pose(stopped_physical)
        self._lose_position()
        self._physical = stopped_physical
        self._mode = Mode.DISABLED
