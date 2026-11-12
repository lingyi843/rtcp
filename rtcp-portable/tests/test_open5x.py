import copy
from dataclasses import replace
import importlib.util
import json
import math
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest

from rtcp_portable.capture import inspect_capture
from rtcp_portable.errors import ConfigurationError, LimitError
from rtcp_portable.gcode import analyze_gcode, strip_comments, words
from rtcp_portable.geometry import rx, rz
from rtcp_portable.ghx import inspect_ghx
from rtcp_portable.models import Interval, Vec3
from rtcp_portable.orientation import normal_to_uv
from tests.helpers import profile

ROOT = Path(__file__).resolve().parents[1]
SETUP = "G21\nG90\nM83\nG92 X0 Y0 Z0 U0 V0 E0\n"


class GCodeTests(unittest.TestCase):
    def test_relative_extrusion_and_modal_axes(self):
        report = analyze_gcode(SETUP + "G1X1Y2U3V4E.5F600\nG1Z3E-.2\n")
        first, second = report["motions"]
        self.assertEqual(first["e_delta_mm"], .5)
        self.assertEqual(second["e_delta_mm"], -.2)
        self.assertEqual(second["end"], {"X": 1, "Y": 2, "Z": 3, "U": 3, "V": 4})
        self.assertEqual(second["feed_word"], 600)
        self.assertFalse(second["unresolved"])

    def test_absolute_extrusion_g92_and_retraction(self):
        report = analyze_gcode(SETUP + "M82\nG1E2F300\nG1E1\nG92E0\nG1E.5\n")
        self.assertEqual([m["e_delta_mm"] for m in report["motions"]], [2, -1, .5])

    def test_independent_e_mode_survives_g90(self):
        report = analyze_gcode(SETUP + "G90\nG1E1F300\nG1E1\n")
        self.assertEqual(report["known_signed_e_sum_mm"], 2)

    def test_relative_coordinates(self):
        report = analyze_gcode(SETUP + "G91\nG1X2U3F600\nG1X2U3\n")
        self.assertEqual(report["motions"][-1]["end"]["X"], 4)
        self.assertEqual(report["motions"][-1]["end"]["U"], 6)

    def test_external_macro_invalidates_all_modes(self):
        report = analyze_gcode(SETUP + 'M98 P"/macros/file.g"\nG1X1Y1Z1U0V0E1F600')
        move = report["motions"][0]
        self.assertIsNone(move["e_delta_mm"])
        self.assertIsNone(move["end"]["X"])
        self.assertIn("distance_mode_unknown", move["unresolved"])
        self.assertFalse(report["automatic_rtcp_import_allowed"])

    def test_modes_can_be_reestablished_after_unknown(self):
        report = analyze_gcode("UNSUPPORTED_MACRO\n" + SETUP + "G1X1E.5F600\n")
        self.assertFalse(report["motions"][0]["unresolved"])
        self.assertFalse(report["automatic_rtcp_import_allowed"])

    def test_no_initial_state_guessed(self):
        move = analyze_gcode("G1X1Y2E1\n")["motions"][0]
        self.assertIsNone(move["e_delta_mm"])
        self.assertIn("units_unknown_or_not_mm", move["unresolved"])
        self.assertIn("feed_unknown", move["unresolved"])

    def test_duplicate_words_rejected(self):
        report = analyze_gcode(SETUP + "G1 X1 X2 F600")
        self.assertEqual(report["motion_count"], 0)
        self.assertIn("syntax_or_unsupported", report["issue_counts"])

    def test_nonfinite_words_rejected(self):
        with self.assertRaises(ConfigurationError):
            words("X" + "9" * 500)
        report = analyze_gcode("G1 XNaN")
        self.assertEqual(report["motion_count"], 0)

    def test_comments_respect_quotes_and_parentheses(self):
        self.assertEqual(strip_comments('M98 P"/a;b.g" ; ignore'), 'M98 P"/a;b.g"')
        self.assertEqual(strip_comments("G1 X1 (Y999 (nested)) E.1; bad"), "G1 X1  E.1")

    def test_malformed_comments_fail_closed(self):
        for text in ("G1 X1 (", "G1 X1 )", 'M98 P"unterminated'):
            with self.subTest(text=text), self.assertRaises(ConfigurationError):
                strip_comments(text)

    def test_inch_is_not_silently_used_as_mm(self):
        report = analyze_gcode(SETUP + "G20\nG1X1E1F60")
        self.assertIsNone(report["motions"][0]["end"]["X"])
        self.assertIn("inch_not_supported", report["issue_counts"])

    def test_pure_rotary_extrusion_flags_postik_candidate(self):
        report = analyze_gcode(SETUP + "G1X0Y0Z20U30V-400E.01F500\n")
        self.assertEqual(report["raw_word_ranges"]["V"]["minimum"], -400)
        self.assertIn("possible_post_ik_coordinates", report["issue_counts"])

    def test_heating_commands_are_only_counted(self):
        report = analyze_gcode("M104 S220\nM109 S220\nM104 S0")
        self.assertEqual(report["motion_count"], 0)
        self.assertEqual(report["command_counts"]["M104"], 2)

    def test_bad_feed_cannot_reuse_previous_feed(self):
        report = analyze_gcode(SETUP + "G1X1F600\nG1X2F0")
        self.assertIsNone(report["motions"][-1]["feed_word"])


class OrientationTests(unittest.TestCase):
    def test_north_pole_keeps_spin(self):
        self.assertEqual(normal_to_uv(Vec3(0, 0, 1), profile(), 0, 350, max_step_deg=1), (0, 350))

    def test_zero_normal_rejected(self):
        with self.assertRaises(ConfigurationError):
            normal_to_uv(Vec3(0, 0, 0), profile(), 0, 0, max_step_deg=180)

    def test_south_pole_outside_u_limits(self):
        with self.assertRaises(LimitError):
            normal_to_uv(Vec3(0, 0, -1), profile(), 0, 0, max_step_deg=360)

    def test_large_step_does_not_auto_rewind(self):
        with self.assertRaises(LimitError):
            normal_to_uv(Vec3(1, 0, 0), profile(), 0, 0, max_step_deg=10)

    def test_continuous_spin_crosses_360_without_reset(self):
        normal = Vec3(math.sin(math.radians(1)), math.cos(math.radians(1)), 1)
        u, v = normal_to_uv(normal, profile(), 45, 359, max_step_deg=10)
        self.assertAlmostEqual(u, 45)
        self.assertAlmostEqual(v, 361)

    def test_1000_normals_align_to_positive_z(self):
        rng = random.Random(20)
        for _ in range(1000):
            config = profile()
            config = replace(
                config, u=replace(config.u, sign=rng.choice((-1, 1))),
                v=replace(config.v, sign=rng.choice((-1, 1))),
            )
            n = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(.1, 1))
            u, v = normal_to_uv(n, config, 0, 0, max_step_deg=180)
            aligned = rx(rz(n, config.v.radians(v)), config.u.radians(u))
            self.assertLess(math.hypot(aligned.x, aligned.y), 1e-9)
            self.assertAlmostEqual(aligned.z, n.norm(), places=9)

    def test_angle_limit_can_choose_other_branch(self):
        config = profile()
        config = replace(config, u=replace(config.u, limits_deg=Interval(-95, 1)))
        u, _ = normal_to_uv(Vec3(0, 1, 1), config, 0, 0, max_step_deg=180)
        self.assertLess(u, 0)


class GHXTests(unittest.TestCase):
    def test_dtd_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.ghx"
            path.write_text('<!DOCTYPE x [<!ENTITY evil "x">]><Archive/>')
            with self.assertRaises(ConfigurationError):
                inspect_ghx(path)

    def test_embedded_script_is_only_data(self):
        xml = """<Archive><chunk name="DefinitionObjects"><chunks><chunk name="Object" index="0">
        <chunks><chunk name="Container"><items>
        <item name="Name">C# Script</item><item name="InstanceGuid">abc</item>
        <item name="ScriptSource">throw new Exception("must not execute");</item>
        </items></chunk></chunks></chunk></chunks></chunk></Archive>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.ghx"
            path.write_text(xml)
            report = inspect_ghx(path)
            self.assertFalse(report["embedded_code_executed"])
            self.assertIn("throw", report["objects"][0]["values"]["ScriptSource"])

    def test_invalid_xml_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.ghx"
            path.write_text("<broken")
            with self.assertRaises(ConfigurationError):
                inspect_ghx(path)


class CaptureTests(unittest.TestCase):
    @staticmethod
    def tree(values):
        return SimpleNamespace(Branches=[values], Paths=[SimpleNamespace(Indices=[0, 7])])

    def setUp(self):
        spec = importlib.util.spec_from_file_location("authored_capture", ROOT / "bridges/ghpython_capture.py")
        self.bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bridge)
        normal = SimpleNamespace(X=0, Y=0, Z=1)
        planes = [
            SimpleNamespace(Origin=SimpleNamespace(X=x, Y=0, Z=1), ZAxis=normal) for x in (0, 1)
        ]
        self.data = json.loads(self.bridge.capture(
            self.tree(planes), self.tree([0, 1]), self.tree([0]), self.tree([0]), "mm"
        ))

    def test_capture_preserves_branch_without_automatic_alignment(self):
        report = inspect_capture(self.data)
        self.assertEqual(report["counts"]["planes"], 2)
        self.assertEqual(report["branch_paths"]["planes"], [[0, 7]])
        self.assertFalse(report["automatic_job_conversion_allowed"])

    def test_flattened_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.bridge.capture([], [], [], [], "mm")

    def test_units_must_be_explicit(self):
        with self.assertRaises(ValueError):
            self.bridge.capture([], [], [], [], "inch")

    def test_zero_normal_rejected(self):
        data = copy.deepcopy(self.data)
        data["planes"][0]["items"][0]["normal"] = [0, 0, 0]
        with self.assertRaises(ConfigurationError):
            inspect_capture(data)

    def test_duplicated_branches_rejected(self):
        self.data["planes"].append(copy.deepcopy(self.data["planes"][0]))
        with self.assertRaises(ConfigurationError):
            inspect_capture(self.data)

    def test_forged_alignment_flag_not_accepted(self):
        self.data["alignment_confirmed"] = True
        with self.assertRaises(ConfigurationError):
            inspect_capture(self.data)
