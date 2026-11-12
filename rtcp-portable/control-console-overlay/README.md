# Five-axis control console RTCP switch overlay

This directory is a machine-side overlay for `printer_control_console`.
It adds:

- `machine.rtcp` in `/control/api/status`;
- authorized `POST /control/api/rtcp/enable` and `/disable`;
- a persistent ON/OFF switch card at the lower-right of the five-axis console.

Before copying, stop `printer-control.service`. Back up the destination
`backend/` files and `dist/index.html`. Copy these paths to the matching
`/home/<user>/printer_control_console` tree, compile the Python files, then
restart the service.

Do not copy this overlay over a newer console without reconciling the three
backend files first.
