# `.122` 原生 U/V 正式切换记录（2026-11-12）

目标：在完成备份后，将 `192.168.5.122` 正式切换到原生 U/V 运动学。

## 备份

已完成完整备份：

```text
/home/jin/rtcp-backups/native-uv-20261112-103323
```

备份内容包括：

- `/home/jin/printer_data/config`
- `/home/jin/printer_data/systemd/klipper.env`
- `/home/jin/klipper`
- 备份清单和部署包

备份大小约 `1.4G`，记录的原 Klipper 提交为：

```text
77d5d942ed2fb6d3f688114f68d236ccd391bda7
```

## 正式修改

正式运行目录已更新：

```text
/home/jin/klipper
/home/jin/printer_data/config/printer.cfg
/home/jin/printer_data/config/machine_functions.cfg
```

核心变化：

```ini
[printer]
kinematics: corexy_uv

[stepper_u]
gear_ratio: 260:16

[stepper_v]
gear_ratio: 60:16
```

保留了 `.122` 原有 X/Y/Z、四 Z、挤出机、CAN 和视觉/激光配置参数，没有直接套用 `.124` 的 X/Y 行程参数。

## 验证

- `klipper.service` 重启成功并保持 `active`；
- Moonraker 返回 `Printer is ready`；
- `gcode_move.axis_map` 已包含：

```text
X=0, Y=1, Z=2, E=3, U=4, V=5
```

- `toolhead.extra_axes` 已包含：

```text
stepper_u=4
stepper_v=5
```

- 当前仍未执行 G28、G1、FORCE_MOVE、加热、挤出或真实打印。

## 回滚

如需回滚，使用备份目录恢复 `/home/jin/klipper` 和 `/home/jin/printer_data/config`，然后重启 `klipper.service`。
