# tan RTCP Backup Extraction

## Goal
Recover the retained RTCP-related files for the former `tan` Raspberry Pi from local historical backups and sanitized 2026-08-20 audit evidence. Do not connect to, read, or modify any other Raspberry Pi.

## Current Phase
Recovery complete; exact missing items are documented.

## Phases

### Phase 1 - Verify target and access
**Status:** complete

- Confirmed the former address is not available for recovery.
- User confirmed the current `tan` contents are gone and only historical backups can be used.

### Phase 2 - Inventory RTCP artifacts
**Status:** complete

- Locate RTCP kinematics, toolhead patches, configs, macros, backups, firmware, tests and G-code.
- Record active versus archived Klipper trees and configs.
- Reconstruct the 2026-08-20 historical baseline from retained local records.
- Compare current remote files against the historical baseline using paths, timestamps, sizes, SHA-256 hashes and text diffs.

### Phase 3 - Export local package
**Status:** complete

- Copy only identified RTCP-related files to a new local package under `tmp`.
- Preserve remote-relative paths and timestamps when practical.
- Generate SHA-256 hashes and a manifest.

### Phase 4 - Verify and hand off
**Status:** complete

- Confirm no remote file or service was changed.
- Verify all copied files and summarize which are source, config, backup, test or reference-only.

## Next Step
Preserve the generated ZIP. If another disk, NAS or old computer later yields candidate files, compare their SHA-256 values against `MISSING_ITEMS.md` and the 2026-08-20 baseline before merging.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `192.168.5.124:7125` timed out and SSH closed the connection on 2026-09-01 | 1 | Do not retry blindly; use read-only identity discovery and retained local baseline records before reconnecting. |

## Scope Guard

- Allowed target: `tan@192.168.5.124` only.
- Forbidden target: `shu@192.168.5.119` and all other Raspberry Pis.
- Remote actions must be read-only.
