# 192.168.5.124 U/V 只读检查记录（2026-11-11）

目标设备：`192.168.5.124`  
登录用户：`zao`  
检查范围：仅读取系统、Klipper、配置和源码；未修改远程文件，未重启服务，未执行 G-code、运动或加热。

## 结论

这台机器的 U/V 属于 Klipper 配置层面的原生扩展轴，但不是官方上游 Klipper 自带的标准 U/V 轴。它使用了本地定制的 `corexy_uv` 运动学和对 Klipper 核心的配套修改。

## 配置证据

`/home/zao/printer_data/config/printer.cfg` 中存在：

```text
[printer]
kinematics: corexy_uv

[stepper_u]
rotation_distance: 360
gear_ratio: 260:18

[stepper_v]
rotation_distance: 360
gear_ratio: 60:16
```

当前不是 `[manual_stepper u/v]` 加 `GCODE_AXIS=U/V` 的方案。

## 定制运动学证据

存在：

```text
/home/zao/klipper/klippy/kinematics/corexy_uv.py
```

该模块：

- 继承 CoreXY 运动学；
- 创建 `stepper_u` 和 `stepper_v` 两个旋转轴对象；
- 将 U/V 加入 `toolhead.extra_axes`；
- 为 U/V 分配独立 trapq；
- 参与移动准备、速度同步、拐角限制和队列规划；
- 处理 U/V 参考失效、掉电、电机失能和 `FORCE_MOVE`；
- 当前文件顶部明确说明是“独立 U/V 旋转关节，尚未做 TCP transform”。

因此，这台机器已经具备“原生 U/V 运动轴和同步规划”的基础，但当前运动学本身还不是 RTCP。它接收的是 XYZUV 目标，尚未把 TCP 点和姿态自动转换为机器 XYZUV。

## 当前机械参数

```text
U: 260:18
V: 60:16
```

这与 192.168.5.122 的 `U=260:16` 不同，说明机器参数必须逐机读取，不能共用一份硬编码配置。

## 工程影响

这台机器比 192.168.5.122 更适合作为 RTCP 的后续接入对象，因为 U/V 已进入运动学层并参与 Klipper 的运动队列。不过不能直接把现有 `corexy_uv.py` 当作 RTCP 使用：

```text
当前：TCP/姿态输入 → （缺少 RTCP）→ XYZUV → corexy_uv → 电机
目标：TCP/姿态输入 → RTCP → XYZUV → corexy_uv → 电机
```

建议 RTCP 第一版放在 `corexy_uv` 之前，先把目标 TCP 位姿转换成 XYZUV，再交给现有 `corexy_uv` 进行队列和速度同步。不要先重写 `corexy_uv` 的底层步进逻辑。

## 版本风险

目标机 Klipper 工作树也存在本地修改和未跟踪文件，包括：

- `klippy/extras/force_move.py`
- `klippy/extras/gcode_move.py`
- `klippy/extras/motion_report.py`
- `klippy/extras/z_tilt.py`
- `klippy/gcode.py`
- `klippy/toolhead.py`
- `klippy/kinematics/corexy_uv.py`
- 多个 `laser_*` 模块

因此后续接入必须基于当前版本做快照和补丁，不应更新或覆盖 Klipper。

本记录不包含密码、私钥或远程登录凭据。
