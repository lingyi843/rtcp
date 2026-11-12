# Progress

## 2026-09-09

- User authorized read-only access to the `shu` Raspberry Pi using the supplied SSH credentials.
- Audit scope is limited to locating RTCP-related backups and comparing them with the recovered `tan` baseline.
- Moonraker and SSH identity checks succeeded and confirmed the intended `shu` target.
- No motion, heat, service restart, file write or configuration change was performed.
- Completed a filename and archive-member inventory of RTCP-related material.
- Located an `open5x-rtcp-product-test-v2` Git reference inside multiple staged deployments; next inspection will use read-only Git commands.
- Inspected the retained Git ref. It represents a separate MCU-side Open5X RTCP product-test architecture rather than the tan `cradle_5axis.py + modified toolhead.py + cartesian_abc.py` architecture.
- Read the retained protocol v2 document and final RTCP C/preflight symbols; recorded the architectural and coordinate-model differences from tan.
- Revalidated the retained Git ref and enumerated its complete RTCP/Open5X file set. Confirmed the working tree is dirty with unrelated sensor work, so only committed Git objects will be exported.
- Exported commit `4171d0b2...` as a local tar.gz and extracted tree under `tmp/shu_rtcp_backup_audit_20260909`.
- Located and reviewed the documented WSL no-real test runner and its STM32H723/Octopus Max EZ firmware configuration.
- Attempted the documented WSL runner locally. It could not run because this Windows host has no installed WSL distribution. No remote test was attempted and no system component was installed.
- Ran the two RTCP host-only Python suites natively; all 49 checks passed.
- Audited the stream parser and MCU transform. Identified a key integration gap: V2 accepts true TCP XYZ plus IJK tool direction, while the recovered GH workflow generally exports XYZ plus A/C angles.
- Searched active/staged printer configs and deployment archives. No machine-specific `[o5x_tcp]` config or RTCP macros were found, and the deployment manifests did not activate the O5X modules.
- Correlated the referenced firmware hash with the pre-R1 backup binary; further command-dictionary inspection is needed to prove whether that firmware actually contains O5X commands.
- Confirmed no firmware dictionary/build output survives on `shu`; the referenced binary alone is insufficient to prove protocol compatibility.
- Verified all three staged source replicas have the same branch/tree/config hashes.
- Inspected the recovered GHX export contract and established that it targets true TCP XYZ plus explicit A/C G-code, requiring an adapter before use with shu V2.
- Verified all 8,540 historical XYZAC motion records can round-trip through the V2 IJK angle encoding under the default A/C mapping with only floating-point noise.
- Completed static AST checks of the three O5X host modules and their required `klippy/stepper.py` support.
- Generated a 61-file RTCP manifest, SHA-256 list, two source archives, compatibility test evidence and a complete Chinese audit report.
- Verified both source archives with `tar -tzf` and rechecked key hashes against the remote audit values.
- Audit complete: shu preserves a separate MCU-side RTCP V2 source line, not the tan host-side RTCP backup; code-level recovery is possible, deploy-ready recovery is not yet possible without machine-specific data.
- Saved per-commit file inventories for all custom Open5X/RTCP and VM7 commits.
- Exported a second, RTCP-only committed snapshot at `7f33fcd5...`, excluding the later VM7 closed-loop feature commit.
