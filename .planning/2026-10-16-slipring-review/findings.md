# Findings

## Supplied document
- File: `C:/Users/zhangyi/Documents/xwechat_files/wxid_kwbddehsn4dr22_6b8a/msg/file/2026-10/电子滑环产品规划书.pdf`
- Five pages; PDF text extracted and all pages rendered with pypdfium2 because bundled Poppler was unavailable.
- Proposed M125-0405 / M125A-0405: OD 12.5 mm, length 18.2 mm, four channels at 5 A each, AWG22 leads, stated operating voltage 240 VAC/VDC, stated dielectric withstand 300 VAC at 50 Hz for 60 s, insulation resistance >=300 MΩ at 300 VDC, -30 to 80 C.
- The proposal lists “total current 20 A”; this is not 20 A available to one two-wire heater.
- Compared old MMC250: twelve channels at 2 A each, length 25 mm, two 2.5 mm mounting holes. Proposed A flange has three 3.2 mm holes. Existing model not independently confirmed by the user.
- The proposal says small signals on power channels are “completely fine”; this is too categorical for a thermistor mixed with mains.
- User says old heater uses five parallel channels per conductor and thermistor uses two individual channels. New 5 A single conductor is not a guaranteed equivalent to five 2 A parallel conductors.
- Heater voltage/power and whether existing PE is separately provided remain unknown; previous discussion contemplated 220 V but this does not establish the current heater rating.

## Calculation checks (ideal nominal values)
- New heater circuit: 5 A maximum nominal channel rating, not 10 A or 20 A.
- 24 V * 5 A = 120 W; 220 V * 5 A = 1100 W. These are theoretical nameplate bounds, not recommended operating powers.
- 24 V / 200 W heater: 8.33 A, exceeds 5 A channel rating.
- 220 V / 1000 W heater: 4.55 A, near 5 A; requires derating and thermal validation.

## Visual verification
- Inspected complete pages 2 and 4. Electrical table indeed states 300 VAC/60 s; this is not evidence of a reinforced mains-to-thermistor isolation barrier.
- Page 4 explicitly asserts small signals are “completely fine”; retain as a source claim, not an engineering conclusion.
- “Total current 20 A” appears in the supplied table; it is an arithmetic sum of channel labels, not proof of allowable simultaneous-loading conditions.
- Visually inspected page 3: both flanges are 24 mm OD, but hole patterns differ (3 x 3.2 mm vs 2 x 2.5 mm); housing length differs (18.2 vs 25 mm).

## Manufacturer source
- Opened `https://www.senring.com/capsule-slip-ring/m125.html`: official M125 series page confirms M125-0405 at four 5 A channels, 18.2 mm length; 240 VAC/DC, AWG22 for 5 A channels and dielectric strength 300 VAC at 50 Hz for 60 s.
- IMPORTANT correction after full page parsing: official series table states insulation resistance **200 MΩ / 300 VDC**, whereas supplied proposal states >=300 MΩ / 300 VDC. Earlier preliminary note of agreement on 300 MΩ was incorrect. Request signed current model-specific specification.
- Correct main model values do not establish mains-to-sensor reinforced isolation or a PE application approval.
- Source verification correction: Moog FAQ page parsed only navigation and contained no `parallel`, `current` or `signal` text. Do not cite that page for derating; earlier search-derived note of an explicit Moog statement was not adequately verified.
- Parallel-channel imbalance is used as an electrical-circuit inference, not an attributed manufacturer approval. No application-specific derating coefficient was verified.
- TI isolation guidance distinguishes working voltage, withstand test voltage, clearance, creepage and basic/reinforced isolation. A generic 240 V working rating and 300 VAC test alone do not establish the required mains-to-low-voltage barrier.
- LDO's AC bed guide independently includes bed protective earth and an inline thermal fuse.
- Visually inspected complete page 5: the supplied document itself says final specifications are subject to the manufacturer's formal specification and actual product.
- All five pages have now been visually inspected. Page 1 labels the source as a compiled specification, and page 5 defers to formal manufacturer data; do not treat the supplied planning PDF as an application approval.
- Official M125 search result reconfirms four circuits at 5 A and 18.2 mm length.
- Verified TI isolation resources through the search connector: TI Precision Labs “What are Creepage and Clearance?” and the SSZT546 technical article distinguish working voltage, surge/withstand voltage, creepage and clearance.

## Final primary-source verification
- Correction: direct retrieval of the guessed Moog brochure URL failed; do not use the earlier purported brochure statement. Native web tool returned blank results; reliable final sources were obtained using the search-service connector.
- TI TIDU813B is an unrelated isolated DC/DC design and was not used for the final answer. Verified relevant TI source instead: `https://www.ti.com/document-viewer/ja-jp/lit/html/SSZT546/GUID-84885CF5-5D8A-48E6-AA76-326DA5CC3E8E`.
- LDO Rev A AC-bed wiring guide explicitly includes bed earth, frame protective earth and inline thermal fuse.
- Search-service connector verified Senring page in full: 4 x 5 A, AWG22, 18.2 mm, -30 to 80 C, ≥200 MΩ/300 VDC, 300 VAC/50 Hz/60 s. Its insulation-resistance value differs from supplied PDF.

## Assessment
- Reducing lead count is a reasonable objective, and two suitably rated independent channels can carry a heater circuit while two carry a thermistor.
- Replacement is not electrically equivalent to five parallel 2 A channels per conductor. The old 10 A figure is only an arithmetic ideal; parallel capacity needs manufacturer derating and current-sharing validation.
- New heater circuit is limited by the 5 A channel specification, not summed “20 A.”
- If using mains: four channels have no spare for PE; a separate validated protective-earth path or a suitable extra channel is required for a Class I exposed metal bed design. Do not rely on ordinary bearings as the assumed protective-earth connection.
- Need model-specific insulation approval between mains channels and thermistor channels connected to the low-voltage board; no blanket approval from generic working-voltage rating.
- Validate thermistor continuity/noise while rotating and heating, not just its nominal low current.
- No approval to energize given. User needs to provide actual heater voltage and rated power, confirm the old model and describe PE.

