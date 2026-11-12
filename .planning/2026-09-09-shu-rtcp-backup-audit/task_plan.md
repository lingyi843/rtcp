# shu RTCP Backup Audit

## Goal
Read-only inspect RTCP-related backup material on the `shu` Raspberry Pi at `192.168.5.119`, compare it with the recovered historical `tan` RTCP baseline, and report what matches, differs, or is still missing.

## Current Phase
Complete.

## Phases

### Phase 1 - Identity and safety gate
**Status:** complete

- Confirm Moonraker/SSH hostname is `shu` at `192.168.5.119`.
- Query only identity, service paths, metadata and file contents needed for the audit.
- Do not move axes, heat, restart services, edit files, or upload anything.

### Phase 2 - Locate RTCP backups
**Status:** complete

- Search user-owned backup/archive/config/source locations for RTCP, cradle, XYZAC, toolhead and related files.
- Record path, size, modification time, SHA-256 and archive members.

### Phase 3 - Compare with tan history
**Status:** complete

- Compare against the 2026-08-20 tan baseline hashes and the desktop recovery folder.
- Inspect text differences for the core RTCP files and configuration/macros.

### Phase 4 - Report and optional local export
**Status:** complete

- Produce a local comparison report.
- State exactly what additional material, if any, is needed from the user.

## Next Step
Await user confirmation of the physical A/C axis convention and whether the next implementation should continue with shu MCU-side V2 or rebuild the tan host-side prototype.

## Scope Guard

- Allowed remote target: `shu@192.168.5.119` only.
- Remote access is read-only.
- No G-code, Moonraker mutation endpoint, service restart, config change, upload, motion or heat.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| WSL no-real runner could not start: WSL executable exists but no Linux distribution is installed; initial PowerShell path conversion also used an invalid regex escape. | 1 | Do not install or alter WSL for this audit. Run Python host tests natively and search for an existing local C compiler/Git Bash; if none exists, record the C test suite as not executable in the present environment. |
| First native Python-test wrapper had a PowerShell parser error because a `finally` block was piped directly. | 1 | Wrap the whole test body in a script block before piping to `Tee-Object`. |
| First local GH/G-code search wrapper piped directly after nested `foreach` blocks and triggered the same PowerShell empty-pipe parser rule. | 1 | Collect the loop output into a variable/script block, then sort/format it. |
