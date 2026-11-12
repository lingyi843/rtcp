# Progress

## 2026-11-10
- Read planning skill and previous design/audit evidence; checked local workspace.
- Created separate project plan; unrelated root planning/worktree left unchanged.
- Python 3.12 and setuptools available; runtime/test dependencies will be standard-library.
- No printer access this turn.
- Implemented immutable schema, Rx(U)Rz(V) forward/inverse, analytical geometric
  subdivision, fail-closed offline session, CLI and static snapshot lint.
- Created synthetic complete profile and intentionally incomplete machine template.
- Profiles and core do not contain IP addresses, credentials or user-specific paths.
- Initial unittest run: 64/64 pass in 3.648 s. No prior implementation failures.
- Saved reports/snapshot-audit.json and reports/arc-simulation.json.
- Added explicit motor-disable invalidation regression (suite now 65 tests).
- Added README, integration/migration contracts, frozen offline manifest, repeatable
  test-evidence and wheel/isolated-install verification scripts.
- 65/65 source tests passed; pure-Python wheel built with --no-index and no build isolation.
  Fresh venv imported only installed package and passed full 65-test suite, CLI, selfcheck
  and simulation. Initial report had garbled Chinese path text due child stdout encoding;
  assertion confirmed actual installed path, and output handling has been corrected.
- Added existing-wheel recheck with source-content matching and portable ZIP bundling.
- Final source run: 65/65 pass in 4.240 s; clean installed run: 65/65 pass in 3.232 s.
  All six installation-check subprocesses exit 0. Verified Unicode installation path.
- Added Chinese handoff report; runtime package and profiles contain no network
  transports, IPs, credentials or fixed installation paths.
- Created dist/rtcp-portable-offline-0.1.0.zip (33 entries, 73,747 bytes);
  CRC and every bundled file hash checked. ZIP SHA256:
  5dd2cd2b9546ac970c7dffd6e9b0f83f34dd934dab24df2568d7a19d1f45aaee.
- All offline development phases complete. No live deployment or printer changes.

## Follow-up — supplied GHX and G-code
- Resumed file-based planning, added phases 5–7. Inspected headers/tails and script
  markers. Continuing offline only; originals and prior distribution remain intact.
- Statically decoded GHX clusters with GH_IO serialization, without solving Rhino
  documents or executing user scripts. Saved wiring reports for IK and feed clusters.
- Added strict modal G-code audit, normal-to-UV solver, pre-IK capture helper/validator,
  explicit schema-v2 job and rest-to-rest XYZUV/E/CoreXY timing feasibility.
- Actual sample audit: 8,570 lines, 8,548 motion commands, 8,540 explicit XYZUV rows;
  every such row has X=Y=0, V reaches -463.8 degrees. M98 macro unknown -> no safe
  automatic interpretation/import. Original inputs unchanged.
- v0.2 final source suite: 115/115 pass in 3.762 s; 27 Python files pass 3.10 grammar.
  New wheel installed in fresh venv, source-free staging suite 115/115 in 3.166 s;
  all eight build/install/CLI validation commands exit 0.
- Original GHX/G-code SHA256 rechecked unchanged; v0.1 wheel/ZIP unchanged.
- Added Chinese adaptation instructions and handoff report, explicitly separating
  static audit, authored bridge tests, actual Rhino capture and unimplemented live planning.
- Published v0.2 ZIP: 55 entries, 204,317 bytes; CRC and all content hashes verified.
  SHA256 ae58bb1067d46e608f77dfdacaee4e5abf42346c383c367e46c333bf55c5f804.
- Follow-up phases complete. No printer connection/deployment or original-file edits.
