# X42S / Octopus MAX EZ interface verification
## Phases
1. Verify BTT output voltage, socket format and driver adapter options — complete.
2. Verify X42S PLC/opto wiring and electrical limits — complete.
3. Recommend minimum reliable adapter chain and state unverified limits — complete.
## Next Step
If the user proceeds, confirm actual PCB revision/header population and chosen motor channel; verify delivered X42S SKU input current and pulse timing before any wiring or motion.
## Decision
Prefer PLC pulse + CAN for the first short-wire sample because no optical-input current uncertainty is added. Opto + CAN remains electrically plausible at 5V COM but is not guaranteed without load/timing checks. Use native M1–M7 signal headers when present; only use an EZ-compatible breakout if actually taking signals from the EZ socket. A standard A4988/StepStick adapter is not directly socket-compatible.
## Errors and resolution
- Existing MAX-EZ-connector-official.png was not a valid readable image; downloaded and inspected the official repository connector and pinout PNGs instead.
- Web PDF fetches rejected application/octet-stream; downloaded PDFs using HTTPS and rendered relevant pages locally.
