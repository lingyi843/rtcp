# Findings

- Historical records identify `192.168.5.124` as the independent `tan` RTCP experiment controller.
- Historical RTCP source locations include `/home/tan/klipper/klippy/kinematics/cradle_5axis.py` and modified `toolhead.py`; the active service previously used a separate non-RTCP runtime tree.
- Local `cradle_5axis.remote.py` has SHA-256 `58d923d12de16f6465ef3a2177201fb1ebe47bf38e9c8480aee3158908c58d29`, exactly matching the 2026-08-20 remote audit.
- The complete final 2026-08-20 `toolhead.py` is still missing. Its expected SHA-256 is `e96b36c9f2acbe7f567259796d0b40ebe8a5a084186175f49f377a3530513128`, with 2052 lines.
- The nearest complete local predecessor is SHA-256 `a9967430d6676cbf71f482d742dd60bf3e0c506e0ae3c67571c80c307a0e6136`, with 1940 lines. Final safety-command and macro regions were recovered separately from sanitized audit output.
- A 92-file local recovery package and comparison report were produced at `C:\Users\zhangyi\Documents\五轴曲面打印\tmp\tan_rtcp_export_20260901`.
