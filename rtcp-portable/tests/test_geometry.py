from dataclasses import FrozenInstanceError, replace
import copy
import json
import math
from pathlib import Path
import random
import unittest

from rtcp_portable.errors import ConfigurationError, LimitError
from rtcp_portable.geometry import Transform
from rtcp_portable.models import Interval, Pose, Registration, Rotary, Vec3, profile_from_dict
from rtcp_portable.path import chord_bound, subdivide
from tests.helpers import profile

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_finite_numbers_only(self):
        for bad in (True, "1", None, float("inf"), float("nan"), 10**500):
            with self.subTest(bad=repr(bad)), self.assertRaises(ConfigurationError):
                Vec3(bad, 0, 0)

    def test_immutable_objects(self):
        point = Vec3(1, 2, 3)
        with self.assertRaises(FrozenInstanceError):
            point.x = 5
        with self.assertRaises(FrozenInstanceError):
            profile().u.sign = -1

    def test_sign_is_explicit_integer(self):
        for bad in (0, 2, True, 1.0, None):
            with self.subTest(bad=bad), self.assertRaises(ConfigurationError):
                Rotary(bad, 0, Interval(-90, 90), (260, 18))

    def test_bad_limits(self):
        for values in ((5, 5), (10, 0), (0, float("nan"))):
            with self.subTest(values=values), self.assertRaises(ConfigurationError):
                Interval(*values)

    def test_bad_gear(self):
        for gear in ((0, 18), (260, -1), [260], None):
            with self.subTest(gear=gear), self.assertRaises(ConfigurationError):
                Rotary(1, 0, Interval(-90, 90), gear)

    def test_profile_budgets(self):
        for name, bad in (
            ("max_depth", 0), ("max_depth", 25), ("max_depth", True),
            ("max_segments", 0), ("chord_tolerance_mm", 0),
        ):
            with self.subTest(name=name, bad=bad), self.assertRaises(ConfigurationError):
                replace(profile(), **{name: bad})

    def test_valid_synthetic_profile(self):
        data = json.loads((ROOT / "profiles/simulation.json").read_text())
        result = profile_from_dict(data)
        self.assertEqual(result.u.gear_ratio, (260, 18))

    def test_machine_template_is_rejected(self):
        data = json.loads((ROOT / "profiles/machine.template.json").read_text())
        with self.assertRaises(ConfigurationError):
            profile_from_dict(data)

    def test_unknown_keys_and_geometry_fail_closed(self):
        original = json.loads((ROOT / "profiles/simulation.json").read_text())
        for field, value in (("extra", 1), ("geometry", "legacy_ry_a"), ("schema_version", True)):
            data = copy.deepcopy(original)
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ConfigurationError):
                profile_from_dict(data)

    def test_limits_copied_immutable(self):
        limits = list(profile().xyz_limits_mm)
        result = replace(profile(), xyz_limits_mm=limits)
        limits[0] = Interval(0, 1)
        self.assertEqual(result.xyz_limits_mm[0], Interval(-1000, 1000))

    def test_transform_contract(self):
        with self.assertRaises(ConfigurationError):
            Transform(None, Registration(Vec3(0, 0, 0)))


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.config = profile()
        self.transform = Transform(self.config, Registration(Vec3(5, -3, 2)))

    def assertVector(self, actual, expected, tolerance=1e-9):
        self.assertLessEqual((actual - expected).norm(), tolerance)

    def test_identity_adds_pivot_and_offset_once(self):
        output = self.transform.forward(Pose(Vec3(10, 20, 30), 0, 0))
        self.assertVector(output.xyz, Vec3(115, 137, 62))

    def test_u_rotates_about_x_not_old_y(self):
        transform = Transform(self.config, Registration(Vec3(0, 0, 0)))
        output = transform.forward(Pose(Vec3(0, 10, 0), 90, 0))
        self.assertVector(output.xyz, self.config.pivot_mm + Vec3(0, 0, 10))

    def test_v_is_inner_axis_and_rotates_with_u(self):
        transform = Transform(self.config, Registration(Vec3(0, 0, 0)))
        output = transform.forward(Pose(Vec3(10, 0, 0), 90, 90))
        self.assertVector(output.xyz, self.config.pivot_mm + Vec3(0, 0, 10))

    def test_registration_rotates_with_work(self):
        transform = Transform(self.config, Registration(Vec3(10, 0, 0)))
        output = transform.forward(Pose(Vec3(0, 0, 0), 0, 90))
        self.assertVector(output.xyz, self.config.pivot_mm + Vec3(0, 10, 0))

    def test_direction_is_configuration(self):
        config = replace(self.config, u=replace(self.config.u, sign=-1))
        transform = Transform(config, Registration(Vec3(0, 0, 0)))
        self.assertVector(
            transform.forward(Pose(Vec3(0, 10, 0), 90, 0)).xyz,
            config.pivot_mm + Vec3(0, 0, -10),
        )

    def test_nonzero_controller_zeros(self):
        config = replace(
            self.config, u=replace(self.config.u, zero_deg=10),
            v=replace(self.config.v, zero_deg=-20),
        )
        transform = Transform(config, Registration(Vec3(0, 0, 0)))
        self.assertVector(
            transform.forward(Pose(Vec3(1, 2, 3), 10, -20)).xyz,
            config.pivot_mm + Vec3(1, 2, 3),
        )

    def test_gear_does_not_multiply_platform_angle(self):
        altered = replace(self.config, u=replace(self.config.u, gear_ratio=(1, 1)))
        pose = Pose(Vec3(20, 30, 40), 30, 60)
        self.assertEqual(
            self.transform.forward(pose),
            Transform(altered, self.transform.registration).forward(pose),
        )

    def test_nonzero_pivot_roundtrip_regression(self):
        pose = Pose(Vec3(20, 40, 60), 45, -30)
        self.assertVector(self.transform.inverse(self.transform.forward(pose)).xyz, pose.xyz)

    def test_independent_closed_form_1000_cases(self):
        rng = random.Random(20261110)
        for _ in range(1000):
            config = replace(
                self.config,
                u=replace(self.config.u, sign=rng.choice((-1, 1))),
                v=replace(self.config.v, sign=rng.choice((-1, 1))),
            )
            transform = Transform(config, self.transform.registration)
            pose = Pose(Vec3(*(rng.uniform(-100, 100) for _ in range(3))),
                        rng.uniform(-90, 90), rng.uniform(-720, 720))
            a, b = math.radians(config.u.sign * pose.u), math.radians(config.v.sign * pose.v)
            x, y, z = (pose.xyz + transform.registration.offset_mm).values()
            # Independent expanded matrix, no calls to rx/rz.
            expected = config.pivot_mm + Vec3(
                math.cos(b)*x - math.sin(b)*y,
                math.cos(a)*math.sin(b)*x + math.cos(a)*math.cos(b)*y - math.sin(a)*z,
                math.sin(a)*math.sin(b)*x + math.sin(a)*math.cos(b)*y + math.cos(a)*z,
            )
            actual = transform.forward(pose)
            self.assertVector(actual.xyz, expected)
            restored = transform.inverse(actual)
            self.assertVector(restored.xyz, pose.xyz)
            self.assertEqual((restored.u, restored.v), (pose.u, pose.v))


class PathTests(unittest.TestCase):
    def setUp(self):
        self.config = replace(profile(), pivot_mm=Vec3(0, 0, 0))
        self.transform = Transform(self.config, Registration(Vec3(0, 0, 0)))

    def test_straight_line_needs_one_segment(self):
        path = subdivide(self.transform, Pose(Vec3(0, 0, 0), 0, 0), Pose(Vec3(100, 20, 5), 0, 0))
        self.assertEqual(len(path.nodes), 2)
        self.assertEqual(path.max_error_bound_mm, 0)

    def test_arc_midpoint_legacy_regression(self):
        start, end = Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 90)
        actual_mid = self.transform.forward(start.interpolate(end, .5)).xyz
        chord_mid = (self.transform.forward(start).xyz + self.transform.forward(end).xyz).scaled(.5)
        self.assertAlmostEqual((actual_mid - chord_mid).norm(), 14.64466094, places=7)
        path = subdivide(self.transform, start, end)
        self.assertGreater(len(path.nodes), 2)
        self.assertLessEqual(path.max_error_bound_mm, self.config.chord_tolerance_mm)

    def test_multi_turn_arc_not_missed_by_midpoint(self):
        start, end = Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 720)
        path = subdivide(self.transform, start, end)
        self.assertGreater(len(path.nodes), 100)
        self.assertEqual(path.nodes[-1].physical.v, 720)

    def test_no_automatic_shortest_angle_wrap(self):
        start, end = Pose(Vec3(50, 0, 0), 0, 170), Pose(Vec3(50, 0, 0), 0, -170)
        path = subdivide(self.transform, start, end)
        self.assertTrue(any(abs(node.logical.v) < 1e-12 for node in path.nodes))

    def test_interior_exceeds_limit_despite_valid_endpoints(self):
        config = replace(self.config, xyz_limits_mm=(Interval(-100, 100), Interval(-10, 40), Interval(-100, 100)))
        transform = Transform(config, Registration(Vec3(0, 0, 0)))
        with self.assertRaises(LimitError):
            subdivide(transform, Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 180))

    def test_transformed_xyz_limit_not_logical_limit(self):
        config = replace(self.config, pivot_mm=Vec3(980, 0, 0))
        transform = Transform(config, Registration(Vec3(0, 0, 0)))
        with self.assertRaises(LimitError):
            subdivide(transform, Pose(Vec3(0, 0, 0), 0, 0), Pose(Vec3(30, 0, 0), 0, 0))

    def test_rotary_limits_reject_u270(self):
        with self.assertRaises(LimitError):
            subdivide(self.transform, Pose(Vec3(0, 0, 0), 0, 0), Pose(Vec3(0, 0, 0), 270, 0))

    def test_segment_budget_fails_closed(self):
        config = replace(self.config, max_segments=1)
        with self.assertRaises(LimitError):
            subdivide(Transform(config, self.transform.registration),
                      Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 90))

    def test_depth_budget_fails_closed(self):
        config = replace(self.config, max_depth=1, chord_tolerance_mm=1e-10)
        with self.assertRaises(LimitError):
            subdivide(Transform(config, self.transform.registration),
                      Pose(Vec3(50, 0, 0), 0, 0), Pose(Vec3(50, 0, 0), 0, 90))

    def test_zero_radius_can_rotate_without_xyz_motion(self):
        path = subdivide(self.transform, Pose(Vec3(0, 0, 0), 0, 0), Pose(Vec3(0, 0, 0), 90, 180))
        self.assertEqual(len(path.nodes), 2)

    def test_dense_sampling_confirms_bounds_100_random_paths(self):
        rng = random.Random(321)
        for _ in range(100):
            a, b = [
                Pose(Vec3(*(rng.uniform(-60, 60) for _ in range(3))),
                     rng.uniform(-90, 90), rng.uniform(-360, 360))
                for _ in range(2)
            ]
            path = subdivide(self.transform, a, b)
            for start, end, bound in zip(path.nodes, path.nodes[1:], path.segment_error_bounds_mm):
                for t in (.1, .3, .5, .7, .9):
                    ideal = self.transform.forward(start.logical.interpolate(end.logical, t))
                    chord = start.physical.interpolate(end.physical, t)
                    self.assertLessEqual((ideal.xyz - chord.xyz).norm(), bound + 1e-9)
                    self.config.check_pose(ideal)
                self.assertLessEqual(bound, self.config.chord_tolerance_mm)

    def test_combined_linear_rotary_derivative_bound(self):
        a, b = Pose(Vec3(1, 2, 3), -90, -360), Pose(Vec3(10, -50, 20), 90, 360)
        bound = chord_bound(self.transform, a, b)
        for i in range(101):
            t = i / 100
            ideal = self.transform.forward(a.interpolate(b, t))
            chord = self.transform.forward(a).interpolate(self.transform.forward(b), t)
            self.assertLessEqual((ideal.xyz - chord.xyz).norm(), bound)
