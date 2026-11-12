from __future__ import annotations

import json
import math
import secrets
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .moonraker import MachineSnapshot, MoonrakerClient, MoonrakerError
from .pa_flat_v1 import PAFlatV1Error, PAFlatV1Manager
from .path_dry_run import PathDryRunError, PathDryRunManager


class ControlError(RuntimeError):
    status_code = 400


class AuthorizationError(ControlError):
    status_code = 403


class ConflictError(ControlError):
    status_code = 409


@dataclass
class Lease:
    owner: str
    expires_at: float


class LeaseManager:
    def __init__(self, timeout_s: float):
        self.timeout_s = float(timeout_s)
        self.lease: Lease | None = None
        self.lock = threading.Lock()
        self.expired_since_last_check = False

    def _active_unlocked(self) -> Lease | None:
        if self.lease and self.lease.expires_at <= time.monotonic():
            self.lease = None
            self.expired_since_last_check = True
        return self.lease

    def authorize(self, owner: str) -> Lease:
        with self.lock:
            active = self._active_unlocked()
            if active and active.owner != owner:
                raise ConflictError("另一浏览器正在占用运动授权")
            self.lease = Lease(owner, time.monotonic() + self.timeout_s)
            return self.lease

    def require(self, owner: str, *, touch: bool = True) -> Lease:
        with self.lock:
            active = self._active_unlocked()
            if not active or active.owner != owner:
                raise AuthorizationError("当前浏览器没有有效运动授权")
            if touch:
                active.expires_at = time.monotonic() + self.timeout_s
            return active

    def release(self, owner: str | None = None) -> bool:
        with self.lock:
            active = self._active_unlocked()
            if active and (owner is None or active.owner == owner):
                self.lease = None
                return True
            return False

    def public(self, owner: str) -> dict[str, Any]:
        with self.lock:
            active = self._active_unlocked()
            mine = bool(active and active.owner == owner)
            return {
                "authorized": mine,
                "occupied": bool(active and not mine),
                "expires_in_s": (
                    max(0, int(active.expires_at - time.monotonic())) if mine else 0
                ),
            }

    def take_expired(self) -> bool:
        with self.lock:
            expired = self.expired_since_last_check
            self.expired_since_last_check = False
            return expired


class ControlService:
    SERVICE_NAMES = {
        "klipper": "klipper",
        "moonraker": "moonraker",
        "crowsnest": "crowsnest",
        "fusion": "fusion-alignment",
        "vision": "vision_calib",
        "axiscope": "axiscope",
        "scanner3d": "scanner3d",
        "nginx": "nginx",
    }
    def __init__(
        self,
        config: dict[str, Any],
        *,
        moonraker: MoonrakerClient | None = None,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ):
        self.config = config
        self.moon = moonraker or MoonrakerClient(config["moonraker_url"])
        self.lease = LeaseManager(float(config.get("session_timeout_s", 900)))
        self.operation_lock = threading.Lock()
        self._service_cache: tuple[float, dict[str, str]] = (0.0, {})
        self.command_runner = command_runner or subprocess.run
        self.fusion_motion = self._load_fusion_motion()
        self.path_dry_run = PathDryRunManager(config)
        self.pa_flat_v1 = PAFlatV1Manager(config)
        self._remote_full_home_lock = threading.Lock()
        self._remote_full_home_thread: threading.Thread | None = None
        self._remote_full_home_state: dict[str, Any] = {
            "active": False,
            "state": "idle",
            "message": "not run",
            "updated_at": time.time(),
        }
        self._remote_home_u_lock = threading.Lock()
        self._remote_home_u_thread: threading.Thread | None = None
        self._remote_home_u_state: dict[str, Any] = {
            "active": False,
            "state": "idle",
            "message": "not run",
            "updated_at": time.time(),
        }
        self._remote_gantry_survey_lock = threading.Lock()
        self._remote_gantry_survey_thread: threading.Thread | None = None
        self._remote_gantry_survey_state: dict[str, Any] = {
            "active": False,
            "state": "idle",
            "message": "not run",
            "updated_at": time.time(),
        }

    def _load_fusion_motion(self) -> dict[str, Any]:
        path = Path(str(self.config.get("fusion_config_path", "")))
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("motion", {})
        except Exception:
            return {
                "inspection_pose": {"x": -90.0, "y": -30.0, "z": 110.0},
                "safe_xy_min": [-160.0, -130.0],
                "safe_xy_max": [140.0, 180.0],
                "safe_z_min": 80.0,
                "safe_z_max": 150.0,
                "pose_tolerance": {"u_deg": 0.1, "v_deg": 0.1},
            }

    @staticmethod
    def _macro(status: dict[str, Any], name: str) -> dict[str, Any]:
        return status.get(f"gcode_macro {name}", {})

    @classmethod
    def _reference(cls, snapshot: MachineSnapshot) -> dict[str, Any]:
        return cls._macro(snapshot.raw, "_MACHINE_REFERENCE_STATE")

    @classmethod
    def _require_reference(
        cls,
        snapshot: MachineSnapshot,
        *keys: str,
    ) -> dict[str, Any]:
        reference = cls._reference(snapshot)
        missing = [key for key in keys if int(reference.get(key, 0)) != 1]
        if missing:
            raise ConflictError("机器参考状态无效：" + ", ".join(missing))
        return reference

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            return result if math.isfinite(result) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _require_confirm(body: dict[str, Any], key: str = "confirm") -> None:
        if body.get(key) is not True:
            raise ControlError("操作需要明确确认")

    @staticmethod
    def _require_ready(snapshot: MachineSnapshot) -> None:
        if not snapshot.ready:
            raise ConflictError(f"Klipper未就绪：{snapshot.state_message}")

    @staticmethod
    def _require_idle(snapshot: MachineSnapshot) -> None:
        if not snapshot.idle or snapshot.raw.get("pause_resume", {}).get("is_paused"):
            raise ConflictError(f"打印机状态 {snapshot.print_state} 不允许该操作")

    @staticmethod
    def _require_homed(snapshot: MachineSnapshot, axes: str = "xyz") -> None:
        missing = "".join(axis for axis in axes if axis not in snapshot.homed_axes)
        if missing:
            raise ConflictError(f"缺少回零轴：{missing.upper()}")

    def _require_uv_zero(self, snapshot: MachineSnapshot) -> None:
        tolerance = self.fusion_motion.get("pose_tolerance", {})
        u_tol = float(tolerance.get("u_deg", 0.1))
        v_tol = float(tolerance.get("v_deg", 0.1))
        if not snapshot.uv_known:
            raise ConflictError("U/V位置不可用")
        if abs(snapshot.u) > u_tol or abs(snapshot.v) > v_tol:
            raise ConflictError(
                f"U/V必须归零，当前 U={snapshot.u:.3f} V={snapshot.v:.3f}"
            )

    def _require_no_pa_task(self, snapshot: MachineSnapshot) -> None:
        pa = self._macro(snapshot.raw, "_PA_RUNTIME")
        dry = self._macro(snapshot.raw, "_PA_DRY_RUNTIME")
        if int(pa.get("active", 0)) == 1 or int(dry.get("active", 0)) == 1:
            raise ConflictError("PA校准或空走正在运行")

    @staticmethod
    def _laser_measurements(report: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            item
            for item in report.get("history", [])
            if isinstance(item, dict) and item.get("u_error_mm") is not None
        ]

    @classmethod
    def _laser_sensitivity(
        cls, report: dict[str, Any], direction: str
    ) -> float | None:
        profile = report.get("work_z_profile")
        model = report.get("response_model")
        sources = [
            profile if isinstance(profile, dict) else {},
            model if isinstance(model, dict) else {},
        ]
        keys = []
        normalized = str(direction).lower()
        if normalized in {"positive", "negative"}:
            keys.append(
                f"sensitivity_{normalized}_u_error_mm_per_deg"
            )
        keys.extend(
            [
                "sensitivity_u_error_mm_per_deg",
                "sensitivity_y_error_mm_per_deg",
            ]
        )
        for source in sources:
            for key in keys:
                value = cls._number(source.get(key), float("nan"))
                if math.isfinite(value) and abs(value) > 1.0e-9:
                    return value
        return None

    @classmethod
    def _laser_summary(cls, report: dict[str, Any]) -> dict[str, Any]:
        measurements = cls._laser_measurements(report)
        if not measurements:
            raise ControlError("激光程序没有返回可用的扫描测量")
        first = measurements[0]
        last = measurements[-1]
        before = cls._number(
            report.get("before_error_mm", first.get("u_error_mm")),
            float("nan"),
        )
        after = cls._number(
            report.get("after_error_mm", last.get("u_error_mm")),
            float("nan"),
        )
        applied = cls._number(
            report.get("applied_u_correction_deg"), float("nan")
        )
        if not all(math.isfinite(value) for value in (before, after, applied)):
            raise ControlError("激光程序返回的高差或U角度无效")
        direction = str(last.get("direction", ""))
        sensitivity = cls._laser_sensitivity(report, direction)
        residual_u = (
            None
            if sensitivity is None
            else -after / sensitivity
        )
        return {
            "before_height_diff_mm": before,
            "after_height_diff_mm": after,
            "applied_u_deg": applied,
            "residual_u_deg": residual_u,
            "sensitivity_mm_per_deg": sensitivity,
            "coverage_ratio": cls._number(
                last.get(
                    "continuous_span_coverage_ratio",
                    last.get("span_coverage_ratio"),
                ),
                float("nan"),
            ),
            "fit_rms_mm": cls._number(
                last.get("fit_rms_mm"), float("nan")
            ),
            "report_file": str(
                report.get("report_file")
                or report.get("files", {}).get("json", "")
            ),
        }

    def _run_laser_alignment(
        self, scan_z_mm: float | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        settings = self.config.get("laser_alignment", {})
        script = Path(str(settings.get("script", "")))
        if not script.is_file():
            raise ConflictError(f"激光调平程序不存在：{script}")
        configured_scan_z = self._number(settings.get("scan_z_mm"), 90.0)
        selected_scan_z = (
            configured_scan_z
            if scan_z_mm is None
            else self._number(scan_z_mm, float("nan"))
        )
        if not math.isfinite(selected_scan_z) or not 80.0 <= selected_scan_z <= 120.0:
            raise ControlError("G28 U SCAN_Z must be within 80..120 mm")
        command = [
            str(settings.get("python", "/usr/bin/python3")),
            str(script),
            "--alignment-config",
            str(settings.get("alignment_config", script.parent / "alignment_config.json")),
            "--sensor-config",
            str(settings.get("sensor_config", script.parent / "config.json")),
            "--json",
            "--quiet-progress",
            "calibrate-u",
            "--scan-z",
            f"{selected_scan_z:.6f}",
        ]
        try:
            completed = self.command_runner(
                command,
                cwd=str(script.parent),
                capture_output=True,
                text=True,
                timeout=float(settings.get("timeout_s", 420)),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConflictError("激光调平程序运行超时") from exc
        try:
            report = json.loads(completed.stdout or "")
        except Exception as exc:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise ConflictError(
                "激光调平程序没有返回有效报告"
                + (f"：{detail}" if detail else "")
            ) from exc
        result_status = str(report.get("result_status", "")).lower()
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip()
            raise ConflictError(
                f"激光调平程序失败，退出码 {completed.returncode}"
                + (f"：{detail}" if detail else "")
            )
        if result_status != "passed":
            raise ConflictError(
                f"J100 U校准未通过严格验收：{result_status or 'unknown'}"
            )
        return report, self._laser_summary(report)

    def _respond_laser_summary(self, summary: dict[str, Any]) -> None:
        residual = summary.get("residual_u_deg")
        residual_text = (
            "nan" if residual is None else f"{float(residual):.6f}"
        )
        coverage = summary.get("coverage_ratio")
        fit_rms = summary.get("fit_rms_mm")
        coverage_text = (
            "nan"
            if not math.isfinite(self._number(coverage, float("nan")))
            else f"{float(coverage):.6f}"
        )
        rms_text = (
            "nan"
            if not math.isfinite(self._number(fit_rms, float("nan")))
            else f"{float(fit_rms):.6f}"
        )
        self.moon.send_gcode(
            'RESPOND PREFIX="LASER_U_RESULT" MSG="'
            f"before_dZ={summary['before_height_diff_mm']:.6f}mm "
            f"applied_U={summary['applied_u_deg']:.6f}deg "
            f"after_dZ={summary['after_height_diff_mm']:.6f}mm "
            f"residual_U={residual_text}deg "
            f"coverage={coverage_text} fit_rms={rms_text}mm"
            '"'
        )

    def _wait_for_reference(
        self,
        *keys: str,
        timeout_s: float = 60.0,
    ) -> tuple[MachineSnapshot, dict[str, Any]]:
        deadline = time.monotonic() + timeout_s
        last: MachineSnapshot | None = None
        while time.monotonic() < deadline:
            last = self.moon.snapshot()
            reference = self._reference(last)
            if (
                all(int(reference.get(key, 0)) == 1 for key in keys)
                and last.live_velocity <= 0.05
            ):
                return last, reference
            time.sleep(0.1)
        raise MoonrakerError(
            f"Reference state did not become valid: keys={keys}, last={last}"
        )

    def _run_gantry_survey(self) -> dict[str, Any]:
        settings = self.config.get("gantry_survey", {})
        points = settings.get(
            "points",
            [[-70.0, 70.0], [70.0, 70.0], [70.0, -70.0], [-70.0, -70.0]],
        )
        safe_z = self._number(settings.get("safe_print_z_mm"), 5.0)
        if len(points) != 4:
            raise ControlError("gantry_survey requires exactly four points")
        snapshot = self.moon.snapshot()
        self._require_homed(snapshot)
        self._require_reference(
            snapshot,
            "machine_home_valid",
            "u_tram_valid",
            "tap_z_valid",
        )
        measured: list[dict[str, float]] = []
        for point in points:
            x, y = float(point[0]), float(point[1])
            self.moon.send_gcode(
                "G90\n"
                f"G1 Z{safe_z:.4f} F300\n"
                f"G1 X{x:.4f} Y{y:.4f} F6000\n"
                "M400\nQUERY_PROBE",
                timeout_s=120,
            )
            pre = self.moon.wait_settled(
                target=[x, y, safe_z],
                coordinate_space="gcode",
                timeout_s=120,
                tolerance=0.10,
            )
            if bool(pre.raw.get("probe", {}).get("last_query")):
                raise ConflictError("Tap is triggered before a gantry survey probe")
            self.moon.send_gcode("PROBE", timeout_s=120)
            checked = self.moon.wait_settled(
                required_homed="xyz",
                timeout_s=120,
            )
            probe_position = checked.raw.get("probe", {}).get("last_probe_position") or []
            if len(probe_position) < 3:
                raise ConflictError("Tap did not return a valid survey position")
            measured.append(
                {"x": x, "y": y, "machine_z": self._number(probe_position[2])}
            )
        self.moon.send_gcode(
            f"G90\nG1 Z{safe_z:.4f} F300\nM400",
            timeout_s=60,
        )
        self.moon.wait_settled(
            target=[measured[-1]["x"], measured[-1]["y"], safe_z],
            coordinate_space="gcode",
            timeout_s=60,
            tolerance=0.10,
        )
        values = [point["machine_z"] for point in measured]
        span = max(values) - min(values)
        twist = abs((values[0] + values[2]) - (values[1] + values[3])) / 2.0
        return {
            "points": measured,
            "span_mm": span,
            "twist_mm": twist,
            "threshold_mm": self._number(settings.get("qgl_threshold_mm"), 0.08),
        }

    def _full_home_workflow(self) -> dict[str, Any]:
        self.moon.send_gcode("BED_MESH_CLEAR\nMACHINE_HOME", timeout_s=300)
        self.moon.wait_settled(
            required_homed="xyz",
            target=[0.0, 0.0, 105.0],
            coordinate_space="gcode",
            timeout_s=300,
            tolerance=0.35,
        )
        self._wait_for_reference("machine_home_valid", timeout_s=30)

        self.moon.send_gcode("_REFERENCE_U_BEGIN", timeout_s=30)
        report, laser = self._run_laser_alignment()
        self._respond_laser_summary(laser)
        self.moon.send_gcode(
            "UV_REFERENCE_SET AXIS=U POSITION=0\n_REFERENCE_U_SUCCESS",
            timeout_s=60,
        )
        self._wait_for_reference("machine_home_valid", "u_tram_valid", timeout_s=30)

        self.moon.send_gcode("TAP_Z_REFERENCE", timeout_s=300)
        preliminary, reference = self._wait_for_reference(
            "machine_home_valid", "u_tram_valid", "tap_z_valid", timeout_s=300
        )
        survey = self._run_gantry_survey()
        qgl_applied = False
        if float(survey["span_mm"]) > float(survey["threshold_mm"]):
            if int(reference.get("qgl_commissioned", 0)) != 1:
                raise ConflictError(
                    "Gantry span exceeds the QGL threshold but QGL is not commissioned"
                )
            self.moon.send_gcode("MACHINE_QGL", timeout_s=600)
            qgl_applied = True
            self._wait_for_reference(
                "machine_home_valid",
                "u_tram_valid",
                "gantry_tram_valid",
                "tap_z_valid",
                timeout_s=600,
            )
            post_qgl_survey = self._run_gantry_survey()
            post_qgl_limit = self._number(
                self.config.get("gantry_survey", {}).get(
                    "post_qgl_max_span_mm"
                ),
                0.05,
            )
            if float(post_qgl_survey["span_mm"]) > post_qgl_limit:
                raise ConflictError(
                    "Post-QGL gantry span exceeds limit: "
                    f"{post_qgl_survey['span_mm']:.6f} > {post_qgl_limit:.6f} mm"
                )
            survey["post_qgl"] = post_qgl_survey
        else:
            self.moon.send_gcode(
                "_REFERENCE_GANTRY_SUCCESS\nTAP_Z_REFERENCE",
                timeout_s=300,
            )
        checked, final_reference = self._wait_for_reference(
            "machine_home_valid",
            "u_tram_valid",
            "gantry_tram_valid",
            "tap_z_valid",
            timeout_s=600,
        )
        self.moon.send_gcode(
            "G90\nG1 X0 Y0 F6000\nG1 Z15 F300\nM400",
            timeout_s=120,
        )
        checked = self.moon.wait_settled(
            required_homed="xyz",
            target=[0.0, 0.0, 15.0],
            coordinate_space="gcode",
            timeout_s=120,
            tolerance=0.35,
        )
        return {
            "ok": True,
            "result_status": "completed",
            "homed_axes": checked.homed_axes,
            "position": checked.position[:3],
            "laser": laser,
            "survey": survey,
            "qgl_applied": qgl_applied,
            "generation": int(final_reference.get("generation", 0)),
            "bed_machine_z": self._number(final_reference.get("bed_machine_z")),
        }

    def _service_status(self) -> dict[str, str]:
        now = time.monotonic()
        cached_at, cached = self._service_cache
        if now - cached_at < float(self.config.get("service_status_cache_s", 5)):
            return cached
        result: dict[str, str] = {}
        for key, name in self.SERVICE_NAMES.items():
            try:
                completed = self.command_runner(
                    ["systemctl", "is-active", name],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                result[key] = (completed.stdout or "unknown").strip()
            except Exception:
                result[key] = "unknown"
        self._service_cache = (now, result)
        return result

    def status(self, owner: str) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        session_state = self.lease.public(owner)
        self.lease.take_expired()
        raw = snapshot.raw
        reference = self._macro(raw, "_MACHINE_REFERENCE_STATE")
        pa_config = self._macro(raw, "_PA_CONFIG")
        pa_runtime = self._macro(raw, "_PA_RUNTIME")
        dry_runtime = self._macro(raw, "_PA_DRY_RUNTIME")
        saved = raw.get("save_variables", {}).get("variables", {})
        extruder = raw.get("extruder", {})
        bed = raw.get("heater_bed", {})
        fan = raw.get("fan", {})
        sfs = raw.get("filament_motion_sensor encoder_sensor", {})
        rtcp = raw.get("rtcp", {})
        toolhead = raw.get("toolhead", {})
        print_stats = raw.get("print_stats", {})
        virtual_sdcard = raw.get("virtual_sdcard", {})
        limits_min = toolhead.get("axis_minimum") or []
        limits_max = toolhead.get("axis_maximum") or []
        print_filename = str(print_stats.get("filename", ""))
        dry_metadata = self.path_dry_run.metadata_for_filename(print_filename)
        pa_flat_mode = self.pa_flat_v1.mode_for_filename(print_filename)
        path_dry_active = bool(
            dry_metadata
            and snapshot.print_state in {"printing", "paused"}
        )
        pa_flat_active = bool(
            pa_flat_mode and snapshot.print_state in {"printing", "paused"}
        )

        def profile(material: str) -> dict[str, Any]:
            prefix = f"pa_{material.lower()}_"
            return {
                "valid": int(saved.get(prefix + "valid", 0)) == 1,
                "k": self._number(saved.get(prefix + "k")),
                "temperature": self._number(saved.get(prefix + "temp")),
                "revision": str(saved.get(prefix + "revision", "")),
            }

        pa_session = {
            key.removeprefix("pa_session_"): value
            for key, value in saved.items()
            if key.startswith("pa_session_")
        }
        return {
            "ok": True,
            "machine": {
                "state": snapshot.state,
                "state_message": snapshot.state_message,
                "print_state": snapshot.print_state,
                "homed_axes": snapshot.homed_axes,
                "position": {
                    "x": snapshot.position[0],
                    "y": snapshot.position[1],
                    "z": snapshot.position[2],
                    "e": snapshot.position[3],
                    "u": snapshot.u,
                    "v": snapshot.v,
                },
                "coordinates": {
                    "gcode_position": snapshot.position,
                    "toolhead_position": snapshot.toolhead_position,
                    "live_position": snapshot.live_position,
                    "homing_origin": snapshot.homing_origin,
                    "coordinate_offset": snapshot.coordinate_offset,
                },
                "reference": {
                    "machine_home_valid": int(reference.get("machine_home_valid", 0)) == 1,
                    "u_tram_valid": int(reference.get("u_tram_valid", 0)) == 1,
                    "gantry_tram_valid": int(reference.get("gantry_tram_valid", 0)) == 1,
                    "tap_z_valid": int(reference.get("tap_z_valid", 0)) == 1,
                    "mesh_valid": int(reference.get("mesh_valid", 0)) == 1,
                    "qgl_commissioned": int(reference.get("qgl_commissioned", 0)) == 1,
                    "generation": int(reference.get("generation", 0)),
                    "bed_machine_z": self._number(reference.get("bed_machine_z")),
                    "last_stage": str(reference.get("last_stage", "")),
                    "last_result": str(reference.get("last_result", "")),
                },
                "live_velocity": snapshot.live_velocity,
                "limits": {"minimum": limits_min, "maximum": limits_max},
                "extruder": {
                    "temperature": self._number(extruder.get("temperature")),
                    "target": self._number(extruder.get("target")),
                    "can_extrude": bool(extruder.get("can_extrude")),
                },
                "bed": {
                    "available": bool(bed),
                    "temperature": self._number(bed.get("temperature")),
                    "target": self._number(bed.get("target")),
                },
                "fan": {"speed": self._number(fan.get("speed"))},
                "sfs": {
                    "available": bool(sfs),
                    "enabled": bool(sfs.get("enabled")),
                    "filament_detected": bool(sfs.get("filament_detected")),
                    "speed": self._number(sfs.get("measured_speed")),
                    "raw_speed": self._number(sfs.get("raw_speed")),
                    "speed_valid": bool(sfs.get("speed_valid")),
                    "event_count": int(sfs.get("event_count", 0)),
                    "last_event_age": self._number(
                        sfs.get("last_event_age"), -1.0
                    ),
                    "distance_per_event": self._number(
                        sfs.get("speed_distance_per_event")
                    ),
                },
                "rtcp": {
                    "available": bool(rtcp),
                    "active": bool(rtcp.get("active")),
                    "reason": str(rtcp.get("reason", "")),
                    "pivot_mm": list(rtcp.get("pivot_mm") or []),
                    "offset_mm": list(rtcp.get("offset_mm") or []),
                    "last_segments": int(rtcp.get("last_segments", 0)),
                    "last_error_bound_mm": self._number(
                        rtcp.get("last_error_bound_mm")
                    ),
                },
            },
            "session": session_state,
            "pa": {
                "config": pa_config,
                "runtime": pa_runtime,
                "dry_runtime": dry_runtime,
                "profiles": {"PLA": profile("pla"), "PETG": profile("petg")},
                "session": pa_session,
                "applied_k": self._number(extruder.get("pressure_advance")),
                "smooth_time": self._number(extruder.get("smooth_time"), 0.04),
            },
            "path_dry_run": {
                "active": path_dry_active,
                "state": snapshot.print_state if dry_metadata else "standby",
                "filename": print_filename if dry_metadata else "",
                "source": (
                    str(dry_metadata["analysis"]["source"])
                    if dry_metadata
                    else ""
                ),
                "progress": (
                    max(0.0, min(1.0, self._number(virtual_sdcard.get("progress"))))
                    if dry_metadata
                    else 0.0
                ),
                "print_duration_s": (
                    self._number(print_stats.get("print_duration"))
                    if dry_metadata
                    else 0.0
                ),
                "speed_percent": (
                    int(dry_metadata["options"]["speed_percent"])
                    if dry_metadata
                    else 0
                ),
                "z_offset": (
                    self._number(dry_metadata["options"]["z_offset"])
                    if dry_metadata
                    else 0.0
                ),
            },
            "pa_flat_v1": {
                **self.pa_flat_v1.manifest(),
                "active": pa_flat_active,
                "mode": pa_flat_mode or "",
                "filename": print_filename if pa_flat_mode else "",
                "state": snapshot.print_state if pa_flat_mode else "standby",
                "progress": (
                    max(0.0, min(1.0, self._number(virtual_sdcard.get("progress"))))
                    if pa_flat_mode
                    else 0.0
                ),
                "print_duration_s": (
                    self._number(print_stats.get("print_duration"))
                    if pa_flat_mode
                    else 0.0
                ),
            },
            "camera": self.config["camera"],
            "services": self._service_status(),
            "links": self.config["links"],
            "inspection_pose": self.fusion_motion.get(
                "inspection_pose", {"x": -90, "y": -30, "z": 110}
            ),
        }

    def authorize(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        lease = self.lease.authorize(owner)
        return {
            "ok": True,
            "authorized": True,
            "expires_in_s": max(0, int(lease.expires_at - time.monotonic())),
        }

    def lock_session(self, owner: str) -> dict[str, Any]:
        self.lease.release(owner)
        return {"ok": True, "locked": True}

    def emergency_stop(self) -> dict[str, Any]:
        self.lease.release()
        self.moon.emergency_stop()
        return {"ok": True, "message": "急停命令已发送"}

    def firmware_restart(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self.lease.require(owner)
        if body.get("confirm") != "FIRMWARE_RESTART":
            raise ControlError("固件恢复确认文本不正确")
        with self._operation():
            self.moon.send_gcode("FIRMWARE_RESTART", timeout_s=15)
            self.moon.wait_ready(timeout_s=35)
            self.lease.release(owner)
        return {
            "ok": True,
            "message": "Klipper已恢复",
        }

    def _operation(self):
        service = self

        class Guard:
            def __enter__(self):
                if not service.operation_lock.acquire(blocking=False):
                    raise ConflictError("另一项机器操作正在执行")
                return self

            def __exit__(self, exc_type, exc, tb):
                service.operation_lock.release()

        return Guard()

    def _set_remote_full_home_state(
        self,
        state: str,
        message: str,
        *,
        active: bool | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._remote_full_home_lock:
            if active is not None:
                self._remote_full_home_state["active"] = active
            self._remote_full_home_state["state"] = state
            self._remote_full_home_state["message"] = message
            self._remote_full_home_state["updated_at"] = time.time()
            if result is not None:
                self._remote_full_home_state["result"] = result

    def remote_full_home_status(self) -> dict[str, Any]:
        with self._remote_full_home_lock:
            return dict(self._remote_full_home_state)

    def _respond_remote_full_home(
        self,
        message: str,
        *,
        error: bool = False,
    ) -> None:
        safe_message = " ".join(str(message).splitlines())
        safe_message = safe_message.replace("\\", "/").replace('"', "'")
        type_arg = " TYPE=error" if error else ""
        try:
            self.moon.send_gcode(
                f'RESPOND{type_arg} PREFIX="FULL_HOME" MSG="{safe_message}"',
                timeout_s=20,
            )
        except Exception:
            pass

    def request_remote_full_home(self) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        self._require_ready(snapshot)
        self._require_idle(snapshot)
        self._require_no_pa_task(snapshot)
        owner = f"klipper-full-home-{secrets.token_hex(6)}"
        with self._remote_full_home_lock:
            if self._remote_full_home_state.get("active"):
                raise ConflictError("FULL_HOME is already running")
            if self.operation_lock.locked():
                raise ConflictError("another machine operation is running")
            self.lease.authorize(owner)
            self._remote_full_home_state = {
                "active": True,
                "state": "queued",
                "message": "request accepted",
                "updated_at": time.time(),
            }
            worker = threading.Thread(
                target=self._run_remote_full_home,
                args=(owner,),
                name="full-home-workflow",
                daemon=True,
            )
            self._remote_full_home_thread = worker
            worker.start()
        return {"ok": True, "accepted": True}

    def _run_remote_full_home(self, owner: str) -> None:
        try:
            time.sleep(0.25)
            self._respond_remote_full_home(
                "accepted: upper four-Z -> X/Y -> J100 U -> Tap -> survey -> optional QGL -> final Tap"
            )
            self._set_remote_full_home_state(
                "running",
                "machine home, J100, Tap and gantry survey are running",
            )
            result = self.home(
                owner,
                {"mode": "full", "confirm": True},
            )
            self._set_remote_full_home_state(
                "completed",
                "completed at X0 Y0 Z15",
                result=result,
            )
            self._respond_remote_full_home("completed: position X0 Y0 Z15")
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._set_remote_full_home_state("failed", message)
            self._respond_remote_full_home(f"failed: {message}", error=True)
        finally:
            self.lease.release(owner)
            with self._remote_full_home_lock:
                self._remote_full_home_state["active"] = False
                self._remote_full_home_state["updated_at"] = time.time()

    def handle_remote_full_home(self, **_params: Any) -> None:
        try:
            self.request_remote_full_home()
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._set_remote_full_home_state("rejected", message, active=False)
            self._respond_remote_full_home(f"rejected: {message}", error=True)

    def handle_remote_full_home_status(self, **_params: Any) -> None:
        state = self.remote_full_home_status()
        self._respond_remote_full_home(
            f"active={int(bool(state.get('active')))} "
            f"state={state.get('state', 'unknown')} "
            f"message={state.get('message', '')}"
        )

    def _set_remote_gantry_survey_state(
        self,
        state: str,
        message: str,
        *,
        active: bool | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._remote_gantry_survey_lock:
            if active is not None:
                self._remote_gantry_survey_state["active"] = active
            self._remote_gantry_survey_state["state"] = state
            self._remote_gantry_survey_state["message"] = message
            self._remote_gantry_survey_state["updated_at"] = time.time()
            if result is not None:
                self._remote_gantry_survey_state["result"] = result

    def _run_remote_gantry_survey(self, owner: str) -> None:
        try:
            time.sleep(0.25)
            with self._operation():
                snapshot = self._preflight_motion(owner)
                self._require_reference(
                    snapshot,
                    "machine_home_valid",
                    "u_tram_valid",
                    "tap_z_valid",
                )
                self._set_remote_gantry_survey_state("running", "probing four gantry points")
                result = self._run_gantry_survey()
            self._set_remote_gantry_survey_state(
                "completed",
                f"span={result['span_mm']:.6f}mm twist={result['twist_mm']:.6f}mm",
                result=result,
            )
            self.moon.send_gcode(
                'RESPOND PREFIX="GANTRY_SURVEY" '
                f'MSG="span={result["span_mm"]:.6f}mm twist={result["twist_mm"]:.6f}mm"'
            )
        except Exception as exc:
            self._set_remote_gantry_survey_state(
                "failed", f"{type(exc).__name__}: {exc}"
            )
        finally:
            self.lease.release(owner)
            with self._remote_gantry_survey_lock:
                self._remote_gantry_survey_state["active"] = False
                self._remote_gantry_survey_state["updated_at"] = time.time()

    def request_remote_gantry_survey(self) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        self._require_ready(snapshot)
        self._require_idle(snapshot)
        owner = f"klipper-gantry-survey-{secrets.token_hex(6)}"
        with self._remote_gantry_survey_lock:
            if self._remote_gantry_survey_state.get("active"):
                raise ConflictError("GANTRY_SURVEY is already running")
            if self.operation_lock.locked():
                raise ConflictError("another machine operation is running")
            self.lease.authorize(owner)
            self._remote_gantry_survey_state = {
                "active": True,
                "state": "queued",
                "message": "request accepted",
                "updated_at": time.time(),
            }
            worker = threading.Thread(
                target=self._run_remote_gantry_survey,
                args=(owner,),
                name="gantry-survey-workflow",
                daemon=True,
            )
            self._remote_gantry_survey_thread = worker
            worker.start()
        return {"ok": True, "accepted": True}

    def handle_remote_gantry_survey(self, **_params: Any) -> None:
        try:
            self.request_remote_gantry_survey()
        except Exception as exc:
            self._set_remote_gantry_survey_state(
                "rejected", f"{type(exc).__name__}: {exc}", active=False
            )

    def _set_remote_home_u_state(
        self,
        state: str,
        message: str,
        *,
        active: bool | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._remote_home_u_lock:
            if active is not None:
                self._remote_home_u_state["active"] = active
            self._remote_home_u_state["state"] = state
            self._remote_home_u_state["message"] = message
            self._remote_home_u_state["updated_at"] = time.time()
            if result is not None:
                self._remote_home_u_state["result"] = result

    def remote_home_u_status(self) -> dict[str, Any]:
        with self._remote_home_u_lock:
            return dict(self._remote_home_u_state)

    def _respond_remote_home_u(
        self,
        message: str,
        *,
        error: bool = False,
    ) -> None:
        safe_message = " ".join(str(message).splitlines())
        safe_message = safe_message.replace("\\", "/").replace('"', "'")
        type_arg = " TYPE=error" if error else ""
        try:
            self.moon.send_gcode(
                f'RESPOND{type_arg} PREFIX="G28_U" MSG="{safe_message}"',
                timeout_s=20,
            )
        except Exception:
            pass

    def _set_klipper_home_u_job_state(
        self, active: bool, scan_z_mm: float, result: str
    ) -> None:
        command = (
            f"_LASER_U_JOB_BEGIN SCAN_Z={scan_z_mm:.6f}"
            if active
            else f"_LASER_U_JOB_END RESULT={result}"
        )
        self.moon.send_gcode(command, timeout_s=30)

    def request_remote_home_u(
        self, scan_z_mm: Any = None
    ) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        self._require_ready(snapshot)
        self._require_idle(snapshot)
        self._require_no_pa_task(snapshot)
        self._require_homed(snapshot)
        settings = self.config.get("laser_alignment", {})
        selected_scan_z = self._number(
            settings.get("scan_z_mm") if scan_z_mm is None else scan_z_mm,
            float("nan"),
        )
        if not math.isfinite(selected_scan_z) or not 80.0 <= selected_scan_z <= 120.0:
            raise ControlError("G28 U SCAN_Z must be within 80..120 mm")
        owner = f"klipper-home-u-{secrets.token_hex(6)}"
        with self._remote_home_u_lock:
            if self._remote_home_u_state.get("active"):
                raise ConflictError("HOME_U is already running")
            if self.operation_lock.locked():
                raise ConflictError("another machine operation is running")
            self.lease.authorize(owner)
            self._remote_home_u_state = {
                "active": True,
                "state": "queued",
                "message": "request accepted",
                "scan_z_mm": selected_scan_z,
                "updated_at": time.time(),
            }
            worker = threading.Thread(
                target=self._run_remote_home_u,
                args=(owner, selected_scan_z),
                name="home-u-workflow",
                daemon=True,
            )
            self._remote_home_u_thread = worker
            worker.start()
        return {"ok": True, "accepted": True}

    def _run_remote_home_u(self, owner: str, scan_z_mm: float) -> None:
        final_result = "failed"
        try:
            self._set_klipper_home_u_job_state(True, scan_z_mm, "running")
            self._respond_remote_home_u(
                f"accepted: J100 U calibration at Z={scan_z_mm:.3f}"
            )
            self._set_remote_home_u_state(
                "running",
                "J100 U calibration is running",
            )
            result = self.home_u(
                owner, {"confirm": True, "scan_z_mm": scan_z_mm}
            )
            final_result = "passed"
            self._set_remote_home_u_state(
                "completed",
                "J100 U calibration completed",
                result=result,
            )
            self._respond_remote_home_u("completed")
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._set_remote_home_u_state("failed", message)
            self._respond_remote_home_u(f"failed: {message}", error=True)
        finally:
            try:
                self._set_klipper_home_u_job_state(
                    False, scan_z_mm, final_result
                )
            except Exception:
                pass
            self.lease.release(owner)
            with self._remote_home_u_lock:
                self._remote_home_u_state["active"] = False
                self._remote_home_u_state["updated_at"] = time.time()

    def handle_remote_home_u(self, **_params: Any) -> None:
        try:
            self.request_remote_home_u(_params.get("scan_z_mm"))
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._set_remote_home_u_state("rejected", message, active=False)
            self._respond_remote_home_u(f"rejected: {message}", error=True)

    def handle_remote_home_u_status(self, **_params: Any) -> None:
        state = self.remote_home_u_status()
        self._respond_remote_home_u(
            f"active={int(bool(state.get('active')))} "
            f"state={state.get('state', 'unknown')} "
            f"scan_z={self._number(state.get('scan_z_mm'), 90.0):.3f} "
            f"message={state.get('message', '')}"
        )

    def _preflight_motion(self, owner: str) -> MachineSnapshot:
        self.lease.require(owner)
        snapshot = self.moon.snapshot()
        self._require_ready(snapshot)
        self._require_idle(snapshot)
        self._require_no_pa_task(snapshot)
        return snapshot

    def jog(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        axis = str(body.get("axis", "")).lower()
        if axis not in {"x", "y", "z"}:
            raise ControlError("axis必须为x、y或z")
        delta = self._number(body.get("delta_mm"), float("nan"))
        if not math.isfinite(delta) or abs(delta) < 1e-9 or abs(delta) > 10.0:
            raise ControlError("点动距离必须在-10到10 mm之间且不能为0")
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_reference(snapshot, "tap_z_valid")
            self._require_uv_zero(snapshot)
            bounds = self.config["manual_bounds"]
            target = list(snapshot.position[:3])
            machine_target = list(snapshot.toolhead_position[:3])
            index = {"x": 0, "y": 1, "z": 2}[axis]
            target[index] += delta
            machine_target[index] += delta
            names = ("x", "y", "z")
            for idx, name in enumerate(names):
                low, high = [float(value) for value in bounds[name]]
                machine_min = float(snapshot.raw["toolhead"]["axis_minimum"][idx])
                machine_max = float(snapshot.raw["toolhead"]["axis_maximum"][idx])
                if not low <= target[idx] <= high:
                    raise ConflictError(f"{name.upper()}目标超出操作台安全范围")
                if not machine_min <= machine_target[idx] <= machine_max:
                    raise ConflictError(f"{name.upper()}目标超出安全范围")
            if axis in {"x", "y"} and snapshot.position[2] < float(
                bounds["minimum_xy_travel_z"]
            ):
                raise ConflictError("XY点动前Z必须至少为5 mm")
            feed = 600.0 if axis == "z" else 1200.0
            self.moon.send_gcode(
                f"G91\nG1 {axis.upper()}{delta:.4f} F{feed:.0f}\nG90\nM400"
            )
            checked = self.moon.wait_settled(
                target=target,
                coordinate_space="gcode",
                timeout_s=45,
            )
        return {"ok": True, "position": checked.position[:3]}

    def home(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        mode = str(body.get("mode", "")).lower()
        commands = {
            "x": ("G28 X", "x"),
            "xy": ("G28 X Y", "xy"),
            "z": ("G28 Z", "z"),
        }
        if mode not in {*commands, "full"}:
            raise ControlError("回零模式必须为x、xy、z或full")
        self._require_confirm(body)
        with self._operation():
            self._preflight_motion(owner)
            if mode == "full":
                result = self._full_home_workflow()
                self.moon.send_gcode(
                    'RESPOND PREFIX="HOME_RESULT" '
                    f'MSG="complete position X0 Y0 Z15 generation={result["generation"]}"'
                )
                return result
            self.moon.send_gcode(commands[mode][0], timeout_s=300)
            checked = self.moon.wait_settled(
                timeout_s=300, required_homed=commands[mode][1]
            )
        return {"ok": True, "homed_axes": checked.homed_axes}

    def home_u(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_reference(snapshot, "machine_home_valid")
            self.moon.send_gcode("_REFERENCE_U_BEGIN", timeout_s=30)
            report, laser = self._run_laser_alignment(
                body.get("scan_z_mm")
            )
            self._respond_laser_summary(laser)
            corrected = self.moon.snapshot()
            uv_state = self._macro(corrected.raw, "_UV_AXIS_STATE")
            macro_u = self._number(uv_state.get("u"), float("nan"))
            if (
                not math.isfinite(macro_u)
                or abs(macro_u) > 0.02
                or abs(corrected.u) > 0.02
            ):
                raise ConflictError(
                    "J100 reported success but U zero was not synchronized"
                )
            self.moon.send_gcode(
                "UV_REFERENCE_SET AXIS=U POSITION=0\n_REFERENCE_U_SUCCESS",
                timeout_s=60,
            )
            self._wait_for_reference("machine_home_valid", "u_tram_valid", timeout_s=30)
        return {
            "ok": True,
            "result_status": str(report.get("result_status", "")),
            "laser": laser,
        }

    def zero_uv(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            if not snapshot.uv_known:
                raise ConflictError("U/V位置不可用")
            if abs(snapshot.u) > 360 or abs(snapshot.v) > 360:
                raise ConflictError("U/V记录角度超出允许的归零范围")
            commands: list[str] = []
            for axis, value in (("U", snapshot.u), ("V", snapshot.v)):
                if abs(value) > 0.001:
                    direction = "-" if value > 0 else "+"
                    commands.append(
                        f"UV_JOG AXIS={axis} DIR={direction} DIST={abs(value):.6f}"
                    )
            if commands:
                self.moon.send_gcode("\n".join(commands + ["M400"]))
            checked = self.moon.wait_settled(timeout_s=120)
            self._require_uv_zero(checked)
        return {"ok": True, "u": checked.u, "v": checked.v}

    @staticmethod
    def _rtcp_state(snapshot: MachineSnapshot) -> dict[str, Any]:
        state = snapshot.raw.get("rtcp", {})
        return {
            "available": bool(state),
            "active": bool(state.get("active")),
            "reason": str(state.get("reason", "")),
            "pivot_mm": list(state.get("pivot_mm") or []),
            "offset_mm": list(state.get("offset_mm") or []),
            "last_segments": int(state.get("last_segments", 0)),
            "last_error_bound_mm": float(
                state.get("last_error_bound_mm", 0.0) or 0.0
            ),
        }

    def rtcp_enable(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            if not snapshot.uv_known:
                raise ConflictError("U/V参考无效，请先完成 HOME_U/HOME_V")
            state = snapshot.raw.get("rtcp", {})
            if not state:
                raise ConflictError("Klipper RTCP对象未加载")
            self.moon.send_gcode("M400\nRTCP_ENABLE", timeout_s=90)
            checked = self.moon.snapshot()
            rtcp = self._rtcp_state(checked)
            if not rtcp["active"]:
                raise ConflictError(
                    "RTCP未进入活动状态：" + (rtcp["reason"] or "unknown")
                )
        return {"ok": True, "rtcp": rtcp}

    def rtcp_disable(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        with self._operation():
            self._lease_require_and_idle(owner)
            self.moon.send_gcode("M400\nRTCP_DISABLE", timeout_s=90)
            checked = self.moon.snapshot()
            rtcp = self._rtcp_state(checked)
            if rtcp["active"]:
                raise ConflictError("RTCP关闭请求未生效")
        return {"ok": True, "rtcp": rtcp}

    def _lease_require_and_idle(self, owner: str) -> MachineSnapshot:
        self.lease.require(owner)
        snapshot = self.moon.snapshot()
        self._require_ready(snapshot)
        self._require_idle(snapshot)
        return snapshot

    def inspection(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_reference(
                snapshot,
                "machine_home_valid",
                "u_tram_valid",
                "gantry_tram_valid",
                "tap_z_valid",
            )
            self._require_uv_zero(snapshot)
            pose = self.fusion_motion.get(
                "inspection_pose", {"x": -90.0, "y": -30.0, "z": 110.0}
            )
            x, y, z = (float(pose["x"]), float(pose["y"]), float(pose["z"]))
            xy_min = self.fusion_motion.get("safe_xy_min", [-160, -130])
            xy_max = self.fusion_motion.get("safe_xy_max", [140, 180])
            if not float(xy_min[0]) <= x <= float(xy_max[0]):
                raise ConflictError("拍照位X超出Fusion安全范围")
            if not float(xy_min[1]) <= y <= float(xy_max[1]):
                raise ConflictError("拍照位Y超出Fusion安全范围")
            if not float(self.fusion_motion.get("safe_z_min", 80)) <= z <= float(
                self.fusion_motion.get("safe_z_max", 150)
            ):
                raise ConflictError("拍照位Z超出Fusion安全范围")
            script = (
                "G90\n"
                f"G1 Z{z:.3f} F600\n"
                f"G1 X{x:.3f} Y{y:.3f} F1200\n"
                "M400"
            )
            self.moon.send_gcode(script)
            checked = self.moon.wait_settled(
                target=[x, y, z],
                coordinate_space="gcode",
                timeout_s=120,
                tolerance=0.35,
            )
        return {"ok": True, "position": checked.position[:3]}

    def _preflight_pa(self, owner: str) -> MachineSnapshot:
        snapshot = self._preflight_motion(owner)
        self._require_reference(
            snapshot,
            "machine_home_valid",
            "u_tram_valid",
            "gantry_tram_valid",
            "tap_z_valid",
        )
        return snapshot

    def pa_dry_run(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        if body.get("v_ready") is not True or body.get("bed_clear") is not True:
            raise ControlError("必须确认V轴垂直且平台已清空")
        mode = str(body.get("mode", "COARSE")).upper()
        if mode not in {"COARSE", "FINE"}:
            raise ControlError("mode必须为COARSE或FINE")
        with self._operation():
            snapshot = self._preflight_pa(owner)
            self._require_homed(snapshot)
            self._require_uv_zero(snapshot)
            extruder = snapshot.raw.get("extruder", {})
            bed = snapshot.raw.get("heater_bed", {})
            if self._number(extruder.get("target")) > 0.1 or self._number(
                bed.get("target")
            ) > 0.1:
                raise ConflictError("空走要求热端和热床目标温度为0")
            command = f"PA_DRY_RUN MODE={mode} V_READY=1 BED_CLEAR=1"
            if mode == "FINE":
                command += f" COARSE_INDEX={int(body.get('coarse_index', -1))}"
            self.moon.send_gcode(command)
        return {"ok": True, "mode": mode}

    def pa_coarse(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        if body.get("v_ready") is not True or body.get("bed_clear") is not True:
            raise ControlError("必须确认V轴垂直且平台已清空")
        material = str(body.get("material", "")).upper()
        if material not in {"PLA", "PETG"}:
            raise ControlError("材料必须为PLA或PETG")
        temp = self._number(body.get("temperature"))
        bed_temp = self._number(body.get("bed_temperature"))
        flow = self._number(body.get("flow"), 1.0)
        with self._operation():
            self._preflight_pa(owner)
            self.moon.send_gcode(
                "PA_CALIBRATE_COARSE "
                f"MATERIAL={material} TEMP={temp:.1f} BED_TEMP={bed_temp:.1f} "
                f"FLOW={flow:.4f} V_READY=1",
                timeout_s=300,
            )
        return {"ok": True, "material": material}

    def pa_fine(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        if body.get("v_ready") is not True or body.get("bed_clear") is not True:
            raise ControlError("必须确认V轴垂直且平台已清空")
        index = int(body.get("coarse_index", -1))
        with self._operation():
            self._preflight_pa(owner)
            self.moon.send_gcode(
                f"PA_CALIBRATE_FINE COARSE_INDEX={index} V_READY=1",
                timeout_s=300,
            )
        return {"ok": True, "coarse_index": index}

    def pa_accept(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        index = int(body.get("fine_index", -1))
        self._require_confirm(body)
        with self._operation():
            self._preflight_motion(owner)
            self.moon.send_gcode(f"PA_ACCEPT FINE_INDEX={index}")
        return {"ok": True, "fine_index": index}

    def pa_use(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        material = str(body.get("material", "")).upper()
        temp = self._number(body.get("temperature"))
        if material not in {"PLA", "PETG"} or temp <= 0:
            raise ControlError("PA档案材料或温度无效")
        with self._operation():
            self._preflight_motion(owner)
            self.moon.send_gcode(f"PA_USE MATERIAL={material} TEMP={temp:.1f}")
        return {"ok": True, "material": material}

    def pa_invalidate(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        self._require_confirm(body)
        material = str(body.get("material", "")).upper()
        if material not in {"PLA", "PETG", "ALL"}:
            raise ControlError("失效材料必须为PLA、PETG或ALL")
        with self._operation():
            self._preflight_motion(owner)
            self.moon.send_gcode(f"PA_INVALIDATE MATERIAL={material}")
        return {"ok": True, "material": material}

    def pa_abort(self) -> dict[str, Any]:
        self.moon.send_gcode("PA_ABORT")
        return {"ok": True, "message": "PA中止请求已发送"}

    def pa_flat_v1_start(
        self, owner: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_confirm(body)
        mode = str(body.get("mode", "")).upper()
        if mode not in self.pa_flat_v1.MODES:
            raise ControlError("mode必须为DRY或PRINT")
        speed_percent = 100
        if mode == "DRY":
            speed_value = self._number(body.get("speed_percent", 50), float("nan"))
            speed_percent = int(speed_value)
            if (
                not math.isfinite(speed_value)
                or abs(speed_value - speed_percent) > 1e-9
                or speed_percent not in {50, 100}
            ):
                raise ControlError("空打速度只能为50或100")
        try:
            self.pa_flat_v1.verify_files()
        except PAFlatV1Error as exc:
            raise ControlError(str(exc)) from exc

        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_uv_zero(snapshot)
            if mode == "DRY":
                extruder = snapshot.raw.get("extruder", {})
                bed = snapshot.raw.get("heater_bed", {})
                if self._number(extruder.get("target")) > 0.1 or self._number(
                    bed.get("target")
                ) > 0.1:
                    raise ConflictError("空打要求热端和热床目标温度为0")
            try:
                self.moon.send_gcode(f"M220 S{speed_percent}")
                self.moon.start_print(self.pa_flat_v1.relative_filename(mode))
            except Exception:
                try:
                    self.moon.send_gcode("M220 S100")
                except Exception:
                    pass
                raise
        return {
            "ok": True,
            "mode": mode,
            "speed_percent": speed_percent,
            "filename": self.pa_flat_v1.relative_filename(mode),
        }

    def pa_flat_v1_cancel(self) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        filename = str(snapshot.raw.get("print_stats", {}).get("filename", ""))
        mode = self.pa_flat_v1.mode_for_filename(filename)
        if not mode or snapshot.print_state not in {"printing", "paused"}:
            raise ConflictError("当前没有由操作台启动的平面PA任务")
        self.moon.cancel_print()
        try:
            self.moon.wait_print_idle(timeout_s=20)
        finally:
            self.moon.send_gcode(
                "M220 S100\n"
                "M221 S100\n"
                "M104 S0\n"
                "M106 S0\n"
                "SET_PRESSURE_ADVANCE ADVANCE=0 SMOOTH_TIME=0.040"
            )
        return {"ok": True, "message": "平面PA任务已中止并完成清理"}

    def pa_flat_v1_apply(
        self, owner: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            index = int(body.get("index", -1))
            k = self.pa_flat_v1.k_for_index(index)
        except (TypeError, ValueError, PAFlatV1Error) as exc:
            raise ControlError(str(exc) or "INDEX无效") from exc
        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_uv_zero(snapshot)
            self.moon.send_gcode(
                f"SET_PRESSURE_ADVANCE ADVANCE={k:.3f} SMOOTH_TIME=0.040"
            )
        return {"ok": True, "index": index, "k": k}

    @staticmethod
    def _snapshot_position(snapshot: MachineSnapshot) -> dict[str, float]:
        return {
            "x": snapshot.position[0],
            "y": snapshot.position[1],
            "z": snapshot.position[2],
            "e": snapshot.position[3],
            "u": snapshot.u,
            "v": snapshot.v,
        }

    def path_dry_run_files(self) -> dict[str, Any]:
        try:
            files = self.path_dry_run.list_files()
        except PathDryRunError as exc:
            raise ControlError(str(exc)) from exc
        return {"ok": True, "files": files}

    def path_dry_run_preview(self, body: dict[str, Any]) -> dict[str, Any]:
        filename = str(body.get("filename", "")).strip()
        speed_value = self._number(body.get("speed_percent", 50), float("nan"))
        z_offset = self._number(body.get("z_offset"), float("nan"))
        if not filename:
            raise ControlError("请选择G-code文件")
        if not math.isfinite(speed_value) or not math.isfinite(z_offset):
            raise ControlError("空打速度或Z安全抬升无效")
        speed_percent = int(speed_value)
        if abs(speed_value - speed_percent) > 1e-9:
            raise ControlError("空打速度倍率必须为整数")
        snapshot = self.moon.snapshot()
        try:
            return self.path_dry_run.preview(
                filename,
                initial_position=self._snapshot_position(snapshot),
                speed_percent=speed_percent,
                z_offset=z_offset,
            )
        except PathDryRunError as exc:
            raise ControlError(str(exc)) from exc

    def path_dry_run_start(
        self, owner: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        self.lease.require(owner, touch=False)
        self._require_confirm(body)
        if (
            body.get("bed_clear") is not True
            or body.get("supervised") is not True
            or body.get("path_reviewed") is not True
        ):
            raise ControlError("必须确认平台清空、现场值守并已检查轨迹范围")
        token = str(body.get("token", ""))
        try:
            metadata = self.path_dry_run.load(token)
        except PathDryRunError as exc:
            raise ControlError(str(exc)) from exc
        violations = list(metadata["analysis"].get("violations") or [])
        if violations:
            raise ConflictError("；".join(str(item) for item in violations))

        with self._operation():
            snapshot = self._preflight_motion(owner)
            self._require_homed(snapshot)
            self._require_uv_zero(snapshot)
            extruder = snapshot.raw.get("extruder", {})
            bed = snapshot.raw.get("heater_bed", {})
            if self._number(extruder.get("target")) > 0.1 or self._number(
                bed.get("target")
            ) > 0.1:
                raise ConflictError("真实空打要求热端和热床目标温度为0")
            speed_factor = self._number(
                snapshot.raw.get("gcode_move", {}).get("speed_factor"), 1.0
            )
            if abs(speed_factor - 1.0) > 0.001:
                raise ConflictError("请先在Mainsail将速度倍率恢复到100%")

            current = self._snapshot_position(snapshot)
            preview_start = metadata["analysis"]["start_position"]
            mismatches: list[str] = []
            for axis in ("x", "y", "z"):
                if abs(current[axis] - float(preview_start[axis])) > 0.25:
                    mismatches.append(axis.upper())
            for axis in ("u", "v"):
                if abs(current[axis] - float(preview_start[axis])) > 0.1:
                    mismatches.append(axis.upper())
            if mismatches:
                raise ConflictError(
                    f"预览后{','.join(mismatches)}位置发生变化，请重新生成轨迹预览"
                )

            self.moon.start_print(str(metadata["generated_filename"]))
        return {
            "ok": True,
            "source": metadata["analysis"]["source"],
            "generated_filename": metadata["generated_filename"],
        }

    def path_dry_run_cancel(self) -> dict[str, Any]:
        snapshot = self.moon.snapshot()
        filename = str(snapshot.raw.get("print_stats", {}).get("filename", ""))
        metadata = self.path_dry_run.metadata_for_filename(filename)
        if not metadata or snapshot.print_state not in {"printing", "paused"}:
            raise ConflictError("当前没有由操作台启动的真实空打")
        self.moon.cancel_print()
        try:
            settled = self.moon.wait_print_idle(timeout_s=20)
            if settled.ready and settled.uv_known:
                self.moon.send_gcode(
                    "SET_GCODE_VARIABLE MACRO=_UV_AXIS_STATE "
                    f"VARIABLE=u VALUE={settled.u:.6f}\n"
                    "SET_GCODE_VARIABLE MACRO=_UV_AXIS_STATE "
                    f"VARIABLE=v VALUE={settled.v:.6f}"
                )
        except MoonrakerError:
            pass
        return {"ok": True, "message": "真实空打中止请求已发送"}


def load_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def new_client_id() -> str:
    return secrets.token_urlsafe(24)
