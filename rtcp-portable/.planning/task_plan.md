# Portable RTCP — isolated offline implementation

## Goal
Build and test a portable, standard-library offline RTCP development package.
No printer connection, remote file edits, live Klipper installation, motion or heating.
Preserve unrelated workspace files and the other process's printer.cfg debugging.

## Phases
### Phase 1 — Contracts and isolated package
**Status:** complete
Define common-pivot Rx/Rz coordinates, strict configuration and work registration.
### Phase 2 — Geometry, bounded paths and reference/session model
**Status:** complete
Implement pure core, adaptive geometric subdivision, rotary references and no-jump
offline lifecycle. Keep live execution explicitly unsupported.
### Phase 3 — Diagnostics, CLI and regression tests
**Status:** complete
Run independent analytic/randomized tests, legacy-defect regressions and read-only
audit of already-downloaded source/config snapshots; no new Pi access.
### Phase 4 — Portable distribution and handoff
**Status:** complete
Build a pure-Python wheel, install/test in a clean local environment, save evidence
and list unresolved live adapter/planner/calibration work.

## Next Step
v0.2 offline handoff complete. Next data-validation milestone is an actual Rhino
pre-IK capture to confirm branch/segment/E alignment and normal direction; this
does not require connecting the printer. Live deployment remains separately gated.

### Phase 5 — Open5x source and sample audit
**Status:** complete
Trace GHX graph/export coordinates, angles, E/F and macros; fingerprint originals.
### Phase 6 — Offline import and export-contract development
**Status:** complete
Add strict modal G-code analysis and supported normalization; quarantine unknown
macros and ambiguous coordinate semantics rather than produce runnable output.
### Phase 7 — Adapter regression and portable handoff
**Status:** complete
Exercise supplied sample and synthetic edge cases, preserve v0.1 artifacts and
document remaining inputs/real-host gates.

## Confirmed inputs
- U 260:18; XY convention follows active printer.cfg, never overwritten here.
- Common pivot nominally on bed; Rhino origin is bed/pivot. Machine pivot XYZ remains
  separate and is not assumed to be machine (0,0,0).
- U=0 horizontal; V manually referenced per job; both angle signs configurable.
- Vision dx/dy are actual positive workpiece displacement relative to measured rotary
  center, not correction commands. No second disk eccentricity correction.

## Errors and limits
- GH_IO lookup at C:/Program Files/Rhino 8 failed (directory absent). Switched to
  bounded stdlib XML/base64/raw-DEFLATE inspection; no embedded code execution.
- Workspace root has unrelated untracked files and historical planning; untouched.
- No additional AGENTS.md found in checked current-workspace ancestors.
- Python 3.12 available; pytest/build absent. Use unittest and existing setuptools.
- Real pivot XYZ/signs/limits not calibrated: actual-machine template must be incomplete
  and cannot be accepted as a runnable simulation profile without explicit values.
- Official documentation fetch returned no usable output; local versioned sources are
  used for compatibility findings instead. No failed tests in initial 64-test run.
- First clean install passed, but Windows child output decoded the Chinese install
  path incorrectly. Set PYTHONIOENCODING=utf-8 and rerun existing-wheel verification;
  preserve the original report and publish a corrected final report.
- Second install passed; -I ignores PYTHONIOENCODING, so the path display was still
  garbled. Changed this subprocess result to ASCII-escaped JSON and parse it in the
  parent, which is independent of the child's stdout encoding.
