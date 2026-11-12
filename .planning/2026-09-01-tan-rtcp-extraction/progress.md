# Progress

## 2026-09-01

- User restricted the task to the `tan` controller only and explicitly prohibited modifying other Raspberry Pis.
- Created an isolated read-only extraction plan; no network or machine action has yet occurred.
- First read-only check of the historical address `192.168.5.124` did not reach Moonraker; SSH accepted TCP then closed before authentication. No remote state was changed.
- User added a required current-versus-historical comparison because the tan configuration may have changed.
- User confirmed the current `tan` contents are gone and the old IP cannot be used; stopped all live recovery attempts.
- Recovered local June 25, June 27, July 3, July 7 and July 10 RTCP source/config snapshots plus retained G-code and scripts.
- Extracted sanitized 2026-08-20 read-only audit evidence and critical final safety-code snippets without copying session credentials or any other Raspberry Pi configuration.
- Proved the recovered `cradle_5axis.py` exactly matches the 2026-08-20 remote SHA-256 baseline.
- Documented that the exact final `toolhead.py`, final full safety macros/config, firmware binary and remote backup archives remain missing.
- Generated and verified `C:\Users\zhangyi\Documents\五轴曲面打印\tmp\tan_rtcp_export_20260901.zip`; checksum verification and Python syntax checks passed.
