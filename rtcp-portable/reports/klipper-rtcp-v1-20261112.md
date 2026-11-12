# Klipper RTCP v1 实施记录

日期：2026-11-12  
目标机器：`jin@192.168.5.122`

## 本机坐标契约

- 逻辑 `X/Y/Z`：平台上 `U=V=0` 的工件坐标；当前机器以旋转中心为 XY 零点，
  Z 零点位于床面。
- `U/V`：原生轴关节角，单位度；平台水平为零姿态。
- U 绕机器 X 轴，V 绕机器 Z 轴，顺序为 `Rx(U) * Rz(V)`。
- RTCP 配置中 `pivot=(0,0,0)`；视觉测得的相对旋转中心偏移使用
  `offset_x/offset_y/offset_z`。

## 第一版实现

新增：

```text
klipper/klippy/extras/rtcp.py
klipper/printer_data/config/rtcp.cfg
```

接入：

- `gcode_move.py` 的 `G1/G0` 在提交前构建完整 XYZUV/E 子段；
- 子段 X/Y/Z 经 RTCP 转为机器物理坐标，U/V 保持关节角，E 按路径比例分配；
- 全部子段通过误差、限位和预算检查后才进入现有 `corexy_uv` 队列；
- `gcode.py` 在 RTCP 活动时拦截回零、G92、激光、Eddy、探测、调平和 U/V 参考变化；
- Klipper 重启后 RTCP 固定为关闭。

命令：

```gcode
RTCP_ENABLE
RTCP_STATUS
RTCP_DISABLE
RTCP_SET_OFFSET X=0 Y=0 Z=0
```

## 安全边界

- 默认要求 XYZ 已回零、U/V 已参考、无床网 transform、XYZ work offset 为零。
- U/V 限位默认 `U=-90..90`、`V=-720..720`，仍应结合本机机械范围修改。
- 默认弦误差 `0.02 mm`；多圈子段不会因端点/中点重合而漏判。
- 任一子段无法证明或越界时，整条 G1 拒绝，不会只提交前半段。
- v1 没有碰撞模型，也不会自动修改 `START_PRINT/END_PRINT`。

## 部署与备份

修改前备份：

`/home/jin/rtcp-backups/rtcp-v1-pre-20261112-160441`

部署文件：

```text
/home/jin/klipper/klippy/extras/rtcp.py
/home/jin/klipper/klippy/extras/gcode_move.py
/home/jin/klipper/klippy/gcode.py
/home/jin/printer_data/config/rtcp.cfg
/home/jin/printer_data/config/printer.cfg
```

## 验证

- Python/Klipper 语法编译通过；
- 全套离线测试 `129` 项通过；
- 隔离安装测试通过，生成 `portable_rtcp_offline-0.3.0-py3-none-any.whl`；
- RTCP 新增的几何、正逆变换、多圈细分、E 分配、预算拒绝、模式保护测试通过；
- Klipper 重启后状态 `ready`；
- Moonraker 可读取 `rtcp` 对象；
- 启动状态为 `RTCP active=false, reason=disabled`；
- `RTCP_STATUS` 和 `RTCP_SET_OFFSET` 无运动测试通过；
- 未归零时 `RTCP_ENABLE` 正确拒绝，没有下发运动。

由于部署后重启了 Klipper，XYZ/U/V 当前需要重新建立参考。本轮没有执行真实 RTCP
打印、加热或大角度运动。

## 五轴操作台实体开关

在五轴操作台页面右下角增加固定式 RTCP 开关卡片：

- 灰色 `OFF`：RTCP 关闭；
- 绿色 `ON`：RTCP 活动；
- 点击后调用受运动授权保护的后端接口；
- 未授权、Klipper 未加载 `rtcp`、缺少 XYZ 回零或 U/V 参考时显示错误原因；
- 每秒读取 `rtcp.active/reason/offset/last_segments`，页面刷新后状态自动恢复。

新增接口：

```text
POST /control/api/rtcp/enable
POST /control/api/rtcp/disable
```

界面文件：

`/home/jin/printer_control_console/dist/assets/rtcp-switch.js`

修改前备份：

`/home/jin/rtcp-backups/control-console-rtcp-ui-20261112-162225`

验证：

- `/control/assets/rtcp-switch.js` 返回 HTTP 200；
- `/control/` 已加载该脚本；
- `/api/status` 已返回 `machine.rtcp`；
- 未授权调用启用接口返回 HTTP 403；
- 授权后未完成 XYZ 回零时，启用接口返回 HTTP 409，未发送运动；
- `printer-control.service` 重启后运行正常。
