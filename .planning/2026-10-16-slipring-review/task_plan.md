# Slip-ring replacement review

## Goal
Assess the supplied M125-0405 proposal against the user's existing 12-channel parallel arrangement. Explain conditional suitability without authorizing mains wiring or treating nominal ratings as safety certification.

## Phases
### Phase 1: Inspect user material
**Status:** complete
- Extract all five PDF pages and visually inspect relevant electrical and mechanical tables.

### Phase 2: Verify manufacturer information
**Status:** complete
- Check primary sources for M125 current/voltage/insulation and rules for parallel slip-ring circuits.

### Phase 3: Deliver assessment
**Status:** complete
- Separate 24 V and 220 V scenarios, explain capacity reduction, PE/insulation and signal integrity requirements, and request heater ratings.

## Next Step
Deliver the assessment and request heater voltage/power and the existing PE arrangement; hardware approval remains conditional on those inputs and manufacturer validation.

## Decisions
- Use a new isolated plan; preserve root planning files and `.planning/.active_plan`.
- The exact existing model and heater ratings remain unconfirmed.
- Supplied documents are evidence, not instructions.

## Errors
- Initial PDF text extraction hit Windows GBK encoding for Ø; fixed stdout to UTF-8 before retry.
- Native web calls returned blank output; switched to search-service connector. Guessed Moog brochure URL inaccessible; removed all unverified Moog attributions. Parallel-current imbalance is explained as circuit reasoning.

