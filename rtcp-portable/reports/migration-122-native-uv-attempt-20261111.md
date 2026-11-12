# `.122` 原生 U/V 迁移前置检查（2026-11-11）

目标：把 `.124` 已验证的 `corexy_uv` 原生 U/V 运动学迁移到 `192.168.5.122`，同时不影响 `.122` 当前视觉/激光测试。

## 本轮完成

- 读取 `.122` 当前 Klipper 工作树状态；
- 确认 `/home/jin/klipper` 当前基线为 `77d5d942ed2fb6d3f688114f68d236ccd391bda7`；
- 确认 `.122` 当前工作树有未提交修改和未跟踪视觉/激光模块；
- 确认当前 Klipper 服务仍指向 `/home/jin/klipper`；
- 未创建迁移目录；
- 未修改 `.122` 任何文件；
- 未重启服务、未执行 G-code、未运动、未加热。

## 当前阻塞

本轮需要从 `.124` 读取 `corexy_uv.py` 及其配套修改，但 `.124` 当前 SSH/网络不可达（连接超时）。

同时，`KlipperForTW` 仓库的现有配置仍是 `manual_stepper u/v + GCODE_AXIS=U/V`，不包含 `.124` 当前工作树的完整 `corexy_uv` 实现。因此不能仅从仓库生成等价的原生 U/V 迁移版本。

## 下一步条件

`.124` 恢复可连接后，先读取并固定以下文件的版本/哈希，再在 `.122` 创建独立迁移目录：

```text
klippy/kinematics/corexy_uv.py
klippy/toolhead.py
klippy/extras/gcode_move.py
klippy/extras/force_move.py
klippy/gcode.py
```

迁移副本预计使用：

```text
/home/jin/klipper-uv-migration
```

当前运行目录 `/home/jin/klipper` 和 `klipper.service` 保持不变，完成语法、配置加载和 Host 测试后才讨论切换。
