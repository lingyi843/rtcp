# 2026-11-12 RTCP 原生 U/V 与五轴联动工作区

本目录记录本次 Codex 会话从 RTCP 概念确认、`.122` 原生 U/V 切换、
激光/半球扫描适配，到 Klipper RTCP v1 和五轴操作台开关落地的完整结果。

## 会话产出索引

- `conversation-summary.md`：本次会话的技术推进和关键决定。
- `machine-state.md`：`.122` 当前软件、坐标、接口与安全边界。
- `next-test-plan.md`：RTCP + 视觉 + 激光联动的后续试验步骤和不确定项。

## 主要代码入口

- `rtcp-portable/klipper/klippy/extras/rtcp.py`
- `rtcp-portable/klipper/printer_data/config/rtcp.cfg`
- `rtcp-portable/control-console-overlay/`
- `rtcp-portable/reports/klipper-rtcp-v1-20261112.md`
- `rtcp-portable/dist/rtcp-portable-0.3.0-with-ui.zip`

## 远端记录原则

临时迁移快照、虚拟环境、构建缓存和运行日志不进入仓库。可交付源码、
配置模板、工作报告、必要的参考资料和本次会话工作区进入版本管理。

