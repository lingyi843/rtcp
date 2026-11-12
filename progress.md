# Progress

## 2026-08-25

- Started a credential-redacted new-conversation handoff package using only local workspace records. The user explicitly prohibited machine connection, motion, heating, service restart and formal-system changes during this documentation task.
- Re-read `task_plan.md`, `findings.md` and `progress.md`; the final handoff will distinguish user-supplied data, verified facts, deployed changes, staged-only changes and pending hypotheses.
- Identified two critical handoff separation rules: keep the `tan` RTCP inventory distinct from the `shu` CoreXY machine, and describe the M6-to-M7 extruder remap explicitly so the August 14 commissioning pinout is not mistaken for the current motor allocation.
- Inspected the retained local staged artifacts. Flagged `tmp/klipper_debug/printer.cfg.final` as obsolete/reference-only because its motor and Tap pin allocation predates the August 24 live remap; confirmed the span-60, U/V mapping and Tap G92 artifacts and their deployment status.
- Rechecked the user-supplied Octopus Max EZ V1.0 pinout image. A previously cited external board-document path is not available locally, so the handoff will preserve verified signal pins while explicitly requiring live-config confirmation of direction/inversion before any later motion.
- Created `tmp/corexy_chat_handoff_20260825.md` with credential-redacted machine identity, control architecture, M1-M10 mapping, LYX commissioning data, laser/Tap/QGL/RTCP status, deployed-vs-tmp distinctions, safety blockers, prohibited retries and acceptance-gated next steps.
- Re-read the complete 768-line handoff and ran structural/credential checks. All requested sections are present, fence markers are balanced and no stored password pattern was detected.
- Completed the semantic audit: the startup prompt is 394 characters, all referenced local artifacts exist, M6/M7 chronology is explicit, and every span-60 statement consistently says staged/not formally deployed. Updated `task_plan.md` to hand off the next action to a new conversation.

## 2026-08-14

- Corrected the active M6 extruder configuration from 4 to 16 microsteps and from 10 us to 5 us step pulse duration.
- Restarted Klipper successfully; state returned to `ready`.
- Created backup `/home/shu/printer_data/config/printer.cfg.bak-before-lyx-m6-sync-20260814-152541`.
- Confirmed a CH340 serial adapter at `/dev/ttyUSB0`.
- Initial RS485 probing failed because the wiring was physically disconnected.
- User reports RS485 wiring is now restored, serial communication has been independently verified, and the port is released.
- Next: read LYX registers, align parameters, then correlate Klipper motion with encoder feedback.
- First post-reconnection scan of addresses 1-8 still returned no Modbus response; expanded the probe to cover addresses 1-247.
- The first full-address scan was interrupted by the local SSH helper timeout, not by a serial error. Verified that no scan process remained and `/dev/ttyUSB0` was released.
- Retried with a 180 s SSH channel timeout. The full address/baud scan completed but found no valid Modbus reply.
- Confirmed `/dev/ttyUSB0` remains present and unowned; moving to raw serial diagnostics instead of repeating the scan.
- User clarified that the successful parameter read/write was through Windows DriveChip.exe. Redirected RS485 diagnostics to the Windows COM port while retaining Klipper/M6 as the motion-control path.
- Identified Windows COM3 as a CH340 serial adapter. DriveChip remains open; proceeding with a non-destructive port-open test.
- Installed pyserial locally and confirmed COM3 enumeration. DriveChip has no adjacent settings file and remains responsive.
- Opened COM3 successfully while DriveChip was disconnected in its UI. Read the complete LYX register baseline at address 1, 38400 baud.
- Found the control-chain mismatch: LYX=4 microsteps while Klipper=16 microsteps. All other required control registers are already correct and alarm-free.
- Changed LYX from 4 to 16 microsteps, saved to flash and verified by full register readback. No alarm was introduced.
- Ran the first synchronized Klipper/RS485 motion test. It failed the encoder-motion threshold; the test script automatically disabled the extruder and stopped before issuing the reverse move.
- Verified after failure that Klipper remained ready and idle, the extruder was disabled, and LYX remained alarm-free with an unchanged position. Prepared a serial-internal isolation test rather than repeating the same M6 move.
- Ran the initial serial-internal isolation test with M6 disabled; it did not start. Updated the next test to assert only M6 EN while keeping external STEP generation off.
- Repeated with Klipper M6 EN asserted; internal motion still ended immediately. Verified all volatile trajectory registers were written correctly. Moving to a temporary, automatically restored enable-polarity test.
- Completed the temporary high-active EN isolation test successfully. Accurate forward/reverse closed-loop motion and encoder feedback were observed; all runtime changes were restored automatically.
- Verified the active-low behavior directly in the installed Klipper source. The configured `!PD5` logic is correct, shifting focus from software inversion to physical header placement/pin order.
- First M5 header-identification attempt was rejected safely before any motion because V is registered as a G-code axis. No serial/internal motion ran; updating the test to unregister and restore V around the enable-only check.
- Completed corrected M5 and M4 EN-only candidate tests; neither is connected to LYX EN. Both U/V axis registrations and disabled states were restored.
- Prepared and reviewed a temporary M7 EN-only output config. The first activation invocation failed locally before execution because of an SSH-helper argument mistake; active printer.cfg was not changed.
- Activated the reviewed M7 EN-only test config, confirmed M7 was not connected to LYX EN, then restored the formal printer.cfg and restarted Klipper successfully.
- Switched only the extruder enable pin to non-inverted `PD5` for a matched high-active diagnostic and restarted Klipper successfully. LYX `0x18` has not yet been saved high-active.
- Completed matched high-active Klipper/LYX motion with live encoder correlation. All motion checks passed, and the test wrapper restored LYX to low-active afterward pending the final persistence decision.
- Persisted the proven high-active pair: updated printer.cfg comments, retained Klipper `enable_pin: PD5`, saved LYX `0x18=1` to flash, and verified the full register set.
- Completed the faster 1.0 mm forward/reverse quantitative validation. All acceptance checks passed and the extruder was disabled afterward.
- Verified final Klipper and LYX state, then deleted the temporary SSH/SFTP helper files that contained the supplied password.

## 2026-08-20

- Started a new read-only inventory phase for the current Octopus Max EZ controller and the `tan` Raspberry Pi environment.
- Recorded the supplied board pinout as the current hardware baseline and prepared to locate the custom RTCP implementation without motion or configuration changes.
- Tested the previous IP `192.168.5.119`; it is currently unreachable, so discovery moved to a read-only scan of the local `192.168.5.0/24` network.
- Discovered and positively identified the `tan` controller at `192.168.5.124`. Moonraker is reachable, but Klipper is using an eddy standalone config and cannot connect to its MCU.
- Authenticated successfully as `tan`. The first RTCP source listing reached the Pi but failed while printing Unicode locally; updated the read-only SSH helper to emit UTF-8 safely.
- Re-ran the source inventory successfully. Confirmed extensive RTCP backups, a simple math test, a custom cradle-five-axis Klipper kinematics file, toolhead patches, RTCP-specific configuration, firmware backup and G-code test programs.
- Confirmed the systemd unit's environment deliberately launches the non-RTCP `/home/tan/klipper-v013-runtime-77d5d942e` tree. That running tree lacks `cradle_5axis.py`, while the separate `/home/tan/klipper` checkout contains the RTCP kinematics and extensive toolhead changes.
- Confirmed the active configuration is a standard Cartesian compatibility wrapper, not the archived XYZAC/RTCP configuration.
- Diagnosed the current MCU error as an earlier missing-device event: the exact configured by-id symlink is now present, but Klipper has not reconnected since the device appeared. No restart or configuration change was performed.
- Traced the RTCP math and queue integration: logical XYZAC is transformed around the calibrated pivot into separate physical XYZ and AC queues, with inverse position reconstruction, two work-offset frame modes, and duration-preserving speed scaling.
- Reviewed the saved pause/cancel/resume/homing macros and confirmed they contain RTCP safe-disarm and resume-block protections, but they are not included by the current compatibility configuration.
- Established the exact MCU failure timeline: Klipper started 14 minutes before the Octopus enumerated. The correct device node is now present and unowned, so the present error is stale startup state rather than a currently absent USB device.
- Performed read-only syntax compilation of the three custom RTCP-related Python files; all parsed successfully. No MCU reconnect, service restart, configuration switch, or motor command was issued.

## 2026-08-24

- Began Phase 7 for the physical CoreXY test machine at `192.168.5.119` using the supplied `shu` account.
- Recorded the machine photograph and the goal of completing a curved-surface print.
- Established a read-only safety gate: no service restart, configuration mutation, motor enable, homing, heating or print command until the live system inventory is complete.
- Confirmed the host is online and Mainsail/Moonraker/Klipper are presently operational; Klipper reports `ready` before any intervention.
- Authenticated read-only to the `shu` Pi and positively identified the active source, config, MCU serial, custom services and USB devices.
- Mapped the current motor layout: CoreXY X/Y, four independent Z motors on M3-M6, LYX extruder on M7, U rotary axis on M8 and V rotary axis on M9.
- Confirmed XYZ is presently homed and idle, while the advanced host reference/mesh/laser workflows are loaded. No motion, heat, service restart or remote file modification was performed.
- Read the complete home/reference/leveling workflow and queried the live macro/stepper state.
- Identified the first concrete blocker: host-side `HOME_U` laser leveling failed with exit code 5, leaving the machine in an incomplete U-tram stage with U enabled but unreferenced. No attempt was made to resume or move it.
- Located the host workflow service and its serial-device access. A broad read-only recursive source search ran longer than the SSH response window and left a remote grep process; the exact diagnostic PIDs were terminated and verified gone.
- Read the active Fusion V2 hardware configuration and verified its real-motion safety envelope and serial sensor binding. No current-day Fusion V2 run artifact was produced by the failed U reference attempt.
- Confirmed `HOME_U` delegates to an external `fusion_home_u` Moonraker/Klipper remote method rather than the loaded Klipper laser-level extra.
- Identified `printer-control.service` as the websocket remote-method owner and traced exit code 5 to its external J100/laser subprocess gate.
- Read the complete latest U-calibration report. Confirmed the laser data and response model were accepted, but the run reached its roughly 12-degree total forward-correction limit with about 1.88 mm residual remaining. A final one-microstep move worsened the residual and was automatically rolled back, producing exit code 5.
- No retry, motor command, heater command, restart or remote file change was issued while diagnosing the report.
- Queried the live Moonraker position map and confirmed the laser calibration's accepted corrections remain physically represented as U=`20.723845 deg`, while V=`0 deg`.
- Confirmed a real U/V double-remapping defect in `printer_control_console/backend/moonraker.py`; no remote code change has yet been applied.
- Backed up and fixed the control console's U/V double-remapping defect, added a live-order regression test, and passed all 38 backend tests.
- Restarted only `printer-control.service` to load the corrected code. It returned active and re-registered its Klipper remote methods; no axis moved and no heater target changed during this source fix.
- Detected a volatile Klipper state reset and stopped before movement. Log timing later showed Klipper reinitialized at 15:43:53, before the 15:44:33 control-service restart; attribution was corrected and log tracing continues.
- Correlated the restart to a concurrent upload from `192.168.5.107` followed by a recorded `RESTART` command. Preserved those newly uploaded minimal-homing workflow files without editing them.
- A read-only endstop query was safely rejected because Klipper had subsequently lost MCU communication. Confirmed all motors are disabled, printer is shutdown/standby, and heaters remain off.
- Traced the shutdown to an actual Octopus USB disconnect at 15:48:53. The configured MCU device did not re-enumerate during a 30-second wait; stopped before issuing a futile `FIRMWARE_RESTART`.
- Adopted the user's temporary-artifact rule: all subsequent unapproved test files will be staged under `tmp` and will enter active machine directories only after review.
- After the user restored the MCU connection, positively matched the Octopus serial identity and completed a successful `FIRMWARE_RESTART` recovery.
- Verified a cold/idle/disabled baseline and confirmed all six configured homing endstops are open before motion.
- Executed the live full XYZ homing workflow successfully. The machine is settled at X0/Y0/Z105 with the machine reference valid and U/Tap/gantry/mesh references still invalid as expected.
- Ran the second strict J100 U-calibration pass. It materially reduced the residual during measurement, but strict fit-confidence checks failed and the controller automatically rolled U back to its starting logical position without alarm.
- Preserved all new calibration reports in the laser application's existing data directory; no new test script, config or G-code file was added to an active system directory.
- Parsed the post-correction CSV data and separated two issues: intermittent approximately 2 mm false-low readings and repeatable no-return samples near the positive scan edge. No confidence threshold was weakened.
- Created a copied alignment config only in the approved Pi/local `tmp` review area and verified it matched the active config except for report/model paths. Its first scan-only run confirmed the +Y endpoint has no optical return and aborted safely before calibration.
- Shortening the staged span exposed a dependent validation constraint (`minimum_paired_bins`). Adjusted only the temporary review config; no machine motion occurred during the rejected run.
- Completed positive and negative scan-only diagnostics using the staged 60 mm geometry. Both passed with full coverage, low RMS and close agreement; all generated artifacts remain under the Pi `tmp/codex_review` directory.
- Completed a bidirectional span-60 scan. It passed all existing confidence thresholds with low directional disagreement, establishing a clean basis for a temporary response-model recommission.
- The first staged response recommission exposed the remaining 80 mm point-offset dependency and exited without a model. Verified the commanded ±0.2-degree probe cycle returned U to its starting logical position, then corrected only the local `tmp` review config for a v2 retry.
- The v2 span-60 response recommission completed successfully and produced a valid isolated model in the Pi review `tmp` tree. Verified U returned to its starting position and no active calibration file changed.
- Completed the strict staged span-60 calibration successfully. The platform is physically corrected, logical U was defined as zero, residual is under 0.01 mm, and every test artifact remains in the review `tmp` tree.
- Promoted only the verified volatile U-reference flags; no calibration config/model was copied into active directories.
- Reconciled the live homing behavior with a second concurrent config update at 15:57 and confirmed the guarded pre-15:43 homing/workflow files are currently active. Tap probe is open and ready for its guarded reference stage.
- Ran the guarded Tap Z-reference stage. It stopped safely on probe-repeatability failure and did not establish Z0; captured all 12 contact results showing a 0.125 mm monotonic drift.
- Detected that the failed probe cycle left Tap engaged. Lifted Z upward by 5 mm, verified the probe released/open, and kept the Tap reference invalid pending a fresh accuracy run.
- Completed two consecutive 10-sample Tap accuracy runs. Repeatability improved substantially and the later contacts stabilized within 0.003125 mm; prepared a retry using the original strict tolerance.
- Retried Tap with the original strict settings and passed all three samples identically. Print Z reference is now valid.
- Detected an unexpected E=-12 G-code offset after Tap's G92 operation and paused before gantry/extrusion work to inspect the custom Klipper coordinate state.
- Captured the internal base state and ruled out physical extrusion or an external E command. Identified scientific-notation leakage from the Tap macro's unformatted near-zero Z value as the matching failure mechanism.
- Staged and dry-run validated the fixed-decimal Tap patch under `tmp`, reproduced the parser bug deterministically, and normalized the volatile E coordinate without movement. Active configuration is still unchanged pending review.
- Started the four-point gantry survey. It stopped safely on first-corner Tap repeatability scatter before producing a survey result; lifted away from the bed and verified probe open.
- Ran a no-file manual accuracy survey. Captured two corner medians, then aborted at the third point because Tap asserted while the nozzle was still high above the bed.
- Lifted Z to machine 31.383 mm and moved back to X0/Y160; Tap remained triggered. Stopped all probing/motion escalation and left heaters off pending physical inspection.
- Resumed read-only diagnosis from the 20:28 Mainsail screenshot. Confirmed the visible exit code 5 and endpoint position X33.3/Y204/Z105; next action is to parse the matching 20:28 and 20:18 laser JSON reports without changing the active calibration files.
- Parsed and compared the 20:28 and 20:18 formal JSON reports. Both failed the same initial-coarse confidence gate because continuous coverage was 0.59375 against a 0.600 minimum; each had six consecutive no-return samples at the positive-Y edge and applied zero U correction.
- Verified the valid-data fit RMS remained good, the active 80 mm configuration/model were unchanged, and no newer report superseded the 20:28 run. Read-only live status remains Klipper ready at X33.3/Y204/Z105; no machine command or remote write was issued.
- Cross-checked the rejection against the laser source and compared the active 80 mm config with the isolated span-60 review copy. Confirmed the program's quality gate is operating as coded and the staged geometry/model pair has already passed strict end-to-end calibration.
