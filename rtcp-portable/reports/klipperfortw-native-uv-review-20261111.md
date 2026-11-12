# KlipperForTW 与原生 U/V 迁移审查（2026-11-11）

## 结论

不能把 `KlipperForTW` 仓库直接当作“原生 U/V 版本”覆盖到 `192.168.5.122`。

仓库当前的 `printer_data/config/printer.cfg` 仍使用：

```text
[manual_stepper u]
[manual_stepper v]
MANUAL_STEPPER ... GCODE_AXIS=U/V
```

仓库的 Host 补丁目录目前主要是四 Z 和 toolhead 相关补丁，没有发现 `corexy_uv.py` 原生 U/V 运动学补丁。

## 与 192.168.5.124 的区别

`192.168.5.124` 上存在额外的本地定制：

```text
/home/zao/klipper/klippy/kinematics/corexy_uv.py
```

并且 `printer.cfg` 使用：

```text
kinematics: corexy_uv
[stepper_u]
[stepper_v]
```

该实现还配套修改了 `gcode_move.py`、`toolhead.py` 等文件。这部分不是当前 `KlipperForTW` 仓库中可直接复制的标准部署内容，而是 `.124` 工作树中的额外本地实现。

## 对 `.122` 的建议

应采用两阶段迁移：

1. 在 `/home/jin/KlipperForTW` 独立拉取和验证仓库；不覆盖正在运行的 `/home/jin/klipper`。
2. 另建一个 `.122` 专用的 `corexy_uv` 迁移分支/运行目录，明确记录从 `.124` 移植的自定义文件和补丁。
3. 先离线启动 Klipper 配置解析与 Host 单元测试，再替换服务指向。
4. 迁移后继续保留 RTCP 默认关闭，确认原有 XYZ、四 Z、U/V 手动功能能够回退。

在没有确认 `.124` 的完整改动来源、文件清单和测试结果前，不应直接把 `.124` 的工作树文件覆盖到 `.122` 的脏工作树。
