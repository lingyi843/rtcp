import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "klipper/klippy/extras/rtcp.py"
SPEC = importlib.util.spec_from_file_location("klipper_rtcp", MODULE_PATH)
rtcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rtcp)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometry = rtcp.RTCPGeometry(
            pivot=(0.0, 0.0, 0.0),
            offset=(2.0, -3.0, 0.0),
            u_sign=1,
            u_zero_deg=0.0,
            v_sign=1,
            v_zero_deg=0.0,
        )

    def test_zero_pose_keeps_machine_xyz(self):
        self.assertEqual(
            self.geometry.forward_xyz((10.0, 20.0, 30.0), 0.0, 0.0),
            (12.0, 17.0, 30.0),
        )

    def test_u_rotates_about_x(self):
        actual = self.geometry.forward_xyz((0.0, 3.0, 0.0), 90.0, 0.0)
        for value, expected in zip(actual, (2.0, 0.0, 0.0)):
            self.assertAlmostEqual(value, expected, places=12)

    def test_v_is_inner_axis_about_z(self):
        actual = self.geometry.forward_xyz((10.0, 0.0, 0.0), 90.0, 90.0)
        for value, expected in zip(actual, (3.0, 0.0, 12.0)):
            self.assertAlmostEqual(value, expected, places=12)

    def test_inverse_round_trip(self):
        physical = self.geometry.forward_xyz((31.0, -17.0, 8.0), 37.0, -125.0)
        logical = self.geometry.inverse_xyz(physical, 37.0, -125.0)
        for value, expected in zip(logical, (31.0, -17.0, 8.0)):
            self.assertAlmostEqual(value, expected, places=10)

    def test_signed_configuration(self):
        signed = rtcp.RTCPGeometry(
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
            -1, 0.0, -1, 0.0)
        actual = signed.forward_xyz((5.0, 0.0, 0.0), 90.0, 90.0)
        for value, expected in zip(actual, (0.0, 0.0, 5.0)):
            self.assertAlmostEqual(value, expected, places=12)


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.geometry = rtcp.RTCPGeometry(
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
            1, 0.0, 1, 0.0)

    def test_pure_translation_uses_one_segment(self):
        start = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [100.0, 20.0, 5.0, 10.0, 0.0, 0.0]
        nodes, errors = rtcp.plan_logical_segments(
            self.geometry, start, end, 0.02, 20, 100000)
        self.assertEqual(nodes, [end])
        self.assertEqual(errors, [0.0])

    def test_rotary_arc_is_subdivided(self):
        start = [50.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [50.0, 0.0, 0.0, 20.0, 0.0, 90.0]
        nodes, errors = rtcp.plan_logical_segments(
            self.geometry, start, end, 0.02, 20, 100000)
        self.assertGreater(len(nodes), 2)
        self.assertLessEqual(max(errors), 0.02)
        self.assertEqual(nodes[-1], end)

    def test_multi_turn_is_not_lost(self):
        start = [50.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [50.0, 0.0, 0.0, 0.0, 0.0, 720.0]
        nodes, errors = rtcp.plan_logical_segments(
            self.geometry, start, end, 0.02, 20, 100000)
        self.assertGreater(len(nodes), 100)
        self.assertLessEqual(max(errors), 0.02)

    def test_extrusion_is_distributed_linearly(self):
        start = [50.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [50.0, 0.0, 0.0, 24.0, 0.0, 180.0]
        nodes, _ = rtcp.plan_logical_segments(
            self.geometry, start, end, 0.02, 20, 100000)
        fractions = [(node[5] / 180.0, node[3] / 24.0)
                     for node in nodes]
        for v_fraction, e_fraction in fractions:
            self.assertAlmostEqual(v_fraction, e_fraction, places=10)

    def test_budget_rejection_is_complete(self):
        start = [50.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [50.0, 0.0, 0.0, 0.0, 0.0, 720.0]
        with self.assertRaises(ValueError):
            rtcp.plan_logical_segments(
                self.geometry, start, end, 0.000001, 20, 20)

    def test_rotary_limit_rejects_before_submission(self):
        start = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        end = [0.0, 0.0, 0.0, 0.0, 95.0, 0.0]
        with self.assertRaises(ValueError):
            rtcp.plan_logical_segments(
                self.geometry, start, end, 0.02, 20, 100000,
                u_limits=(-90.0, 90.0))


class FakePrinter:
    command_error = ValueError

    def __init__(self, objects):
        self.objects = objects

    def lookup_object(self, name, default=None):
        if name == "gcode":
            return self.objects["gcode"]
        return self.objects.get(name, default)

    def register_event_handler(self, event, handler):
        pass

    def get_reactor(self):
        class Reactor:
            @staticmethod
            def monotonic():
                return 0.0
        return Reactor()


class FakeConfig:
    def __init__(self, printer):
        self.printer = printer

    def get_printer(self):
        return self.printer

    def getfloat(self, name, default=None, **kwargs):
        values = {
            "pivot_x": 0.0, "pivot_y": 0.0, "pivot_z": 0.0,
            "offset_x": 0.0, "offset_y": 0.0, "offset_z": 0.0,
            "u_zero_deg": 0.0, "v_zero_deg": 0.0,
            "u_min_deg": -90.0, "u_max_deg": 90.0,
            "v_min_deg": -720.0, "v_max_deg": 720.0,
            "chord_tolerance_mm": 0.02,
        }
        return values.get(name, default)

    def getint(self, name, default=None, **kwargs):
        return {"u_sign": 1, "v_sign": 1,
                "max_depth": 20, "max_segments": 100000}.get(name, default)

    def getboolean(self, name, default=None):
        return default


class FakeGcode:
    def __init__(self):
        self.commands = {}

    def register_command(self, name, handler, desc=None):
        self.commands[name] = handler


class FakeMove:
    def __init__(self, position):
        self.last_position = list(position)
        self.base_position = [0.0] * 6
        self.homing_position = [0.0] * 6
        self.move_transform = None


class FakeToolhead:
    def __init__(self, position):
        self.position = list(position)

    def get_position(self):
        return list(self.position)

    def wait_moves(self):
        pass

    def get_status(self, eventtime=None):
        return {
            "homed_axes": "xyz",
            "axis_minimum": [-300.0, -300.0, -300.0, 0.0],
            "axis_maximum": [300.0, 300.0, 300.0, 0.0],
        }


class FakeRotary:
    def get_status(self):
        return {"referenced": True}


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.gcode = FakeGcode()
        self.move = FakeMove([10.0, 20.0, 30.0, 0.0, 0.0, 0.0])
        self.toolhead = FakeToolhead(self.move.last_position)
        self.objects = {
            "gcode": self.gcode,
            "gcode_move": self.move,
            "toolhead": self.toolhead,
            "stepper_u": FakeRotary(),
            "stepper_v": FakeRotary(),
        }
        self.instance = rtcp.RTCP(FakeConfig(FakePrinter(self.objects)))

    def test_enable_disable_preserves_physical_pose(self):
        result = {}
        self.instance.cmd_RTCP_ENABLE(type("G", (), {
            "respond_info": lambda self, message: result.setdefault("info", message),
            "error": ValueError,
        })())
        self.assertTrue(self.instance.active)
        self.assertEqual(self.move.last_position, self.toolhead.get_position())
        self.instance.cmd_RTCP_DISABLE(type("G", (), {
            "respond_info": lambda self, message: result.setdefault("off", message),
        })())
        self.assertFalse(self.instance.active)
        self.assertEqual(self.move.last_position, self.toolhead.get_position())

    def test_active_guard_blocks_reference_and_allows_motion(self):
        self.instance.active = True
        self.instance.check_command("G1")
        with self.assertRaises(ValueError):
            self.instance.check_command("G28")
        with self.assertRaises(ValueError):
            self.instance.check_command("LASER_U_LEVEL")

    def test_active_g1_builds_segments_before_submission(self):
        self.instance.active = True
        end = [40.0, 20.0, 30.0, 4.0, 0.0, 90.0]
        nodes, errors = self.instance.segment_positions(
            self.move.last_position, end)
        self.assertGreater(len(nodes), 1)
        self.assertEqual(nodes[-1], end)
        self.assertLessEqual(max(errors), 0.02)
        self.assertEqual(self.instance.last_segments, len(nodes))


if __name__ == "__main__":
    unittest.main()
