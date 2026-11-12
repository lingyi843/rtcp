# shu CoreXY Config Retention Audit

## Goal

Perform a read-only inventory of the `shu` controller's Klipper configuration tree and related runtime references. Classify files as active, referenced dependency, backup/history, temporary/staged, or deletion candidate. Do not delete, move, rename, restart services, or issue machine commands.

## Current Phase

Phase 4 - Approved conservative cleanup.

## Phases

### Phase 1 - Read-only live inventory

**Status:** complete

- Verify the `shu` host identity and active Klipper/Moonraker configuration paths without machine control.
- Capture an inventory of config directories, files, modification times, sizes, active includes, and service references.

### Phase 2 - Reference and retention analysis

**Status:** complete

- Trace active include/import/macro references and distinguish them from similarly named stale copies.
- Classify potential deletion candidates conservatively; do not infer that a backup is disposable merely because it is old.

### Phase 3 - Review report

**Status:** complete

- Deliver a deletion-review table with evidence, risks, estimated reclaimable space, and explicit keep/archive/delete recommendations.
- Await explicit approval before any deletion or relocation.

### Phase 4 - Approved conservative cleanup

**Status:** complete

- Preserve every active or referenced configuration file and every file dated 2026-08-20 or later.
- Package the exact early, non-referenced cleanup set with a manifest and hashes outside the active config tree.
- Remove only the packaged originals, then re-read the active include graph and config directory layout.

## Safety Constraints

- Read-only only: no remote writes, deletions, moves, renames, restarts, heating, homing, motor enable, or G-code execution.
- Do not inspect or persist credentials beyond the user-provided connection scope.
- Active configuration and any file referenced by an active include, service, macro, or deployment path are never candidates for deletion in this audit.
- Unapproved artifacts remain under `tmp`; no candidate list constitutes deletion authorization.

## Next Step

Keep current LYX/M7 troubleshooting backups and all files dated 2026-08-20 or later. If further cleanup is requested, review the retained recent snapshots only after the current extruder fault is resolved and a known-good configuration is frozen.
