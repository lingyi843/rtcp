from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class MoonrakerError(RuntimeError):
    pass


@dataclass(frozen=True)
class MachineSnapshot:
    raw: dict[str, Any]
    state: str
    state_message: str
    print_state: str
    homed_axes: str
    position: list[float]
    toolhead_position: list[float]
    live_position: list[float]
    homing_origin: list[float]
    coordinate_offset: list[float]
    live_velocity: float
    uv_known: bool
    u: float
    v: float

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    @property
    def idle(self) -> bool:
        return self.print_state in {"standby", "complete", "cancelled", "error"}


class MoonrakerClient:
    STATUS_OBJECTS = (
        "webhooks",
        "toolhead",
        "print_stats",
        "virtual_sdcard",
        "pause_resume",
        "gcode_move",
        "motion_report",
        "extruder",
        "heater_bed",
        "fan",
        "filament_motion_sensor encoder_sensor",
        "display_status",
        "save_variables",
        "gcode_macro _UV_AXIS_STATE",
        "gcode_macro _MACHINE_REFERENCE_STATE",
        "gcode_macro _PA_CONFIG",
        "gcode_macro _PA_RUNTIME",
        "gcode_macro _PA_DRY_RUNTIME",
        "probe",
        "quad_gantry_level",
        "bed_mesh",
        "rtcp",
    )

    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self._objects_cache: tuple[float, set[str]] = (0.0, set())

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request, timeout=float(timeout_s or self.timeout_s)
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                payload_detail = json.loads(detail)
                message = (
                    payload_detail.get("error", {}).get("message")
                    or payload_detail.get("error")
                    or detail
                )
            except Exception:
                message = detail
            raise MoonrakerError(f"Moonraker HTTP {exc.code}: {message}") from exc
        except Exception as exc:
            raise MoonrakerError(f"Moonraker request failed for {path}: {exc}") from exc

    def available_objects(self) -> set[str]:
        cached_at, cached = self._objects_cache
        if cached and time.monotonic() - cached_at < 30.0:
            return cached
        result = self._request("/printer/objects/list")
        objects = set(result.get("result", {}).get("objects", []))
        self._objects_cache = (time.monotonic(), objects)
        return objects

    def query_status(self) -> dict[str, Any]:
        available = self.available_objects()
        selected = [item for item in self.STATUS_OBJECTS if item in available]
        query = "&".join(urllib.parse.quote(item, safe="") for item in selected)
        result = self._request(f"/printer/objects/query?{query}")
        return result.get("result", {}).get("status", {})

    def query_objects(self, *objects: str) -> dict[str, Any]:
        available = self.available_objects()
        missing = [item for item in objects if item not in available]
        if missing:
            raise MoonrakerError(
                "Klipper object unavailable: " + ", ".join(missing)
            )
        query = "&".join(
            urllib.parse.quote(item, safe="") for item in objects
        )
        result = self._request(f"/printer/objects/query?{query}")
        return result.get("result", {}).get("status", {})

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def snapshot(self) -> MachineSnapshot:
        raw = self.query_status()
        webhooks = raw.get("webhooks", {})
        toolhead = raw.get("toolhead", {})
        print_stats = raw.get("print_stats", {})
        motion = raw.get("motion_report", {})
        gcode_move = raw.get("gcode_move", {})
        axis_map = {
            str(key).upper(): int(value)
            for key, value in (gcode_move.get("axis_map") or {}).items()
            if isinstance(value, int)
        }

        def mapped_position(values: Any) -> list[float]:
            raw_values = [self._float(value) for value in (values or [])]

            def axis_value(axis: str, fallback_index: int) -> float:
                index = axis_map.get(axis, fallback_index)
                return raw_values[index] if 0 <= index < len(raw_values) else 0.0

            return [
                axis_value("X", 0),
                axis_value("Y", 1),
                axis_value("Z", 2),
                axis_value("E", 3),
                axis_value("U", 4),
                axis_value("V", 5),
            ]

        gcode_position = mapped_position(
            gcode_move.get("gcode_position")
            or motion.get("live_position")
            or toolhead.get("position")
        )
        toolhead_position = mapped_position(
            gcode_move.get("position") or toolhead.get("position")
        )
        live_position = mapped_position(
            motion.get("live_position") or toolhead.get("position")
        )
        homing_origin = mapped_position(gcode_move.get("homing_origin"))
        coordinate_offset = [
            toolhead_position[index] - gcode_position[index]
            for index in range(len(gcode_position))
        ]

        uv = raw.get("gcode_macro _UV_AXIS_STATE", {})
        uv_axes_registered = "U" in axis_map and "V" in axis_map
        uv_known = int(uv.get("u_known", 0)) == 1 and int(uv.get("v_known", 0)) == 1
        # mapped_position() has already canonicalized the vector to X/Y/Z/E/U/V.
        # Applying the raw Klipper axis_map again here swaps U and V when their
        # registration order is V then U (the order used by the live machine).
        u = gcode_position[4] if uv_axes_registered else self._float(uv.get("u"))
        v = gcode_position[5] if uv_axes_registered else self._float(uv.get("v"))
        return MachineSnapshot(
            raw=raw,
            state=str(webhooks.get("state", "offline")).lower(),
            state_message=str(webhooks.get("state_message", "Moonraker unavailable")),
            print_state=str(print_stats.get("state", "unknown")).lower(),
            homed_axes=str(toolhead.get("homed_axes", "")).lower(),
            position=gcode_position,
            toolhead_position=toolhead_position,
            live_position=live_position,
            homing_origin=homing_origin,
            coordinate_offset=coordinate_offset,
            live_velocity=abs(self._float(motion.get("live_velocity"))),
            uv_known=uv_known,
            u=u,
            v=v,
        )

    def send_gcode(self, script: str, timeout_s: float = 180.0) -> dict[str, Any]:
        return self._request(
            "/printer/gcode/script",
            method="POST",
            payload={"script": script},
            timeout_s=timeout_s,
        )

    def emergency_stop(self) -> dict[str, Any]:
        return self._request(
            "/printer/emergency_stop",
            method="POST",
            payload={},
            timeout_s=10.0,
        )

    def start_print(self, filename: str) -> dict[str, Any]:
        return self._request(
            "/printer/print/start",
            method="POST",
            payload={"filename": filename},
            timeout_s=15.0,
        )

    def cancel_print(self) -> dict[str, Any]:
        return self._request(
            "/printer/print/cancel",
            method="POST",
            payload={},
            timeout_s=15.0,
        )

    def wait_print_idle(self, timeout_s: float = 20.0) -> MachineSnapshot:
        deadline = time.monotonic() + timeout_s
        last: MachineSnapshot | None = None
        while time.monotonic() < deadline:
            last = self.snapshot()
            if last.idle and last.live_velocity <= 0.05:
                return last
            time.sleep(0.2)
        raise MoonrakerError(f"Print did not stop before timeout; last={last}")

    def wait_ready(self, timeout_s: float = 35.0) -> MachineSnapshot:
        deadline = time.monotonic() + timeout_s
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                snapshot = self.snapshot()
                if snapshot.ready:
                    return snapshot
            except Exception as exc:
                last_error = exc
            time.sleep(0.5)
        raise MoonrakerError(
            f"Klipper did not become ready within {timeout_s:.0f}s"
            + (f": {last_error}" if last_error else "")
        )

    def wait_settled(
        self,
        *,
        timeout_s: float = 90.0,
        required_homed: Iterable[str] = (),
        target: list[float] | None = None,
        tolerance: float = 0.25,
        coordinate_space: str = "gcode",
    ) -> MachineSnapshot:
        if coordinate_space not in {"gcode", "toolhead", "live"}:
            raise ValueError(f"Unknown coordinate space: {coordinate_space}")
        deadline = time.monotonic() + timeout_s
        stable_started: float | None = None
        last: MachineSnapshot | None = None
        while time.monotonic() < deadline:
            last = self.snapshot()
            axes_ok = all(axis in last.homed_axes for axis in required_homed)
            target_ok = True
            if target is not None:
                positions = {
                    "gcode": last.position,
                    "toolhead": last.toolhead_position,
                    "live": last.live_position,
                }[coordinate_space]
                target_ok = all(
                    abs(positions[index] - target[index]) <= tolerance
                    for index in range(min(3, len(target)))
                )
            if axes_ok and target_ok and last.live_velocity <= 0.05:
                if stable_started is None:
                    stable_started = time.monotonic()
                if time.monotonic() - stable_started >= 0.3:
                    return last
            else:
                stable_started = None
            time.sleep(0.1)
        raise MoonrakerError(
            f"Machine did not settle before timeout; last={last}"
        )
