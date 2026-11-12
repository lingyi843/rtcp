# `.122` 当前机器状态

## 软件

```text
Host: 192.168.5.122
Klipper: /home/jin/klipper
Config: /home/jin/printer_data/config/printer.cfg
Kinematics: corexy_uv
RTCP object: rtcp
RTCP default: disabled
```

关键配置：

```text
[stepper_u] gear_ratio: 260:16
[stepper_v] gear_ratio: 60:16
```

## RTCP 配置

```ini
[rtcp]
pivot_x: 0.0
pivot_y: 0.0
pivot_z: 0.0
offset_x: 0.0
offset_y: 0.0
offset_z: 0.0
u_sign: 1
v_sign: 1
u_zero_deg: 0.0
v_zero_deg: 0.0
u_min_deg: -90.0
u_max_deg: 90.0
v_min_deg: -720.0
v_max_deg: 720.0
chord_tolerance_mm: 0.02
require_no_work_offsets: True
```

`offset` 当前只保存在内存时可使用 `RTCP_SET_OFFSET`；正式值确认后再写文件。

## 文件位置

```text
/home/jin/klipper/klippy/extras/rtcp.py
/home/jin/klipper/klippy/extras/gcode_move.py
/home/jin/klipper/klippy/gcode.py
/home/jin/klipper/klippy/extras/motion_report.py
/home/jin/printer_data/config/rtcp.cfg
/home/jin/printer_data/config/printer.cfg
/home/jin/printer_control_console/dist/assets/rtcp-switch.js
```

## 已确认备份

```text
/home/jin/rtcp-backups/native-uv-20261112-103323
/home/jin/rtcp-backups/native-uv-u-fix-20261112-114938
/home/jin/rtcp-backups/laser-uv-state-20261112-143534
/home/jin/rtcp-backups/hemisphere-native-u-20261112-145752
/home/jin/rtcp-backups/rtcp-v1-pre-20261112-160441
/home/jin/rtcp-backups/control-console-rtcp-ui-20261112-162225
```

## 当前使用边界

- `HOME_U/HOME_V` 只是当前位置参考，不执行机械寻边。
- RTCP 启用要求 XYZ 已回零、U/V referenced、无 bed mesh transform、XYZ work offset 为零。
- 打印过程中不要通过界面切换 RTCP；当前接口会拒绝非空闲状态。
- 正式开始作业建议由 `START_PRINT` 在全部准备完成后启用，由安全结束宏在 `M400` 后关闭。

