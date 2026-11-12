from dataclasses import replace
import copy
import json
from pathlib import Path
import unittest

from rtcp_portable.errors import ConfigurationError
from rtcp_portable.geometry import Transform
from rtcp_portable.models import Registration, Vec3
from rtcp_portable.timing import AXIS_NAMES, RateLimit, TimingLimits, limits_from_dict, plan_job, trapezoid
from tests.helpers import profile

ROOT = Path(__file__).resolve().parents[1]


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.transform = Transform(profile(), Registration(Vec3(5, -3, 0)))
        self.limits = limits_from_dict(json.loads((ROOT / "profiles/timing.simulation.json").read_text()))
        self.job = json.loads((ROOT / "examples/timed-job.json").read_text())

    def test_each_trapezoid_integrates_to_one(self):
        for distance, requested in ((.001, 0), (1, 0), (1000, 0), (10, 100)):
            with self.subTest(distance=distance, requested=requested):
                timing = trapezoid((distance, 0, 0, 0, 0, 0, distance, distance), self.limits, requested)
                accel, ramp = timing["normalized_acceleration"], timing["accel_s"]
                peak, cruise = timing["normalized_peak_velocity"], timing["cruise_s"]
                self.assertAlmostEqual(accel * ramp * ramp + peak * cruise, 1, places=10)
                self.assertGreaterEqual(timing["duration_s"], requested)

    def test_all_axis_speed_and_acceleration_bounds(self):
        result = plan_job(self.transform, self.limits, self.job)
        for segment in result["segments"]:
            for axis, limit in zip(AXIS_NAMES, self.limits.axes):
                self.assertLessEqual(segment["timing"]["axis_peak_velocity"][axis], limit.velocity + 1e-9)
                self.assertLessEqual(segment["timing"]["axis_acceleration"][axis], limit.acceleration + 1e-9)

    def test_signed_e_preserved_across_subdivision(self):
        result = plan_job(self.transform, self.limits, self.job)
        for index, event in enumerate(self.job["events"]):
            self.assertAlmostEqual(
                sum(segment["e_delta_mm"] for segment in result["segments"] if segment["event"] == index),
                event.get("e_delta_mm", 0), places=12,
            )
        self.assertAlmostEqual(result["net_e_mm"], .8)
        self.assertGreater(result["segment_count"], len(self.job["events"]))

    def test_common_normalized_time_on_all_axes(self):
        result = plan_job(self.transform, self.limits, self.job)
        for segment in result["segments"]:
            start, end = segment["physical_start"], segment["physical_end"]
            values = [b-a for a, b in zip(start["xyz_mm"], end["xyz_mm"])]
            values.extend((end["u_deg"]-start["u_deg"], end["v_deg"]-start["v_deg"], segment["e_delta_mm"]))
            peak = segment["timing"]["normalized_peak_velocity"]
            for axis, delta in zip(AXIS_NAMES, values):
                self.assertAlmostEqual(segment["timing"]["axis_peak_velocity"][axis], abs(delta)*peak)

    def test_time_is_contiguous_and_ends_at_total(self):
        result = plan_job(self.transform, self.limits, self.job)
        elapsed = 0
        for segment in result["segments"]:
            self.assertAlmostEqual(segment["start_time_s"], elapsed)
            elapsed += segment["timing"]["duration_s"]
        self.assertAlmostEqual(elapsed, result["duration_s"])

    def test_tighter_corexy_limits_increase_duration(self):
        baseline = plan_job(self.transform, self.limits, self.job)
        limits = TimingLimits(self.limits.axes[:6] + (RateLimit(.01, .1), RateLimit(.01, .1)))
        slower = plan_job(self.transform, limits, self.job)
        self.assertGreater(slower["duration_s"], baseline["duration_s"])

    def test_tighter_rotary_limits_increase_duration(self):
        axes = list(self.limits.axes)
        axes[3] = RateLimit(.01, .1)
        slower = plan_job(self.transform, TimingLimits(tuple(axes)), self.job)
        baseline = plan_job(self.transform, self.limits, self.job)
        self.assertGreater(slower["duration_s"], baseline["duration_s"])

    def test_macro_cannot_pass_through(self):
        self.job["events"].append({"kind": "M98", "path": "file.g"})
        with self.assertRaises(ConfigurationError):
            plan_job(self.transform, self.limits, self.job)

    def test_postik_coordinate_declaration_rejected(self):
        self.job["coordinate_space"] = "machine_post_ik"
        with self.assertRaises(ConfigurationError):
            plan_job(self.transform, self.limits, self.job)

    def test_old_angle_convention_rejected(self):
        self.job["angle_convention"] = "ry_minus_a_rz_c"
        with self.assertRaises(ConfigurationError):
            plan_job(self.transform, self.limits, self.job)

    def test_zero_length_extruding_move_not_misinterpreted(self):
        self.job["events"][0]["target"] = copy.deepcopy(self.job["initial_pose"])
        with self.assertRaises(ConfigurationError):
            plan_job(self.transform, self.limits, self.job)

    def test_explicit_orient_can_move_xyz_without_model_translation(self):
        result = plan_job(self.transform, self.limits, self.job)
        segments = [s for s in result["segments"] if s["kind"] == "orient"]
        self.assertTrue(segments)
        self.assertEqual(segments[0]["logical_start"]["xyz_mm"], segments[-1]["logical_end"]["xyz_mm"])
        self.assertNotEqual(segments[0]["physical_start"]["xyz_mm"], segments[-1]["physical_end"]["xyz_mm"])
        self.assertEqual(sum(s["e_delta_mm"] for s in segments), 0)

    def test_budget_is_whole_job(self):
        tiny_profile = replace(profile(), max_segments=1)
        with self.assertRaises(ValueError):
            plan_job(Transform(tiny_profile, Registration(Vec3(0, 0, 0))), self.limits, self.job)

    def test_limits_must_be_complete_and_positive(self):
        data = json.loads((ROOT / "profiles/timing.simulation.json").read_text())
        del data["axes"]["e"]
        with self.assertRaises(ConfigurationError):
            limits_from_dict(data)
        with self.assertRaises(ConfigurationError):
            RateLimit(0, 1)

    def test_noops_rejected(self):
        with self.assertRaises(ConfigurationError):
            trapezoid((0,)*8, self.limits, 0)

    def test_offline_timing_flags_remain_false(self):
        result = plan_job(self.transform, self.limits, self.job)
        self.assertFalse(result["live_supported"])
        self.assertFalse(result["executable_gcode"])
        self.assertEqual(result["timing_model"], "rest_to_rest_every_chord")
