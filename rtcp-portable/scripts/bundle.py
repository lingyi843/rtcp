"""Create a NEW portable source+wheel ZIP from an explicit file allowlist."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rtcp_portable import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tests-report", type=Path, required=True)
    parser.add_argument("--install-report", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite an existing bundle")
    files = [
        ROOT / name for name in ("README.md", "pyproject.toml", "deployment-manifest.json")
    ]
    for folder in ("rtcp_portable", "klipper", "control-console-overlay",
                   "tests", "scripts", "bridges", "profiles", "examples",
                   "docs", "reports"):
        files.extend(
            path for path in (ROOT / folder).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
            and path.suffix in (".py", ".ps1", ".json", ".md")
            and not path.name.startswith(("portability-check", "test-results"))
        )
    wheels = list((ROOT / "dist").glob(f"portable_rtcp_offline-{__version__}-*.whl"))
    if len(wheels) != 1:
        parser.error("exactly one verified wheel must exist in dist/")
    files.extend(wheels)
    evidence = json.loads(args.install_report.read_text(encoding="utf-8"))
    if not evidence["success"]:
        parser.error("final installation verification has not passed")
    tests = json.loads(args.tests_report.read_text(encoding="utf-8"))
    if not tests["success"]:
        parser.error("final tests have not passed")
    for relative, digest in tests["source_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            parser.error(f"source changed since tests: {relative}")
    if hashlib.sha256(wheels[0].read_bytes()).hexdigest() != evidence["wheel_sha256"]:
        parser.error("wheel changed since install verification")
    hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(set(files))}
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "version": __version__, "live_supported": False, "files_sha256": hashes,
    }
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in hashes:
            archive.write(ROOT / relative, "rtcp-portable/" + relative)
        archive.writestr("rtcp-portable/bundle-manifest.json",
                         json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("bundle CRC check failed")
        for relative, expected in hashes.items():
            if hashlib.sha256(archive.read("rtcp-portable/" + relative)).hexdigest() != expected:
                raise RuntimeError(f"bundle hash check failed: {relative}")
    print(json.dumps({
        "bundle": args.output.name, "file_count": len(hashes) + 1,
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "live_supported": False, "crc_and_content_hashes_verified": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
