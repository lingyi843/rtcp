# Findings

- Audit initiated on 2026-08-28 for the `shu` CoreXY machine. Scope is read-only classification of accumulated configuration/intermediate files.
- Historical records identify `/home/shu/printer_data/config/printer.cfg` as the prior active Klipper entry point, but this must be confirmed live before classifying any files.
- Historical records include approved backups, staged `tmp/codex_review` artifacts, old M6 LYX commissioning files, and active CoreXY workflow/config includes. Filename age alone is insufficient evidence for deletion.
- Live read-only verification on 2026-08-28: SSH identity is `shu@shu`; the active Klipper process explicitly loads `/home/shu/printer_data/config/printer.cfg` and is running.
- Active Klipper include graph is `printer.cfg` -> `mainsail.cfg`, `mesh_function.cfg`, `machine_state.cfg`, `homing.cfg`, `leveling.cfg`, `workflow.cfg`, `pa_calibration.cfg`, `laser_offset_macros.cfg`, and `laser_u_motion_macros.cfg`.
- The running Crowsnest process explicitly uses `/home/shu/printer_data/config/crowsnest.conf`. `moonraker.conf` and `KlipperScreen.conf` exist as standard runtime configuration files; their active status requires final process/source-path confirmation before classification.
- The config tree contains 86 files totaling about 859 KiB: root-level files 588,406 bytes, `archive/` 196,928 bytes, `backups/` 73,066 bytes, `tests/` 1,592 bytes, and `.theme/` 216 bytes.
- Exact duplicate groups were found among historical snapshots, including two `printer.cfg.bak-before-g28-m400-*` files, two high-active/M7-enable backups, two laser-U historical snapshots, and `archive/20260824-1518-before-simple-g28/workflow.cfg` identical to active `workflow.cfg`.
- No deletion has been performed. Root-level non-included configuration files must still be checked against running auxiliary services before becoming candidates.
- Active `pa_calibration.cfg` declares `[save_variables] filename: ~/printer_data/config/pa_variables.cfg`; the zero-byte `pa_variables.cfg` is active state storage and must not be deleted.
- `moonraker.log` confirms both the active `moonraker.conf` path and `.moonraker.conf.bkp` as Moonraker's backup configuration path. Both must be kept.
- `timelapse.cfg` is a symlink to `/home/shu/moonraker-timelapse/klipper_macro/timelapse.cfg`; it is not currently included by active `printer.cfg`, but it is an installed plugin entry point and remains a review-only candidate rather than a deletion recommendation.
- No non-active root config filename appeared in scanned active Klipper config contents or active auxiliary-service source trees, except `pa_variables.cfg` (active) and `.moonraker.conf.bkp` references inside Moonraker test sources. This is evidence of non-use, not proof that files have no historical recovery value.
- The entire tree is only about 859 KiB, so cleanup is organizational rather than a meaningful storage recovery action.
- Approved cleanup completed at 2026-08-28 10:02:44 local controller time. Twenty-eight early, non-referenced root files totaling 291,461 bytes were packaged and removed from the active config root.
- Backup location: `/home/shu/printer_data/config-retention-backups/20260828-100244-old-unused-config-cleanup/old-unused-config-files.tar.gz`; SHA-256 `76faf39e3d08af2ad702c9740c03fdbbc8ef0d57fe11b57ac9f5a1171a5bc88e`. The backup directory also contains a JSON manifest and SHA256SUMS file.
- Pre-delete checks verified each removed file's SHA-256, confirmed the active includes, and excluded all active/runtime, recent (2026-08-20 onward), and LYX/M7 diagnostic snapshots. Post-delete checks confirmed the active Klipper process still uses `printer.cfg`, all nine active includes remain, sampled removed files are absent, and the backup tar exists.
