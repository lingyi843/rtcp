# Findings

- Source: C:/Users/zhangyi/xwechat_files/wxid_kwbddehsn4dr22_6b8a/msg/file/2026-09/本周成果/CoreXY皮带装配体.STEP
- Size: 81,493,738 bytes.
- Header identifies STEP AP214, AUTOMOTIVE_DESIGN, SolidWorks 2026 / SwSTEP 2.0.
- Embedded export timestamp: 2026-09-05T08:12:55.
- The workspace contains historical machine commissioning records, which are not treated as proof of this model's component configuration.

## Actual geometry review
- STEP import succeeded locally using occt-import-js; the original file was not modified or uploaded.
- 123 PRODUCT definitions; 628 rendered mesh bodies (not 628 unique parts), 816,563 triangles.
- Display triangulation: 0.35 mm linear deflection, 0.45 angular deflection. Bounds are approximate tessellated geometry bounds, not precision metrology.
- Original STEP Y is vertical. Original XYZ bounds size: 511.3195 × 714.1250 × 510.5904 mm. Physical width × depth × height: approximately 511.3 × 510.6 × 714.1 mm.
- Main 2020 frame itself is about 510 × 510 × 630 mm, raised about 84.1 mm above the model floor by the lower support/motor structure.
- Structure: 2020 extrusion outer frame, four vertical MGN9 520 mm rails and four Z belt loops, lower corner Z drive motors, moving CoreXY gantry, two horizontal MGN9 400 mm rails, MGN12 400 mm cross-axis rail and carriage.
- Two XY motors are mounted on the gantry at original Z approximately 463.5–505.5 mm, treated as the rear for viewer direction labels.
- Central lower mechanism: opposed side supports, tilting cradle, sector gear and drive motor, rotary transmission, round print-bed plate labeled 280 mm. Mesh bounds of the bed are about 279.7 × 3.0 × 279.7 mm.
- A brush-ring shaft component is named in the assembly; this alone does not establish an actual installed slip ring or wiring specification.
- Inspected full iso and side images. No populated electronics tray, power supply, controller board, full toolhead/nozzle assembly, or wiring loom is apparent in these views or the component names.
- The model is a static assembly pose; neither usable electronics clearances nor full tilt/rotation/XYZ travel have been validated.
- Local interactive viewer: http://127.0.0.1:8768, served only on loopback. Original mesh geometry is available for rotation, zoom, view switching, and picking.
