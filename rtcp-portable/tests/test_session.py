import unittest

from rtcp_portable.errors import LimitError, StateError
from rtcp_portable.models import Pose, Vec3
from rtcp_portable.session import Mode, OfflineSession
from tests.helpers import profile, ready_session


class SessionTests(unittest.TestCase):
    def test_new_session_cannot_begin(self):
        s = OfflineSession(profile(), Pose(Vec3(150, 150, 80), 0, 0))
        self.assertEqual(s.mode, Mode.DISABLED)
        with self.assertRaises(StateError):
            s.begin()

    def test_begin_end_preserve_physical_position(self):
        s = ready_session()
        physical = s.physical
        logical = s.begin()
        self.assertNotEqual(logical.xyz, physical.xyz)
        self.assertEqual(s.physical, physical)
        self.assertEqual(s.end(), physical)
        self.assertIsNone(s.logical)

    def test_end_at_rotated_pose_does_not_apply_inverse_again(self):
        s = ready_session()
        s.begin()
        s.queue_move(Pose(Vec3(20, 10, 30), 40, 75))
        s.drain_simulated()
        physical = s.physical
        self.assertEqual(s.end(), physical)
        logical = s.begin()
        self.assertLess((logical.xyz - Vec3(20, 10, 30)).norm(), 1e-9)
        self.assertEqual(s.physical, physical)

    def test_queue_not_executed_until_drain(self):
        s = ready_session()
        physical = s.physical
        s.begin()
        s.queue_move(Pose(Vec3(10, 20, 30), 10, 20))
        self.assertEqual(s.physical, physical)
        self.assertEqual(s.pending_count, 1)
        s.drain_simulated()
        self.assertNotEqual(s.physical, physical)
        self.assertEqual(s.pending_count, 0)

    def test_pending_queue_prevents_end_and_pause(self):
        s = ready_session()
        s.begin()
        s.queue_move(Pose(Vec3(10, 20, 30), 10, 20))
        for action in (s.end, s.pause):
            with self.assertRaises(StateError):
                action()
        self.assertEqual(s.mode, Mode.ACTIVE)
        self.assertEqual(s.pending_count, 1)

    def test_rejected_move_is_transactional(self):
        s = ready_session()
        s.begin()
        s.queue_move(Pose(Vec3(10, 20, 30), 10, 20))
        logical, physical = s.logical, s.physical
        with self.assertRaises(LimitError):
            s.queue_move(Pose(Vec3(10, 20, 30), 270, 20))
        self.assertEqual(s.logical, logical)
        self.assertEqual(s.physical, physical)
        self.assertEqual(s.pending_count, 1)

    def test_pause_preserves_session_and_reference(self):
        s = ready_session()
        logical = s.begin()
        generation = s.reference_generation
        s.pause()
        with self.assertRaises(StateError):
            s.queue_move(logical)
        s.resume()
        self.assertEqual(s.logical, logical)
        self.assertEqual(s.reference_generation, generation)

    def test_raw_operations_forbidden_when_active_or_paused(self):
        s = ready_session()
        s.begin()
        for paused in (False, True):
            if paused:
                s.pause()
            for operation in ("G28", "Z_TILT_ADJUST", "BED_MESH_CALIBRATE", "G92", "SET_U"):
                with self.subTest(operation=operation, paused=paused), self.assertRaises(StateError):
                    s.guard_machine_operation(operation)
        s.end()
        s.guard_machine_operation("G28")

    def test_no_reference_changes_in_active_session(self):
        s = ready_session()
        s.begin()
        with self.assertRaises(StateError):
            s.set_rotary_reference_simulated("v", 0)
        with self.assertRaises(StateError):
            s.set_xyz_homed_simulated()
        with self.assertRaises(StateError):
            s.register_vision_zero_pose(0, 0, dz=0)

    def test_reference_change_invalidates_registration(self):
        s = ready_session()
        generation = s.reference_generation
        s.set_rotary_reference_simulated("v", 0)
        self.assertGreater(s.reference_generation, generation)
        with self.assertRaises(StateError):
            s.begin()
        s.register_vision_zero_pose(3, -2, dz=0)
        s.begin()

    def test_xyz_rehoming_invalidates_registration(self):
        s = ready_session()
        s.set_xyz_homed_simulated()
        with self.assertRaises(StateError):
            s.begin()

    def test_vision_refuses_tilted_or_nonzero_v_pose(self):
        for axis, value in (("u", 20), ("v", 45)):
            s = ready_session()
            s.set_rotary_reference_simulated(axis, value)
            with self.subTest(axis=axis), self.assertRaises(StateError):
                s.register_vision_zero_pose(0, 0, dz=0)

    def test_vision_requires_explicit_dz(self):
        s = ready_session()
        with self.assertRaises(TypeError):
            s.register_vision_zero_pose(0, 0)

    def test_both_rotary_references_required(self):
        s = OfflineSession(profile(), Pose(Vec3(150, 150, 80), 0, 0))
        s.set_xyz_homed_simulated()
        s.set_rotary_reference_simulated("u", 0)
        with self.assertRaises(StateError):
            s.register_vision_zero_pose(0, 0, dz=0)

    def test_ac_alias_is_not_implicitly_accepted(self):
        with self.assertRaises(StateError):
            ready_session().set_rotary_reference_simulated("a", 0)

    def test_fault_loses_reference_and_never_parks(self):
        s = ready_session()
        s.begin()
        s.queue_move(Pose(Vec3(10, 20, 30), 10, 20))
        physical = s.physical
        s.fault()
        self.assertEqual(s.mode, Mode.FAULT)
        self.assertEqual(s.physical, physical)
        self.assertEqual(s.pending_count, 0)
        with self.assertRaises(StateError):
            s.resume()
        s.reset()
        with self.assertRaises(StateError):
            s.begin()

    def test_cancel_requires_stop_acknowledgement(self):
        s = ready_session()
        s.begin()
        with self.assertRaises(StateError):
            s.cancel_after_stop_simulated(s.physical, motion_stopped=False)
        self.assertEqual(s.mode, Mode.ACTIVE)

    def test_cancel_drops_queue_and_requires_new_registration(self):
        s = ready_session()
        s.begin()
        s.queue_move(Pose(Vec3(10, 20, 30), 10, 20))
        stopped = Pose(Vec3(140, 150, 90), 2, 3)
        s.cancel_after_stop_simulated(stopped, motion_stopped=True)
        self.assertEqual(s.mode, Mode.DISABLED)
        self.assertEqual(s.physical, stopped)
        self.assertEqual(s.pending_count, 0)
        with self.assertRaises(StateError):
            s.begin()

    def test_new_host_never_inherits_references(self):
        original = ready_session()
        original.begin()
        other = OfflineSession(profile(), original.physical)
        with self.assertRaises(StateError):
            other.begin()

    def test_motor_disable_invalidates_reference(self):
        s = ready_session()
        s.begin()
        s.pause()
        s.motors_disabled_simulated()
        self.assertEqual(s.mode, Mode.FAULT)
        with self.assertRaises(StateError):
            s.resume()
        s.reset()
        with self.assertRaises(StateError):
            s.begin()

    def test_move_rejected_while_disabled(self):
        s = ready_session()
        with self.assertRaises(StateError):
            s.queue_move(Pose(Vec3(0, 0, 0), 0, 0))
