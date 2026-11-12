# 192.168.5.122 原生 U/V 轴适配记录

日期：2026-11-12  
设备：`jin@192.168.5.122`

## 问题

- Mainsail 的 U/V 手动参考按钮可能发送不带参数的 `SET_U`/`SET_V`，旧宏会直接报参数缺失。
- `G28 U`、`G28 V` 被 Klipper 入口提前拒绝，无法从界面执行参考。
- 激光运动模块和 Eddy V 中心模块仍按旧 `manual_stepper u/v` 查找或运动，原生 U/V 下会出现 `Unknown config object 'manual_stepper u'`。

## 已完成

- `SET_U`、`SET_V`：省略参数时默认把当前位置定义为 0°；保留显式角度设置。
- 增加 `HOME_V`；`HOME_U` 保持“当前位置参考、无端点运动”的安全语义。
- Klipper `G28 U/V` 入口改为分别路由到 `HOME_U/HOME_V`，不会误触发 XYZ 回零。
- 激光 `laser_motion` 改用 `stepper_u/stepper_v` 原生轴检查与原生 `G1 U/V` 规划。
- Eddy V 中心流程改用原生 V 相对运动，移除运行时对 `manual_stepper v` 的依赖。
- 适配前已备份：
  `/home/jin/rtcp-backups/native-uv-u-fix-20261112-114938`

## 验证

- Klipper 重启后状态：`ready`。
- `G28 U`：成功，U `referenced=true`。
- `SET_U`（无参数）：成功。
- `G1 U0.1 F6` 后 `G1 U0 F6`：位置从 `0 → 0.1 → 0`，U 保持 `referenced=true`。
- `G28 V`、`G1 V0.1 F6`、`G1 V0 F6`：成功，V 保持 `referenced=true`。
- 当前轴映射：`X=0,Y=1,Z=2,E=3,U=4,V=5`。
- 重启后的日志未出现新的配置错误、`Unknown config object` 或宏评估错误。

## 说明

U/V 当前没有物理端点，因此 `HOME_U/HOME_V` 是“当前位置设为零”的逻辑参考，不是机械碰限位。真实激光调平、视觉中心标定前，仍应先完成安全位置确认和 U/V 参考。

## 激光调平 `Saved state expired` 修复

2026-11-12 13:48 的失败发生在激光流程 `step=correct`，不是传感器或标定结果错误。

原因：

- 新版激光 U 修正先执行 `SAVE_GCODE_STATE`；
- 修正运动结束后执行 `SET_KINEMATIC_POSITION U=0`，这会提升 U 的 `reference_generation`；
- 之后才执行 `RESTORE_GCODE_STATE`，Klipper 检测到旋转轴参考发生变化，主动拒绝恢复旧状态；
- 激光流程把该异常记录为调平故障，后续点击就提示先执行 `LASER_LEVEL_RESET`。

修复：

- 将 `RESTORE_GCODE_STATE` 移到 `SET_KINEMATIC_POSITION U=0` 之前；
- 恢复调用者坐标模式后，再更新 U 的参考和缓存状态。

修复前备份：

`/home/jin/rtcp-backups/laser-uv-state-20261112-143534`

回归验证：

- U/V 均执行了 `SAVE_GCODE_STATE → G91 → 0.1° 运动 → M400 → RESTORE → SET_KINEMATIC_POSITION`；
- 未再出现 `Saved state expired`；
- 测试后 U/V 位置回到 0，`referenced=true`；
- `laser_motion.fault=null`、`active_run=null`，Klipper 状态为 `ready`。

## 半球激光扫描 U 轨迹订阅修复

2026-11-12 14:30 和 14:46 的半球扫描失败信息：

`The value 'manual_stepper u' is not valid for name`

原因：

- `hemisphere_laser` 固定订阅 `motion_report/dump_trapq` 的 `manual_stepper u`；
- 切换到原生 U 后，该 trapq 对象名已经不存在；
- 同时 `motion_report.py` 只注册 `manual_stepper` 队列，没有把 `corexy_uv` 的原生 `stepper_u/stepper_v` 队列暴露给轨迹订阅。

修复：

- `motion_report.py` 注册原生 `stepper_u`、`stepper_v` 的 trapq；
- 半球程序优先订阅 `stepper_u`，旧机器仍回退到 `manual_stepper u`；
- 实时 U 轨迹与仿真记录统一使用 `stepper_u` 名称。

修复前备份：

`/home/jin/rtcp-backups/hemisphere-native-u-20261112-145752`

验证：

- `motion_report.trapq` 已包含 `stepper_u`、`stepper_v`；
- 直接调用 `motion_report/dump_trapq NAME=stepper_u` 成功返回轨迹头；
- 离线单参数敏感性接口返回 HTTP 200，不再出现 `manual_stepper u`；
- `hemilaser-web.service` 重启后无相关错误；
- U/V 当前均为 0°，`referenced=true`，XYZ 为 `homed_axes=xyz`。

未在本轮自动执行真实半球 U 扫描运动。
