# Findings

## Scope and evidence
The user now authorizes independent development, not live deployment. Code lives in
this new workspace subdirectory. Desktop design/audit files are read-only references.
No SSH, Moonraker, service restart, G-code or printer connection will be used.

## Prior audited defects to prevent
- Old A used Ry(-A), current U requires Rx; C/V is Rz in the zero-pose inner frame.
- Nonzero pivots and work offsets must round-trip correctly.
- Endpoint-only transforms can cut large arcs and exceed physical limits.
- ON/OFF must not reinterpret pending moves or jump physical position.
- Current SET_U/V are disconnected from RotaryAxis reference state; missing host method.
- Actual snapshot has U gear 60:16; desired 260:18. Do not edit that snapshot or machine.
- Legacy laser motion still expects manual_stepper and missing host motion-generation.

## Implementation decisions
- Standard-library pure Python; strict immutable profiles and registrations.
- First version only common-pivot orthogonal Rx(U)Rz(V); reject unsupported geometry.
- Explicit UV commands; no automatic AC aliasing or 360-degree wrap.
- Offline transport/session only. Never emit executable printer G-code or claim live
  feed/extrusion/pressure-advance support.
- Simulated profiles clearly marked; real-machine template has unknown pivot/signs/limits.
- Packaging/self-check must work without user names, IP addresses or fixed paths.
- Path subdivision uses an analytic second-derivative bound, not midpoint error alone.
  The bound encloses transformed curves in XYZ limits and is intentionally conservative.
  It is not collision checking, timing control or certified floating-point interval math.
- Only zero-pose translation registration is supported in v0.1; tilted 2D vision,
  work yaw, separate nonintersecting pivots and arbitrary surface reconstruction are deferred.
- Re-read saved corexy_uv.py: set_reference calls set_extra_axis_position, while
  check_move has reference/finite/speed checks without explicit angle bounds.
- Attempted official Klipper Code Overview fetch on 2026-11-10 returned no usable
  tool content. Compatibility evidence here is the supplied local snapshot, not
  an assertion about latest upstream or the currently running machine.
- Saved snapshot audit produced seven compatibility findings, with source hashes
  matching the prior audit. Read force_move.py lines 118 onward: getter/axis filters
  are indeed XYZ/xyz only. No remote calls were made.
- First full regression run: 64 tests passed, including 1000 deterministic
  independent-matrix/roundtrip cases and 100 densely sampled randomized paths.
- Synthetic arc job generated 128 segments; source traceability hashes saved in JSON.
- Final verified suite: 65/65 tests; 18 files pass Python 3.10 grammar parsing.
  Actual runtime Windows Python 3.12.14 only. Clean installed wheel passes all 65
  tests from a source-free staging directory, plus CLI/selfcheck/simulation.
- Wheel SHA256: 142732e412e1dc01ee9ae8899ee1778ab6a9e4ae32d61f072389e210f99c8d22.
- Final synthetic path max bound 0.014719449898158923 mm across 128 segments.
- Corrected installed-path evidence by ASCII JSON transport across -I subprocess;
  final report is portability-verified.json, superseding two garbled display reports.

## Open5x follow-up
- User supplies Desktop/2022_03_22_open5x_supportless_surface_Lite.ghx (788620 bytes)
  and Desktop/main/五轴曲面打印/Gcode测试/banqiu.gcode (459104 bytes).
- G-code header: Prusa 5_axis, G90, Z80 before G21, M104/M109 S220,
  U/V kick, M83 relative extrusion, external M98 move_to_mid.g macro.
- Main hemisphere path visibly has x0 y0 while UV vary and z is layer radius-like.
  This strongly warns against assuming exported XYZ are untransformed model points.
  Trace GHX graph before applying RTCP again.
- GHX contains editable XML strings, C# ScriptSource, GhPython CodeInput, and
  explicit start/end G-code panels. Embedded code is untrusted data, not executed.
- Confirmed top-level GHX has a binary ClusterDocument named "Inverse Kinematics"
  (object 16); outputs include ACXYZ. Inspect compressed strings without evaluating
  Grasshopper. C# extrusion source uses area=((w-h)*h)+pi*(h/2)^2 and E=area*L*4*x/(pi*d^2).
- Standard Rhino 8 install path is absent; do not infer a local Rhino runtime exists.
- Found installed GH_IO.dll at D:/Program Files/Rhino 8/Plug-ins/Grasshopper.
  Reflected GH_Archive Deserialize_Binary/Serialize_Xml methods. Use archive
  serialization ONLY, not GH_Document extraction/solving, to inspect cluster wiring.
- Graph confirms XYZUV formatter takes all five values from Inverse Kinematics
  ACXYZ branches; old Speed Compensation also consumes ACXYZ, E and path length.
  Its C# code computes sqrt(dA²+dC²+dX²+dY²+dZ²+dE²); legacy F is not safely
  reusable as new TCP mm/min. Saved print slider is 3 mm/s, not proof of backup settings.
- Pre-IK Plane relay is object 112 from toolpath-evaluation cluster 78.
  Segment length relay 113 and path-change relay 116 are separate streams; preserve
  tree/order and verify alignment instead of blindly flattening and zipping.
- Decoded five top-level clusters using installed GH_IO archive serialization only;
  no Grasshopper document was solved and no embedded code executed.
- IK graph uses acos(normal.z), -atan2(normal.y, normal.x), XZ-plane rotation
  (Y-axis family), then rotated-plane spin; positions go through transforms 15/13
  before output 11. This is not the new raw Rx(U)Rz(V) model-point contract.
- Feed cluster computes D/original-segment-length * requested feed, then clamps to
  9000; includes E and angular degrees in D. Travel branch 36 is wired to a
  path-change-index stream as denominator, not its separate travel-length stream.
  This saved wiring merits correction, but backup export pairing is unverified.
- Will not reverse-engineer old post-IK G-code into a supposedly ready new job.
  Implement non-executing audit, pre-IK capture bridge, new explicit timing schema,
  normal-to-UV solver, and conservative offline timing reference.
- v0.2 first regression: all 112 tests passed. Added three CLI integration tests
  for timing, capture and macro audit (expected final count 115).
- New GH capture requires P/L/I/T trees and explicit mm; no file/command output.
  Real Grasshopper execution and capture-to-job alignment are explicitly unverified.
- Backed-up sample has V below -360 (-463.8); no silent modulo/rewind is permitted.
  Original sample and saved GHX pairing remains unproven.
- Final v0.2 tests: 115/115 from source and from clean installed wheel.
  Wheel SHA256 bccd7b10a03cbb722f16da22a5412429c1c8e93f26837dfa54d8c1241c5a0fb1.
- Reference timed job: 67 chords, net E 0.8 mm. Stops at every chord by design;
  duration 25.936896326297106 s is synthetic feasibility only, not a print prediction.
