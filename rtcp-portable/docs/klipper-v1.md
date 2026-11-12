# Klipper RTCP v1

本版把 RTCP 放在 Klipper 的 G-code 坐标层与既有 `corexy_uv` 运动学之间。
不会另起上位机进程，也不会绕过 Klipper 的队列、前瞻或 U/V 同步规划。

## 坐标语义

- G-code `X/Y/Z`：工件/平台在 `U=V=0` 时的坐标；当前机器以实测旋转中心为零点。
- G-code `U/V`：实际关节角，单位度；平台水平、V=0 为零姿态。
- U 绕机器 X 轴旋转，V 绕机器 Z 轴旋转。
- 变换顺序固定为 `Rx(U) * Rz(V)`。
- `pivot_x/y/z` 是旋转中心在物理机器坐标中的位置；当前机器设为 `0,0,0`。
- `offset_x/y/z` 是工件相对实际旋转中心的偏移，随工件一起旋转。

正向计算：

```text
q = pivot + Rx(U) * Rz(V) * (logical_xyz + offset)
```

`q` 是下发给 `corexy_uv` 的物理喷嘴点。E、U、V 不改变含义。

## G-code 处理

RTCP 开启后：

1. `G1/G0` 仍先更新逻辑 G-code 坐标。
2. 每个 G1/G0 在提交运动前先完整计算并检查细分子段。
3. 子段的 X/Y/Z 依次变换为物理机器坐标，E/U/V 按原路径比例插值。
4. 所有子段通过后再进入现有 `corexy_uv` 队列。
5. 任一子段越界、误差无法证明或段数超预算时，整条 G1 拒绝，不部分提交。

默认弦误差上限为 `0.02 mm`。U/V 多圈运动不自动取最短角，严格按 G-code
连续角度执行。

## 命令

```gcode
RTCP_ENABLE
RTCP_STATUS
RTCP_DISABLE
RTCP_SET_OFFSET X=... Y=... Z=...
```

`RTCP_SET_OFFSET` 只能在 RTCP 关闭且队列为空时执行，本版不会自动写入配置。

五轴操作台右下角提供常驻 RTCP 开关卡片。开关调用受运动授权保护的后端接口；
页面启动或刷新后会从 `rtcp` 状态对象恢复 ON/OFF 状态，不会仅依赖浏览器本地缓存。

启用前提：

- XYZ 已完成回零；
- 原生 `stepper_u`、`stepper_v` 均有有效参考；
- 没有床网或其它 G-code move transform；
- 默认要求 XYZ 的 G92/work offset 为零。

## 启停边界

- 回零、探测、四 Z、激光、Eddy、视觉定位、`G92` 和 U/V 参考前先 `RTCP_DISABLE`。
- 打印、空走、回抽都保持同一个 RTCP 上下文；不能按 E 是否出料开关。
- 正常结束先完成退让，再等待队列清空，最后执行 `RTCP_DISABLE`。
- 故障、电机失能、参考重设或 Klipper 重启会自动使 RTCP 失效。
- v1 不自动修改用户的 `START_PRINT/END_PRINT`，需要现场确认安全顺序后接入。

## 当前限制

- 没有碰撞、喷嘴/龙门/夹具几何检查。
- 没有自动标定旋转中心和方向；参数必须来自本机测量。
- 没有实时视觉更新 offset；v1 使用显式设置值。
- 未接入 CoreXY 电机级速度模型、压力提前专用补偿或暂停抬头的坐标系切换。
- 真机打印前必须完成无料、小角度、低速验证。
