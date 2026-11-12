"""Run stdlib tests, Python-3.10 syntax checks, and save a NEW evidence report."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new report filename")
    sources = sorted(
        path for folder in ("rtcp_portable", "tests", "scripts", "bridges")
        for path in (ROOT / folder).rglob("*.py")
    )
    hashes = {}
    for path in sources:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "offline_only": True, "live_supported": False,
        "python": sys.version, "platform": platform.platform(),
        "python_310_syntax_checked_files": len(sources),
        "older_runtime_tested": False, "raspberry_pi_tested": False,
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
        "source_sha256": hashes, "test_log": stream.getvalue(),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(stream.getvalue(), end="")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
