from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from rtcp_portable.audit import audit_snapshot
from rtcp_portable.cli import main, read_json, simulate
from rtcp_portable.errors import ConfigurationError

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def call(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_selfcheck(self):
        code, out, _ = self.call(["selfcheck"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])

    def test_validate_template_refused(self):
        code, _, err = self.call(["validate", str(ROOT / "profiles/machine.template.json")])
        self.assertEqual(code, 2)
        self.assertIn("rejected", err)

    def test_simulation_is_explicitly_not_executable(self):
        report = simulate(ROOT / "profiles/simulation.json", ROOT / "examples/arc.json")
        self.assertFalse(report["live_supported"])
        self.assertFalse(report["executable_gcode"])
        self.assertGreater(report["segment_count"], 2)
        self.assertLessEqual(report["max_error_bound_mm"], .02)
        self.assertEqual(len(report["profile_sha256"]), 64)

    def test_output_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            output.write_text("preserve me", encoding="utf-8")
            code, _, _ = self.call(["selfcheck", "--output", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(output.read_text(), "preserve me")

    def test_new_output_is_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            code, _, _ = self.call(["selfcheck", "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.read_text())["offline_only"])

    def test_duplicate_and_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ConfigurationError):
                    read_json(path)

    def test_job_missing_fields_and_legacy_aliases_rejected(self):
        original = json.loads((ROOT / "examples/arc.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for field in ("xyz_mm", "u_deg", "v_deg"):
                data = copy.deepcopy(original)
                del data["points"][0][field]
                data["points"][0]["a_deg"] = 0
                path.write_text(json.dumps(data))
                with self.subTest(field=field), self.assertRaises(ConfigurationError):
                    simulate(ROOT / "profiles/simulation.json", path)

    def test_arbitrary_tilt_vision_frame_rejected(self):
        data = json.loads((ROOT / "examples/arc.json").read_text())
        data["registration"]["frame"] = "camera_at_arbitrary_tilt"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ConfigurationError):
                simulate(ROOT / "profiles/simulation.json", path)

    def test_unsupported_extrusion_and_feed_fields_rejected(self):
        original = json.loads((ROOT / "examples/arc.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for field in ("e_mm", "feed_mm_min"):
                data = copy.deepcopy(original)
                data["points"][0][field] = 10
                path.write_text(json.dumps(data))
                with self.subTest(field=field), self.assertRaises(ConfigurationError):
                    simulate(ROOT / "profiles/simulation.json", path)

    def test_missing_input_returns_readable_error(self):
        code, _, err = self.call(["validate", str(ROOT / "not-present.json")])
        self.assertEqual(code, 2)
        self.assertIn("rejected", err)

    def test_timing_command_requires_and_records_explicit_offset(self):
        code, out, _ = self.call([
            "plan-timing", str(ROOT / "profiles/simulation.json"),
            str(ROOT / "profiles/timing.simulation.json"), str(ROOT / "examples/timed-job.json"),
            "--offset", "5", "-3", "0",
        ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["registration_offset_mm"], [5, -3, 0])
        self.assertFalse(result["live_supported"])
        self.assertEqual(len(result["job_sha256"]), 64)

    def test_capture_command_never_approves_automatic_conversion(self):
        code, out, _ = self.call(["inspect-capture", str(ROOT / "examples/preik-capture.json")])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["automatic_job_conversion_allowed"])

    def test_gcode_command_only_audits_external_macro(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macro.gcode"
            path.write_text('M98 P"/macros/never_execute.g"\n')
            code, out, _ = self.call(["audit-gcode", str(path)])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["automatic_rtcp_import_allowed"])


class AuditTests(unittest.TestCase):
    def test_missing_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConfigurationError):
                audit_snapshot(Path(directory))

    def test_static_scan_does_not_execute_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source").mkdir()
            (root / "config").mkdir()
            (root / "source/corexy_uv.py").write_text(
                "raise RuntimeError('MUST NOT RUN')\n"
                "def set_reference(self):\n"
                "    self.toolhead.set_extra_axis_position(self, 0)\n"
                "def check_move(self):\n"
                "    pass\n"
            )
            for filename in ("toolhead.py", "force_move.py"):
                (root / "source" / filename).write_text("# offline fixture\n")
            (root / "source/laser_motion.py").write_text(
                "old = 'manual_stepper u'\nvalue = tool.move_generation\n"
            )
            (root / "config/machine_functions.cfg").write_text(
                "[gcode_macro SET_U]\ngcode:\n    SET_KINEMATIC_POSITION U=0 SET_HOMED=u\n"
            )
            (root / "config/printer.cfg").write_text("[stepper_u]\ngear_ratio: 60:16\n")
            result = audit_snapshot(root)
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("missing_reference_host_method", codes)
            self.assertIn("u_gear_mismatch_or_unknown", codes)
            self.assertIn("legacy_laser_generation", codes)
            self.assertFalse(result["deployment_ready"])
            self.assertEqual(len(result["sha256"]), 6)
