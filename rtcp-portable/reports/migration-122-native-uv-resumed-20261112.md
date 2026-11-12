# `.122` 原生 U/V 隔离迁移续作（2026-11-12）

目标：在 `192.168.5.122` 的独立目录中继续提取 `192.168.5.124` 的原生 U/V 运动学文件，并验证配置加载；不切换当前 Klipper 服务，不影响视觉/激光测试。

## `.124` 文件提取

登录 `192.168.5.124`（用户 `zao`）后，只读确认：

- 主机在线，Klipper 服务处于 `active`；
- 工作树基线：`77d5d942ed2fb6d3f688114f68d236ccd391bda7`；
- `/home/zao/klipper` 存在本地修改和未跟踪的激光/U/V 文件，未执行覆盖或更新。

已提取并固定以下文件：

```text
klippy/kinematics/corexy_uv.py
klippy/toolhead.py
klippy/extras/gcode_move.py
klippy/extras/force_move.py
klippy/gcode.py
klippy/extras/canbus_stats.py
```

`.124` 文件哈希已保存在本地 `.codex-tmp/extracted-124/`，并上传至 `.122` 隔离目录的：

```text
/home/jin/klipper-uv-migration/tmp/extracted-124-klipper-files.tar.gz
```

## `.122` 隔离迁移

迁移目录：

```text
/home/jin/klipper-uv-migration
```

已完成：

- 将提取的六个 Host 文件写入迁移目录；
- 迁移配置保持 `.122` 的硬件参数：U=`260:16`、V=`60:16`；
- `[printer] kinematics` 使用 `corexy_uv`；
- `[stepper_u]`、`[stepper_v]` 为原生扩展轴；
- 将旧 `MANUAL_STEPPER` 兼容宏改为原生轴方式，避免在原生轴上重复注册：
  - `_REGISTER_UV`
  - `UV_ASSUME_ZERO`
  - `HOME_U`
  - `_U_AXIS_UNBIND`
  - `_U_AXIS_BIND`
- 增加 `SET_U`、`SET_V` 兼容宏，使用 `SET_KINEMATIC_POSITION` 建立参考，不发起运动。

## 验证结果

- 六个 Python 文件通过 `py_compile`；
- 迁移配置启动时成功连接 `mcu` 与 `EBB36`，日志出现 `Configured MCU 'mcu'` 和 `Configured MCU 'EBB36'`；
- 迁移配置在独立 Klippy 进程中可进入可用状态；通过隔离 socket 下发 `GET_POSITION`、`UV_STATUS`、`SET_U U=0`、`SET_V V=0`、`GET_POSITION`，请求被正常接收；
- 未执行 G28、G1、FORCE_MOVE、加热、挤出或电机运动；
- 测试进程已停止，临时 socket 已清理。

## 当前运行状态与边界

当前正式服务仍为：

```text
/home/jin/klipper
klipper.service -> /home/jin/klipper
```

正式服务状态仍为 `active`。`/home/jin/klipper` 的既有视觉/激光修改未覆盖，工作树状态保持原样。

本轮只完成“文件提取 + 隔离配置加载 + 宏兼容验证”。尚未执行原生 U/V 空跑、RTCP 接入、服务切换或真实打印。

## 下一步

1. 在隔离目录中增加 `.122` 专用机器参数文件，明确旋转中心、盘面偏移、U/V 正方向和安全限位。
2. 在不切换正式服务的前提下做无运动状态查询和宏回归。
3. 再进行人工确认后的低速空跑；完成后才讨论是否切换服务。
