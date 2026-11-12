"""Build offline wheel; test isolated installation without access to source imports."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, help="retest an existing wheel without rebuilding it")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new report filename")
    artifacts = ROOT / ".artifacts"
    artifacts.mkdir(exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="installed-check-", dir=artifacts))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PIP_NO_INDEX"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    records = []

    def command(arguments: list[str], cwd: Path) -> str:
        completed = subprocess.run(
            arguments, cwd=cwd, env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        records.append({
            "command": arguments, "cwd": str(cwd), "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr,
        })
        if completed.returncode:
            raise RuntimeError(f"command failed: {arguments}\n{completed.stderr}")
        return completed.stdout

    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "offline_only": True, "live_supported": False,
        "raspberry_pi_tested": False, "success": False,
        "build_performed": args.wheel is None,
        "commands": records,
    }
    try:
        if args.wheel:
            wheel = args.wheel.resolve(strict=True)
        else:
            wheel_dir = sandbox / "wheel"
            wheel_dir.mkdir()
            command([
                sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                "--no-index", "--wheel-dir", str(wheel_dir), str(ROOT),
            ], sandbox)
            wheels = list(wheel_dir.glob("*.whl"))
            if len(wheels) != 1:
                raise RuntimeError("expected exactly one wheel")
            wheel = wheels[0]
        if not wheel.name.endswith("-py3-none-any.whl"):
            raise RuntimeError("wheel unexpectedly platform-specific")
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            if any(name.endswith((".cfg", ".gcode")) for name in names):
                raise RuntimeError("distribution unexpectedly contains live-machine files")
            for source in sorted((ROOT / "rtcp_portable").glob("*.py")):
                name = source.relative_to(ROOT).as_posix()
                if archive.read(name) != source.read_bytes():
                    raise RuntimeError(f"wheel does not match current source: {name}")
            result["wheel_files"] = names
        venv_root = sandbox / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_root)
        python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], sandbox)
        package_check = command([
            str(python), "-I", "-c",
            "import rtcp_portable,sys,pathlib,json; "
            "p=pathlib.Path(rtcp_portable.__file__).resolve(); "
            "assert p.is_relative_to(pathlib.Path(sys.prefix).resolve()); "
            "assert rtcp_portable.LIVE_EXECUTION_SUPPORTED is False; "
            "print(json.dumps(str(p), ensure_ascii=True))",
        ], sandbox)
        result["installed_import"] = json.loads(package_check)
        command([str(python), "-I", "-m", "rtcp_portable", "selfcheck"], sandbox)
        staging = sandbox / "test-copy"
        staging.mkdir()
        for folder in ("tests", "klipper", "profiles", "examples", "bridges"):
            shutil.copytree(ROOT / folder, staging / folder, ignore=shutil.ignore_patterns("__pycache__"))
        command([str(python), "-m", "unittest", "discover", "-s", "tests", "-v"], staging)
        command([
            str(python), "-I", "-m", "rtcp_portable", "simulate",
            str(staging / "profiles/simulation.json"), str(staging / "examples/arc.json"),
            "--output", str(sandbox / "installed-simulation.json"),
        ], sandbox)
        command([
            str(python), "-I", "-m", "rtcp_portable", "plan-timing",
            str(staging / "profiles/simulation.json"),
            str(staging / "profiles/timing.simulation.json"),
            str(staging / "examples/timed-job.json"), "--offset", "5", "-3", "0",
            "--output", str(sandbox / "installed-timing.json"),
        ], sandbox)
        cli = venv_root / ("Scripts/rtcp-offline.exe" if os.name == "nt" else "bin/rtcp-offline")
        command([str(cli), "selfcheck"], sandbox)
        dist = ROOT / "dist"
        dist.mkdir(exist_ok=True)
        target = dist / wheel.name
        if target.exists() and target.resolve() != wheel.resolve():
            raise RuntimeError("distribution target already exists; choose a new version or inspect explicitly")
        if target.resolve() != wheel.resolve():
            shutil.copy2(wheel, target)
        result["wheel"] = target.name
        result["wheel_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        result["success"] = True
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("commands", "wheel_files")},
                     ensure_ascii=True, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
