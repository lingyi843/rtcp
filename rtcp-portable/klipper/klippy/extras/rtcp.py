"""Portable common-pivot RTCP adapter for the native CoreXY U/V kinematics.

Logical G-code coordinates are the workload/platform coordinates at U=V=0.
The adapter converts them to physical machine XYZ using:

    physical_xyz = pivot + Rx(U) * Rz(V) * (logical_xyz + work_offset)

U and V are controller joint angles in degrees.  Their signs and zero angles
are configuration, not inferred from the G-code axis names.
"""
import logging
import math


def _finite(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("%s must be finite" % label) from exc
    if not math.isfinite(result):
        raise ValueError("%s must be finite" % label)
    return result


def _copy_coord(coord):
    return [_finite(value, "coordinate") for value in coord]


class RTCPGeometry:
    def __init__(self, pivot, offset, u_sign, u_zero_deg,
                 v_sign, v_zero_deg):
        self.pivot = tuple(_finite(v, "pivot") for v in pivot)
        self.offset = tuple(_finite(v, "offset") for v in offset)
        self.u_sign = int(u_sign)
        self.v_sign = int(v_sign)
        self.u_zero_deg = _finite(u_zero_deg, "u_zero_deg")
        self.v_zero_deg = _finite(v_zero_deg, "v_zero_deg")
        if len(self.pivot) != 3 or len(self.offset) != 3:
            raise ValueError("pivot and offset require three coordinates")
        if self.u_sign not in (-1, 1) or self.v_sign not in (-1, 1):
            raise ValueError("u_sign and v_sign must be +1 or -1")

    def relative_radians(self, u_deg, v_deg):
        u = math.radians(
            self.u_sign * (_finite(u_deg, "U") - self.u_zero_deg))
        v = math.radians(
            self.v_sign * (_finite(v_deg, "V") - self.v_zero_deg))
        return u, v

    def forward_xyz(self, xyz, u_deg, v_deg):
        """Convert logical workpiece XYZ to physical machine XYZ."""
        x, y, z = (
            _finite(xyz[0], "X") + self.offset[0],
            _finite(xyz[1], "Y") + self.offset[1],
            _finite(xyz[2], "Z") + self.offset[2],
        )
        u, v = self.relative_radians(u_deg, v_deg)
        cv, sv = math.cos(v), math.sin(v)
        x, y = cv * x - sv * y, sv * x + cv * y
        cu, su = math.cos(u), math.sin(u)
        y, z = cu * y - su * z, su * y + cu * z
        return (
            self.pivot[0] + x,
            self.pivot[1] + y,
            self.pivot[2] + z,
        )

    def inverse_xyz(self, xyz, u_deg, v_deg):
        """Convert physical machine XYZ back to logical workpiece XYZ."""
        x = _finite(xyz[0], "X") - self.pivot[0]
        y = _finite(xyz[1], "Y") - self.pivot[1]
        z = _finite(xyz[2], "Z") - self.pivot[2]
        u, v = self.relative_radians(u_deg, v_deg)
        cu, su = math.cos(-u), math.sin(-u)
        y, z = cu * y - su * z, su * y + cu * z
        cv, sv = math.cos(-v), math.sin(-v)
        x, y = cv * x - sv * y, sv * x + cv * y
        return (
            x - self.offset[0],
            y - self.offset[1],
            z - self.offset[2],
        )

    def physical_position(self, logical_position):
        position = _copy_coord(logical_position)
        if len(position) < 6:
            raise ValueError("RTCP position requires XYZ,E,U,V")
        position[:3] = self.forward_xyz(
            position[:3], position[4], position[5])
        return position

    def logical_position(self, physical_position):
        position = _copy_coord(physical_position)
        if len(position) < 6:
            raise ValueError("RTCP position requires XYZ,E,U,V")
        position[:3] = self.inverse_xyz(
            position[:3], position[4], position[5])
        return position

    def chord_bound_mm(self, start, end):
        """Conservative bound for the transformed path's chord error."""
        du = abs(_finite(end[4], "U") - _finite(start[4], "U"))
        dv = abs(_finite(end[5], "V") - _finite(start[5], "V"))
        s = math.radians(du + dv)
        radius = max(
            math.sqrt(sum((_finite(v, "xyz") + offset) ** 2
                          for v, offset in zip(pos[:3], self.offset)))
            for pos in (start, end)
        )
        travel = math.sqrt(sum(
            (_finite(b, "xyz") - _finite(a, "xyz")) ** 2
            for a, b in zip(start[:3], end[:3])))
        return (s * s * radius + 2.0 * s * travel) / 8.0


def plan_logical_segments(geometry, start, end, tolerance_mm,
                          max_depth, max_segments,
                          xyz_limits=None, u_limits=None, v_limits=None):
    """Return logical XYZUV/E endpoints with bounded RTCP chord error.

    The complete segment list is built before the caller submits any motion.
    Any geometry, limit, or budget error rejects the whole G1 line.
    """
    start = _copy_coord(start)
    end = _copy_coord(end)
    if len(start) != len(end) or len(start) < 6:
        raise ValueError("RTCP start/end positions must have matching size >= 6")
    tolerance_mm = _finite(tolerance_mm, "chord_tolerance_mm")
    if tolerance_mm <= 0.0:
        raise ValueError("chord_tolerance_mm must be positive")
    if type(max_depth) is not int or not 1 <= max_depth <= 24:
        raise ValueError("max_depth must be an integer in [1, 24]")
    if type(max_segments) is not int or not 1 <= max_segments <= 1000000:
        raise ValueError("max_segments is outside the supported range")

    def interpolate(t):
        return [a + (b - a) * t for a, b in zip(start, end)]

    def check(position):
        u, v = position[4], position[5]
        if u_limits is not None and not u_limits[0] <= u <= u_limits[1]:
            raise ValueError("U %.6g outside %.6g..%.6g"
                             % (u, u_limits[0], u_limits[1]))
        if v_limits is not None and not v_limits[0] <= v <= v_limits[1]:
            raise ValueError("V %.6g outside %.6g..%.6g"
                             % (v, v_limits[0], v_limits[1]))
        physical = geometry.forward_xyz(position[:3], u, v)
        if xyz_limits is not None:
            for axis, value, limits in zip("XYZ", physical, xyz_limits):
                if not limits[0] <= value <= limits[1]:
                    raise ValueError(
                        "%s %.6g outside %.6g..%.6g"
                        % (axis, value, limits[0], limits[1]))
        return physical

    nodes = [0.0]
    errors = []
    visited = 0
    first_physical = check(start)
    last_physical = check(end)

    def recurse(t0, p0, t1, p1, physical0, physical1, depth):
        nonlocal visited
        visited += 1
        if visited > 2 * max_segments:
            raise ValueError("RTCP subdivision work budget exhausted")
        error = geometry.chord_bound_mm(p0, p1)
        inside = True
        if xyz_limits is not None:
            inside = all(
                min(a, b) - error >= limits[0]
                and max(a, b) + error <= limits[1]
                for a, b, limits in zip(
                    physical0, physical1, xyz_limits))
        if error <= tolerance_mm and inside:
            if len(errors) >= max_segments:
                raise ValueError("RTCP max_segments exceeded")
            nodes.append(t1)
            errors.append(error)
            return
        if depth >= max_depth:
            raise ValueError("RTCP cannot certify segment within max_depth")
        tm = (t0 + t1) * 0.5
        pm = interpolate(tm)
        physicalm = check(pm)
        recurse(t0, p0, tm, pm, physical0, physicalm, depth + 1)
        recurse(tm, pm, t1, p1, physicalm, physical1, depth + 1)

    recurse(0.0, start, 1.0, end,
            first_physical, last_physical, 0)
    return [interpolate(t) for t in nodes[1:]], errors


class RTCP:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object("gcode")
        self.pivot = (
            config.getfloat("pivot_x", 0.0),
            config.getfloat("pivot_y", 0.0),
            config.getfloat("pivot_z", 0.0),
        )
        self.offset = (
            config.getfloat("offset_x", 0.0),
            config.getfloat("offset_y", 0.0),
            config.getfloat("offset_z", 0.0),
        )
        self.u_sign = config.getint("u_sign", 1, minval=-1, maxval=1)
        self.v_sign = config.getint("v_sign", 1, minval=-1, maxval=1)
        if self.u_sign not in (-1, 1) or self.v_sign not in (-1, 1):
            raise config.error("rtcp: u_sign/v_sign must be +1 or -1")
        self.u_zero_deg = config.getfloat("u_zero_deg", 0.0)
        self.v_zero_deg = config.getfloat("v_zero_deg", 0.0)
        self.u_min = config.getfloat("u_min_deg", -90.0)
        self.u_max = config.getfloat("u_max_deg", 90.0)
        self.v_min = config.getfloat("v_min_deg", -720.0)
        self.v_max = config.getfloat("v_max_deg", 720.0)
        if self.u_min >= self.u_max or self.v_min >= self.v_max:
            raise config.error("rtcp: invalid U/V limits")
        self.chord_tolerance_mm = config.getfloat(
            "chord_tolerance_mm", 0.02, above=0.0)
        self.max_depth = config.getint(
            "max_depth", 20, minval=1, maxval=24)
        self.max_segments = config.getint(
            "max_segments", 100000, minval=1, maxval=1000000)
        self.require_no_work_offsets = config.getboolean(
            "require_no_work_offsets", True)
        self.geometry = self._geometry()
        self.active = False
        self.reason = "disabled"
        self.enable_count = 0
        self.last_segments = 0
        self.last_error_bound_mm = 0.0
        self.gcode.register_command(
            "RTCP_ENABLE", self.cmd_RTCP_ENABLE,
            desc="Enable workpiece-coordinate RTCP transformation")
        self.gcode.register_command(
            "RTCP_DISABLE", self.cmd_RTCP_DISABLE,
            desc="Disable RTCP at a motion-queue boundary")
        self.gcode.register_command(
            "RTCP_STATUS", self.cmd_RTCP_STATUS,
            desc="Report RTCP state and current transformations")
        self.gcode.register_command(
            "RTCP_SET_OFFSET", self.cmd_RTCP_SET_OFFSET,
            desc="Set RTCP workpiece offset while RTCP is disabled")
        for event in (
                "klippy:shutdown", "stepper_enable:motor_off",
                "homing:home_rails_begin", "toolhead:set_position"):
            self.printer.register_event_handler(event, self._invalidate)

    def _geometry(self):
        return RTCPGeometry(
            self.pivot, self.offset, self.u_sign, self.u_zero_deg,
            self.v_sign, self.v_zero_deg)

    def _toolhead(self):
        return self.printer.lookup_object("toolhead")

    def _gcode_move(self):
        return self.printer.lookup_object("gcode_move")

    def _invalidate(self, *args):
        if not self.active:
            return
        self.active = False
        self.reason = "invalidated by machine state change"
        try:
            physical = self._toolhead().get_position()
            self._gcode_move().last_position = list(physical)
        except Exception:
            logging.exception("Unable to resynchronize G-code position after RTCP invalidation")
        logging.warning("RTCP disabled: %s", self.reason)

    def _check_enable_conditions(self):
        toolhead = self._toolhead()
        move = self._gcode_move()
        status = toolhead.get_status(self.printer.get_reactor().monotonic())
        if not all(axis in status.get("homed_axes", "") for axis in "xyz"):
            raise self.printer.command_error(
                "RTCP_ENABLE requires XYZ homed")
        for axis in "uv":
            rotary = self.printer.lookup_object("stepper_" + axis, None)
            if rotary is None:
                raise self.printer.command_error(
                    "RTCP_ENABLE requires native stepper_%s" % axis)
            if not rotary.get_status().get("referenced", False):
                raise self.printer.command_error(
                    "RTCP_ENABLE requires HOME_%s or SET_%s"
                    % (axis.upper(), axis.upper()))
        current = toolhead.get_position()
        if not self.u_min <= current[4] <= self.u_max:
            raise self.printer.command_error(
                "RTCP_ENABLE: U %.6f outside configured limits" % current[4])
        if not self.v_min <= current[5] <= self.v_max:
            raise self.printer.command_error(
                "RTCP_ENABLE: V %.6f outside configured limits" % current[5])
        for axis, value, limits in zip("XYZ", current[:3], self._limits()):
            if not limits[0] <= value <= limits[1]:
                raise self.printer.command_error(
                    "RTCP_ENABLE: %s %.6f outside soft limits"
                    % (axis, value))
        if move.move_transform is not None:
            raise self.printer.command_error(
                "RTCP_ENABLE requires no G-code move transform/bed mesh")
        if self.require_no_work_offsets:
            if any(abs(value) > 1e-9
                   for value in move.base_position[:3]):
                raise self.printer.command_error(
                    "RTCP_ENABLE requires zero XYZ G-code base offset")
            if any(abs(value) > 1e-9
                   for value in move.homing_position[:3]):
                raise self.printer.command_error(
                    "RTCP_ENABLE requires zero XYZ homing offset")

    def _limits(self):
        status = self._toolhead().get_status(
            self.printer.get_reactor().monotonic())
        xyz = [(status["axis_minimum"][i], status["axis_maximum"][i])
               for i in range(3)]
        return xyz

    def segment_positions(self, start, end):
        if not self.active:
            return [list(end)], []
        nodes, errors = plan_logical_segments(
            self.geometry, start, end, self.chord_tolerance_mm,
            self.max_depth, self.max_segments, self._limits(),
            (self.u_min, self.u_max), (self.v_min, self.v_max))
        self.last_segments = len(nodes)
        self.last_error_bound_mm = max(errors, default=0.0)
        return nodes, errors

    def physical_position(self, logical_position):
        return self.geometry.physical_position(logical_position)

    def logical_position(self, physical_position):
        return self.geometry.logical_position(physical_position)

    def cmd_RTCP_ENABLE(self, gcmd):
        if self.active:
            gcmd.respond_info("RTCP already active")
            return
        toolhead = self._toolhead()
        toolhead.wait_moves()
        self._check_enable_conditions()
        physical = toolhead.get_position()
        logical = self.logical_position(physical)
        self.geometry = self._geometry()
        # Validate both directions before committing the mode change.
        roundtrip = self.geometry.physical_position(logical)
        if max(abs(a - b) for a, b in zip(roundtrip[:3], physical[:3])) > 1e-6:
            raise gcmd.error("RTCP inverse/forward validation failed")
        self._gcode_move().last_position = list(logical)
        self.active = True
        self.reason = "active"
        self.enable_count += 1
        gcmd.respond_info(
            "RTCP active: logical XYZ is relative to rotation center; "
            "U/V remain machine joint angles")

    def cmd_RTCP_DISABLE(self, gcmd):
        if not self.active:
            gcmd.respond_info("RTCP already disabled: %s" % self.reason)
            return
        toolhead = self._toolhead()
        toolhead.wait_moves()
        physical = toolhead.get_position()
        self._gcode_move().last_position = list(physical)
        self.active = False
        self.reason = "disabled at queue boundary"
        gcmd.respond_info("RTCP disabled; G-code position now uses machine XYZ")

    def cmd_RTCP_SET_OFFSET(self, gcmd):
        if self.active:
            raise gcmd.error("RTCP_SET_OFFSET requires RTCP disabled")
        self._toolhead().wait_moves()
        offset = list(self.offset)
        for index, axis in enumerate("XYZ"):
            offset[index] = gcmd.get_float(axis, offset[index])
        self.offset = tuple(offset)
        self.geometry = self._geometry()
        gcmd.respond_info(
            "RTCP work offset set to X%.6f Y%.6f Z%.6f (not persisted)"
            % self.offset)

    def cmd_RTCP_STATUS(self, gcmd):
        move = self._gcode_move()
        gcmd.respond_info(
            "RTCP active=%s reason=%s enables=%d segments=%d "
            "pivot=(%.6f,%.6f,%.6f) offset=(%.6f,%.6f,%.6f) "
            "gcode=%s"
            % (int(self.active), self.reason, self.enable_count,
               self.last_segments, *self.pivot, *self.offset,
               move.last_position))

    def check_command(self, command):
        if not self.active:
            return
        denied = {
            "G28", "G29", "G30", "G32", "G92",
            "PROBE", "SET_KINEMATIC_POSITION", "FORCE_MOVE",
            "MANUAL_STEPPER", "SET_U", "SET_V", "SET_GCODE_OFFSET",
            "M18", "M84", "QUAD_GANTRY_LEVEL", "Z_TILT_ADJUST",
            "BED_MESH_CALIBRATE",
        }
        denied_prefixes = (
            "HOME_", "LASER_", "EDDY_", "U_FOUR_Z", "TRAM_",
            "SET_X", "SET_Y", "SET_Z", "UV_JOG", "UV_ASSUME_ZERO",
            "FULL_HOME", "PRINT_PREPARE",
        )
        if command in denied or command.startswith(denied_prefixes):
            raise self.printer.command_error(
                "Command %s is blocked while RTCP is active; "
                "finish at a queue boundary and run RTCP_DISABLE" % command)

    def get_status(self, eventtime=None):
        return {
            "active": self.active,
            "reason": self.reason,
            "pivot_mm": list(self.pivot),
            "offset_mm": list(self.offset),
            "u_sign": self.u_sign,
            "v_sign": self.v_sign,
            "u_zero_deg": self.u_zero_deg,
            "v_zero_deg": self.v_zero_deg,
            "chord_tolerance_mm": self.chord_tolerance_mm,
            "last_segments": self.last_segments,
            "last_error_bound_mm": self.last_error_bound_mm,
        }


def load_config(config):
    return RTCP(config)
