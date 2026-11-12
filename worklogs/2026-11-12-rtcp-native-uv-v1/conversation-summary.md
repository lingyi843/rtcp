# 本次对话总结

## 1. RTCP 的职责

本次确认 RTCP 解决的是：

```text
CAM/切片输出 TCP 位置和姿态
    -> RTCP 根据 U/V 和旋转中心求实际机器 XYZ
    -> 既有 CoreXY + 四 Z + U/V + E 同步运动学
```

RTCP 不是简单地在上位机后台持续补发偏移 G-code，而是对目标轨迹做几何变换，
并把结果放入同一个 Klipper 运动队列。

## 2. 本机结构和坐标定义

- 机器：CoreXY，喷嘴 XYZ 龙门，摇篮式 U/V 平台。
- U 绕机器 X 轴旋转，V 绕平台/随 U 倾斜的局部 Z 轴旋转。
- 变换顺序：`Rx(U) * Rz(V)`。
- 当前机器以实际旋转中心作为 XY 机器零点，床面为 Z 零姿态。
- G-code 逻辑 XYZ 定义为平台在 `U=V=0` 时、以旋转中心为零点的工件坐标。
- U/V 是实际关节角，平台水平为零姿态，转角数值直接进入运动学。

## 3. `.122` 原生 U/V 迁移

工作树：

```text
/home/jin/klipper
/home/jin/printer_data/config/printer.cfg
```

结果：

- `kinematics: corexy_uv`
- `stepper_u`、`stepper_v` 为原生扩展轴。
- U 减速比按实物 `260:16`。
- 原生轴映射为 `X=0,Y=1,Z=2,E=3,U=4,V=5`。
- 旧 `manual_stepper u/v` 不再参与正式运动。
- `HOME_U/HOME_V` 为当前位置逻辑参考，不寻找机械限位。
- U/V 参与 XYZUV/E 同步队列。

## 4. 激光与半球扫描适配

解决的问题：

- 不带参数的 `SET_U/SET_V` 会报错，已改成当前位置置零。
- `G28 U/V` 已转到安全参考宏。
- 激光 U 修正的 `SAVE_GCODE_STATE` 顺序导致参考代数变化后恢复失败，已调整。
- 激光和 Eddy V 中心流程不再查找不存在的 `manual_stepper u/v`。
- `motion_report` 已发布 `stepper_u`、`stepper_v` 轨迹队列。
- 半球扫描优先订阅 `stepper_u`，旧机器可回退 `manual_stepper u`。
- 离线敏感性分析和原生 U 轨迹订阅已通过验证。

## 5. Klipper RTCP v1

新增：

```text
klippy/extras/rtcp.py
printer_data/config/rtcp.cfg
```

行为：

- RTCP 默认关闭，Klipper 重启不会自动恢复开启。
- `G1/G0` 在提交前做完整、自适应的 XYZUV/E 子段计算。
- 默认弦误差上限 `0.02 mm`。
- U/V 多圈按连续数值执行，不自动取最短角。
- E 按原始路径参数线性分配到子段。
- 全部子段通过检查后才进入运动队列；任一失败则整条 G1 拒绝。
- RTCP 开启时阻止 G28、G92、探测、四 Z/激光/Eddy、U/V 重新参考和电机失能命令。
- 电机失能、Klipper 重启或机器坐标重设会使 RTCP 自动失效。

命令：

```gcode
RTCP_ENABLE
RTCP_DISABLE
RTCP_STATUS
RTCP_SET_OFFSET X=... Y=... Z=...
```

## 6. 五轴操作台开关

五轴操作台右下角增加常驻开关：

- 灰色 `OFF`：机器坐标模式。
- 绿色 `ON`：RTCP 工件坐标模式。
- 每秒从 `/control/api/status` 同步实际状态。
- 操作需要五轴操作台运动授权。
- 正在打印、未回零、U/V 未参考或 RTCP 未加载时显示错误并阻止切换。

新增接口：

```text
POST /control/api/rtcp/enable
POST /control/api/rtcp/disable
```

## 7. 验证

- 原生 U/V 参考、小角度运动、G28 U/V 和状态恢复通过。
- 激光 `Saved state expired` 已修复。
- 半球扫描 `manual_stepper u is not valid` 已修复。
- RTCP 全套离线测试 `129` 项通过。
- wheel 隔离安装通过。
- Klipper、激光服务、半球扫描服务和五轴操作台服务均为运行状态。
- 五轴操作台 RTCP 状态、授权保护和未回零拒绝已验证。
- 尚未执行真实 RTCP 打印、加热或大角度联动运动。

## 8. 当前最重要的限制

- U/V 方向暂按 `u_sign=1`、`v_sign=1`，还需实机小角度验证。
- 视觉偏移和扫描重构模型坐标不能重复补偿。
- 实际旋转中心、pivot Z、V 绝对相位和机械安全角度仍需逐台确认。
- 当前 RTCP 不自动修改打印开始/结束宏。
- 当前没有完整碰撞模型，轴范围合规不等于不会碰撞。

