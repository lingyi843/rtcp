# CoreXY Five-Axis Curved-Printing Commissioning

## Goal
Verify the complete Klipper -> Octopus M6 STEP/DIR/EN -> LYX9233 closed-loop motor path using RS485 feedback, without heating the hotend.

Additional goal: inventory the current `tan` Raspberry Pi environment and locate/document the user's custom RTCP algorithm without changing machine state.

Current goal: commission the physical CoreXY machine at `192.168.5.119` through a complete curved-surface print, starting with a read-only inventory and then progressing through gated motion, homing, extrusion, thermal and print validation.

Documentation goal: create a self-contained, credential-redacted handoff package for a new conversation, using only local records and without connecting to or changing the machine.

## Current Phase
Phase 8 - Safe basic-machine validation.

## Phases

### Phase 1 - Baseline communication
**Status:** complete

- Confirm Klipper is ready, printer is idle, heater target is zero.
- Enumerate Windows COM ports, identify the DriveChip/LYX adapter and read the LYX register set.
- Stop LYX internal serial motion if register `0x40` is nonzero.

### Phase 2 - Parameter alignment
**Status:** complete

- Verify address, baud, motor type, enable polarity, direction logic, microstep value and run mode.
- Change only mismatched safety-critical control parameters, then save and read back.

### Phase 3 - Closed-loop motion tests
**Status:** complete

- Record RS485 position/error/alarm baseline.
- Command small forward and reverse movements through Klipper M6.
- Verify position changes, direction reversal, return error and alarm status through RS485.

### Phase 4 - Quantitative extrusion-axis validation
**Status:** complete

- Run a larger reversible test at conservative speed.
- Compare commanded motion with encoder position and calculate expected motor angle/pulse count.
- Leave the extruder disabled and Klipper ready.

### Phase 5 - Handoff
**Status:** complete

- Record final configuration, measured results, unresolved physical checks and backup path.
- Remove temporary credentials/scripts from the workspace when no longer needed.

### Phase 6 - Current controller and RTCP inventory
**Status:** complete

- Treat Octopus Max EZ V1.0 as the current motion-control board and preserve its M1-M10 pin map.
- Connect read-only to the current Raspberry Pi using the newly supplied `tan` account.
- Identify hostname/IP, Klipper/Moonraker state, active configuration and board MCU.
- Locate RTCP-related source, services, executables, logs and startup integration.
- Report architecture and risks without starting motion or modifying files.

### Phase 7 - CoreXY 192.168.5.119 baseline inventory
**Status:** complete

- Authenticate read-only as `shu` and positively identify the host, Moonraker, Klipper runtime and active configuration.
- Inventory MCU/USB state, kinematics, XYZ/auxiliary axes, homing, heaters, fans, probes, extruder/LYX configuration, macros and retained curved-print G-code.
- Correlate the live machine with prior M6/LYX commissioning records and identify any configuration drift.
- Inspect current errors and recent logs without restarting services, heating, enabling motors or issuing motion.

### Phase 8 - Safe basic-machine validation
**Status:** in_progress

- Establish a backed-up, reproducible baseline and restore Klipper readiness if required.
- Validate endstops and temperatures before any motor command.
- Perform conservative reversible XYZ and extrusion tests with explicit user-visible safety gates.
- Preserve the verified machine baseline, unresolved safety blockers and staged-only changes in a reusable new-conversation handoff document. Completed on 2026-08-25 at `tmp/corexy_chat_handoff_20260825.md`.

### Phase 9 - Curved-surface print validation
**Status:** pending

- Confirm the intended curved-print architecture, coordinate system and G-code source.
- Run dry-path and no-extrusion validation before heating.
- Execute a controlled first curved-surface print and capture logs, measurements, issues and the frozen working version.

## Next Step
In the new conversation, read `tmp/corexy_chat_handoff_20260825.md` plus the three planning files, then perform a read-only live-state recheck only after the user separately supplies credentials. The first physical blocker remains Tap/PF12 stuck triggered; no probing, QGL, mesh or printing until it is open at high Z.

## Decisions Made

| Decision | Reason |
|---|---|
| Use RS485 as monitoring/configuration only | External Klipper STEP/DIR motion must not overlap LYX internal serial motion. |
| Use cold `FORCE_MOVE` only for commissioning | Avoid heating while still exercising the exact configured M6 extruder stepper. |
| Start with reversible sub-millimeter moves | Limits mechanical risk while producing measurable encoder motion. |
| Read LYX through the Windows COM port | The user confirmed DriveChip.exe on Windows was the working parameter interface; the Pi CH340 is not assumed to be the same physical link. |
| Change LYX to 16 microsteps instead of reverting Klipper to 4 | The supplied target configuration specifies 16 microsteps, and 5 us STEP pulses provide sufficient timing margin at the configured extrusion rate. |
| Use one small serial-internal move as an isolation test | Klipper logged and accepted the external pulse command while LYX position remained exactly unchanged; testing the driver/motor/encoder independently distinguishes signal-wiring failure from motor-side failure. |
| Assert M6 EN during the serial isolation test | LYX internal trajectories still require the external enable input; Klipper can assert EN without generating STEP pulses, preserving isolation. |
| Temporarily test high-active EN and restore it | Both external STEP motion and serial-internal motion failed while Klipper asserted low-active EN. A reversible runtime-only polarity test distinguishes an inactive-low wiring problem from the motor/trajectory path. |
| Treat the motor/encoder/driver path as healthy | High-active EN produced accurate reversible motion with low following error and no alarm; remaining work is confined to the M6 control signals/configuration. |
| Initially keep low-active EN as the diagnostic target (superseded) | Source semantics supported `!PD5`, but subsequent physical tests proved this assembled LYX chain requires high-active EN; the later persistence decision is authoritative. |
| Test adjacent headers by EN only | No external STEP is generated, so candidate-header identification cannot move the machine's native axis motors; only LYX internal motion can occur if its EN wire matches that header. |
| Test a matched high-active pair before requiring rewiring | High-active LYX motion is proven; matching Klipper to it can verify the remaining STEP/DIR path with fully reversible settings. |
| Persist the high-active pair | The synchronized external test matched theory within 0.2%, reversed correctly, returned within 3 raw encoder counts and produced no alarm. Empirical behavior overrides the unverified low-active assumption for this assembled board. |
| Assume the previous controller IP only for discovery | The user changed credentials but did not provide a new IP; `192.168.5.119` is the last known address and will be tested read-only before broader discovery. |
| Select `192.168.5.124` as the current controller | Moonraker reports hostname `tan`, the supplied account name, and exposes the active Klipper paths; this is stronger identification than port presence alone. |
| Treat RTCP as a Klipper fork feature until proven otherwise | Named backups and source hits point to custom `cradle_5axis.py` and `toolhead.py`, while no standalone RTCP service is running. |
| Start the 192.168.5.119 curved-print task with a read-only gate | The attached machine has exposed wiring and a rotary/tilting workholding assembly; motion, homing and heating are unsafe until the live coordinate system, endstops and configuration are positively identified. |
| Stage unapproved test artifacts under `tmp` | Experimental scripts, patches, G-code, configs, reports and generated files must not be placed in active system directories until reviewed. Local staging uses `C:\Users\zhangyi\Documents\五轴曲面打印\tmp`; Pi-side staging uses a dedicated review subdirectory under `/home/shu/printer_data/tmp`. Deployment happens only after review, with a backup and verification record. |
| Use the audited handoff as the new-conversation baseline | It separates the two Pi hosts, resolves historical M6/M7 and PF4/PF12 drift, redacts passwords, records formal-vs-tmp status, and dates the last live snapshot so a new task can safely revalidate instead of guessing. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| RS485 previously returned no data | 1 | User restored the disconnected wiring and released the serial port. |
| Restored link did not answer addresses 1-8 | 2 | Expand the read-only scan to all Modbus addresses 1-247 at every supported baud. |
| Full address scan exceeded the SSH helper's 60 s channel timeout | 1 | Retry with an explicit 180 s SSH channel timeout; the previous remote process has exited and the port is free. |
| Full address/baud scan completed with no valid Modbus reply | 3 | Inspect raw RX data, parity/stop-bit variants and adapter direction behavior; do not repeat the same scan. |
| Pi `/dev/ttyUSB0` was incorrectly assumed to be the DriveChip link | 1 | User clarified DriveChip.exe connected through a Windows COM port; switch the readback path to Windows. |
| Plan update patch did not match the current Next Step location | 1 | Re-applied the update using the plan's actual section ordering. |
| Local Python lacked `pyserial` | 1 | Install the small serial dependency before probing COM3. |
| First synchronized +0.5 mm test produced less than 50% of expected encoder motion | 1 | Extruder was disabled in `finally`; inspect post-test registers and Klipper log before any different test. |
| Serial internal-motion command ended immediately with zero movement | 1 | The LYX enable input was inactive because Klipper had M6 disabled; repeat with EN asserted but no external STEP pulses. |
| Serial internal motion still did not start with Klipper reporting M6 enabled | 2 | Confirmed trajectory registers were accepted; next use a temporary high-active EN test and restore `0x18=0` afterward. |
| M5 candidate enable command was rejected because V is registered as a G-code axis | 1 | Temporarily unregister V, toggle its enable, then restore the V-axis registration with the configured limits. |
| M7 temporary-config activation command passed `90` as the remote command | 1 | No remote mutation occurred; rerun the already-reviewed activation script through stdin with the helper's normal timeout. |
| Previous controller IP `192.168.5.119` is unreachable on 2026-08-20 | 1 | Scan the local `/24` for SSH/Moonraker endpoints and identify the `tan` host by authenticated hostname. |
| RTCP source inventory output contained emoji that Windows GBK could not print | 1 | Change the SSH helper to write UTF-8 bytes directly, then rerun the same read-only query. |
| Broad HOME_U source grep exceeded the useful SSH window and left remote diagnostic PIDs 9009/9018 running | 1 | Terminated only those diagnostic PIDs and replaced the broad `/home/shu` search with targeted service/source-path inspection. |
| A targeted SSH command contained a Windows-decoded surrogate from Chinese regex text and Paramiko refused to encode it | 1 | Remove non-ASCII search literals and retry with ASCII-only patterns; no remote command was executed. |
| ASCII retry stopped after Moonraker service output because `set -e` treated a non-matching process grep as fatal | 1 | Re-ran without fail-fast semantics and guarded optional grep operations with `|| true`. |
| Target Pi does not have `rg` installed | 1 | Use targeted `grep -R`/Python source inspection on the Pi; keep `rg` as the preferred local search tool. |
| First U/V source patch had an incorrect unified-diff hunk length and `patch --dry-run` rejected it | 1 | Recounted all context/add/remove lines and corrected the hunk metadata before any remote source file was modified. |
| A PowerShell-quoted remote command exposed `/dev/null` to local redirection and tried to open `C:\dev\null` | 1 | Switched complex SSH commands to a literal PowerShell here-string so shell redirection is evaluated only on the Pi. |
| `QUERY_ENDSTOPS` was rejected because Klipper lost MCU communication | 1 | Verified the shutdown/disabled/heater-off state; inspect USB enumeration and kernel/service logs before attempting `FIRMWARE_RESTART`. |
| `UV_STATUS` diagnostic command is absent from the current configuration | 1 | Read `_UV_AXIS_STATE` directly through Moonraker; do not add an unreviewed compatibility macro to the active config. |
| Temporary scan-only run failed preflight with `plus_y: 0/5 valid` | 1 | Confirmed the +80 mm endpoint is optically outside the target; shorten only the staged diagnostic span and leave the active calibration config untouched. |
| Span-60 staged config retained `minimum_paired_bins=29` and failed validation | 1 | Set the temporary review copy to 21 paired bins, leaving the active 80 mm/29-bin calibration unchanged. |
| First span-60 response recommission retained point offsets `[+80,0,-80]` and could not obtain complete three-point data | 1 | Updated only the staged review config to `[+60,0,-60]`, isolated the retry reports, and left active calibration/model files unchanged. |
| `TAP_Z_REFERENCE` failed with `Probe samples exceed samples_tolerance` | 1 | Kept Tap reference invalid; captured monotonic 15.08125→15.20625 mm drift and moved to probe-accuracy/settling diagnosis instead of weakening tolerance. |
| First `PROBE_ACCURACY` found the probe already triggered | 1 | Lifted Z +5 mm away from the bed and verified Tap open before any further probing. |
| Four-point gantry survey failed at the first corner on Tap sample tolerance | 1 | Stopped before QGL/reference changes, lifted Z +5 mm, and moved to corner-specific probe accuracy diagnosis. |
| Tap became permanently triggered before the third survey point despite lifting to machine Z31.383 and moving away | 1 | Stopped all probing/QGL/mesh work; physical Tap switch and PF12 cable inspection is required before software can continue safely. |
| A nested PowerShell `python -c` validation command produced a parser error before execution | 1 | Replaced nested quoting with a literal here-string; verified no upload or remote change occurred in the failed invocation. |
| An accidental wait call referenced nonexistent execution cell IDs | 1 | No machine or file action occurred; discarded the invalid calls and resumed with the SSH/image inspection tools. |
| Previously referenced `F:\agentInformationDepo\...\motor_driver_pins.md` is unavailable in the current local environment | 1 | Use the retained verified pin facts in `findings.md`, the user-supplied board image and the standard Octopus M1-M10 signal table; require a fresh active-config read before future motion. |
| First handoff-document patch omitted an added-line prefix inside a code block | 1 | No file was created; regenerate the complete Add File patch programmatically so every content line receives a valid `+` prefix. |
| First attempt to log the handoff patch error did not match the backslash text in `task_plan.md` | 1 | Read the exact file tail and applied a context-correct patch; no other file was changed. |
