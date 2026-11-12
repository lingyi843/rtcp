# 树莓派只读检查记录（2026-11-11）

目标设备：`192.168.5.122`  
登录用户：`jin`  
检查范围：仅读取系统、Klipper、Moonraker、配置和进程；未修改远程文件，未重启服务，未执行 G-code、运动或加热。

## 系统与服务

- 主机名：`jin`
- 系统：Debian/Raspberry Pi，`aarch64`
- 内核：`6.12.75+rpt-rpi-2712`
- `klipper.service`：active/running
- `moonraker.service`：active/running
- 当前未发现独立的 `rtcp` 或 `open5x` systemd 服务
- 当前未发现正在运行的 RTCP 进程
- Klipper 运行用户：`jin`
- Klipper 工作树：`/home/jin/klipper`
- 当前 Klipper 描述：`77d5d942e-dirty`

## 当前 Klipper 结构

`/home/jin/printer_data/config/printer.cfg` 当前包含：

- `[printer] kinematics: corexy`
- `[stepper_x]`
- `[stepper_y]`
- `[stepper_z]`、`[stepper_z1]`、`[stepper_z2]`、`[stepper_z3]`
- `[manual_stepper u]`
- `[manual_stepper v]`
- `[extruder]`
- U/V 通过 delayed g-code `_REGISTER_UV` 绑定到大写 G-code 轴 `U`、`V`

因此当前 U/V 不是 `[stepper_u]`、`[stepper_v]` 这类原生笛卡尔轴，而是 Klipper `manual_stepper` 加 G-code 轴绑定方式。

## 当前 U/V 参数

当前配置读取到：

```text
U: rotation_distance = 360
U: gear_ratio        = 260:16
U: velocity           = 50
U: accel              = 500

V: rotation_distance = 360
V: gear_ratio        = 60:16
V: velocity           = 12
V: accel              = 500
```

注意：用户工程参数中计划使用 U 减速比 `260:18`，但目标树莓派当前 `printer.cfg` 是 `260:16`。本次只读检查没有修改它；后续必须以机械实测和最终确认值为准，不能直接覆盖。

## 现有 U/V 相关功能

当前配置和 `machine_functions.cfg` 中已经存在：

- U/V 启动注册逻辑；
- `UV_JOG`；
- `UV_ASSUME_ZERO`；
- `HOME_U`；
- U/V 状态缓存 `_UV_AXIS_STATE`；
- U 轴调平/绑定/解绑相关宏；
- 启动时的 `open5x_register_uv_axes` delayed-g-code。

这些功能属于现有机器控制流程，不能被 RTCP 初始化流程自动覆盖。

## 工程化结论

第一版移植应保持 RTCP 与现有 Klipper 配置隔离：

1. RTCP 默认 `OFF`；
2. 不自动修改 `printer.cfg`；
3. 不自动重新绑定 U/V；
4. RTCP 只处理明确声明为 TCP 位姿的作业；
5. `UV_JOG`、回零、四 Z 调平、探测、G92、手动移动和电机失能等流程均拒绝在 RTCP 作业状态下切入；
6. 先使用外部离线/主机侧适配器生成 XYZUV/E G-code，再考虑实时 Klipper 模块；
7. 机器端只保留一个 RTCP 根目录和一个机器参数文件，避免把临时结果散落到 `printer_data/config`。

本记录不包含密码、私钥或任何可用于远程登录的敏感信息。

## 版本与改动风险

目标机的 Klipper 工作树不是干净状态：

- 已修改：`klippy/extras/filament_motion_sensor.py`
- 已修改：`klippy/extras/z_tilt.py`
- 已修改：`klippy/toolhead.py`
- 新增未跟踪：`eddy_v_center.py`、`laser_gantry.py`、`laser_leveling.py`、`laser_motion.py`、`laser_reference.py`、`laser_u_level_launcher.py` 及相关模块目录
- Moonraker 还有未跟踪的 `components/timelapse.py`

因此不能通过更新、覆盖或重装 Klipper 来部署 RTCP。后续必须先保存这些工作树状态，并把 RTCP 保持在独立目录中。

本次配置哈希（仅用于后续变更前后对比）：

```text
printer.cfg:          82e78fc0c9dc2a62c8c233c8cc2741b340f26a9358aa039bdb1119c9d07d0cea
machine_functions.cfg: e603bf9d08a9796cf9aef5e9306ca42c3453239823c2be8ecfb8763b52797e9a
moonraker.conf:       edbca3cd786316bc5df6cf76e4c1167865f1674eab69ee94a84cb65c84c541c1
```
