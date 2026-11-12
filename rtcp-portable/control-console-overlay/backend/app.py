from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Any, Callable

from flask import Flask, jsonify, request, send_from_directory, session

from .control_service import (
    ControlError,
    ControlService,
    load_config,
    new_client_id,
)


BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR.parent / "dist"


def create_app(
    service: ControlService | None = None,
    *,
    testing: bool = False,
) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=False,
        TESTING=testing,
    )
    control = service or ControlService(load_config(BASE_DIR / "config.json"))

    def owner() -> str:
        if "client_id" not in session:
            session["client_id"] = new_client_id()
        return str(session["client_id"])

    def body() -> dict[str, Any]:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    def api(callback: Callable[[], Any]):
        try:
            return jsonify(callback())
        except ControlError as exc:
            return jsonify({"ok": False, "error": str(exc)}), exc.status_code
        except Exception as exc:
            app.logger.exception("Control API request failed")
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                ),
                500,
            )

    @app.get("/api/status")
    def status():
        return api(lambda: control.status(owner()))

    @app.post("/api/session/authorize")
    def authorize():
        return api(lambda: control.authorize(owner(), body()))

    @app.post("/api/session/lock")
    def lock_session():
        return api(lambda: control.lock_session(owner()))

    @app.post("/api/emergency-stop")
    def emergency_stop():
        return api(control.emergency_stop)

    @app.post("/api/recovery/firmware-restart")
    def firmware_restart():
        return api(lambda: control.firmware_restart(owner(), body()))

    @app.post("/api/motion/jog")
    def jog():
        return api(lambda: control.jog(owner(), body()))

    @app.post("/api/motion/home")
    def home():
        return api(lambda: control.home(owner(), body()))

    @app.post("/api/motion/zero-uv")
    def zero_uv():
        return api(lambda: control.zero_uv(owner(), body()))

    @app.post("/api/rtcp/enable")
    def rtcp_enable():
        return api(lambda: control.rtcp_enable(owner(), body()))

    @app.post("/api/rtcp/disable")
    def rtcp_disable():
        return api(lambda: control.rtcp_disable(owner(), body()))

    @app.post("/api/motion/inspection")
    def inspection():
        return api(lambda: control.inspection(owner(), body()))

    @app.post("/api/pa/dry-run")
    def pa_dry_run():
        return api(lambda: control.pa_dry_run(owner(), body()))

    @app.post("/api/pa/coarse")
    def pa_coarse():
        return api(lambda: control.pa_coarse(owner(), body()))

    @app.post("/api/pa/fine")
    def pa_fine():
        return api(lambda: control.pa_fine(owner(), body()))

    @app.post("/api/pa/accept")
    def pa_accept():
        return api(lambda: control.pa_accept(owner(), body()))

    @app.post("/api/pa/use")
    def pa_use():
        return api(lambda: control.pa_use(owner(), body()))

    @app.post("/api/pa/invalidate")
    def pa_invalidate():
        return api(lambda: control.pa_invalidate(owner(), body()))

    @app.post("/api/pa/abort")
    def pa_abort():
        return api(control.pa_abort)

    @app.post("/api/pa-flat-v1/start")
    def pa_flat_v1_start():
        return api(lambda: control.pa_flat_v1_start(owner(), body()))

    @app.post("/api/pa-flat-v1/cancel")
    def pa_flat_v1_cancel():
        return api(control.pa_flat_v1_cancel)

    @app.post("/api/pa-flat-v1/apply")
    def pa_flat_v1_apply():
        return api(lambda: control.pa_flat_v1_apply(owner(), body()))

    @app.get("/api/path-dry-run/files")
    def path_dry_run_files():
        return api(control.path_dry_run_files)

    @app.post("/api/path-dry-run/preview")
    def path_dry_run_preview():
        return api(lambda: control.path_dry_run_preview(body()))

    @app.post("/api/path-dry-run/start")
    def path_dry_run_start():
        return api(lambda: control.path_dry_run_start(owner(), body()))

    @app.post("/api/path-dry-run/cancel")
    def path_dry_run_cancel():
        return api(control.path_dry_run_cancel)

    @app.get("/")
    def root():
        return send_from_directory(DIST_DIR, "index.html")

    @app.get("/<path:path>")
    def static_files(path: str):
        candidate = DIST_DIR / path
        if candidate.is_file():
            return send_from_directory(DIST_DIR, path)
        return send_from_directory(DIST_DIR, "index.html")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return app
