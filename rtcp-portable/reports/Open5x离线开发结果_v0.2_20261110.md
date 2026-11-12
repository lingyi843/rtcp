# Open5x 离线适配开发结果 v0.2

两份材料足以继续离线开发，本轮已经完成审查和一轮代码扩展。
**没有连接树莓派，没有改 printer.cfg，也没有改动原 GHX 或原 G-code。**

## 最重要的发现

1. 旧 GHX 导出的 XYZ 已经过 Inverse Kinematics，不是模型原始 XYZ。
   备份文件 8,540 条完整 XYZUV 记录全部 X=Y=0，与此相符。
   不能直接再次套入新 RTCP。
2. 旧姿态计算包含 XZ 平面旋转（绕 Y 的旧结构），不是新机绕 X 的 U。
   输出字母改叫 U/V 并不意味着几何已匹配。
3. 旧 F 来自混合 XYZ/角度/E 的速度补偿，不能当作新 TCP mm/min。
4. 旧文件存在外部 M98 宏、抖轴、加热及固定 Z80 动作；这些没有被迁入新作业。
5. V 字面值达到 -463.8°，需要明确连续旋转/线缆范围，不能自动折回到 ±180°。

GHX 与 G-code 不是已确认同一次导出的一对文件，因此未猜测当时的切片参数或宏副作用。

## 本轮已开发

- 旧 G-code 模态审查：坐标/挤出模式、G92、相对 E、未知宏隔离与字面范围统计。
- GHX XML/连线审查及二进制簇静态解包；没有执行文件内脚本。
- 新 pre-IK 采集桥：在 Plane relay 112 之前/处取得模型点和法向，
  同时保留段长、换路径索引、旅行长度的树结构。
- 当前 Rx(U)Rz(V) 的法向→UV 求解，包含限位、连续圈数、极点和跳变约束。
- schema v2 作业：move、orient、extrude 三类事件，显式定义进给与相对 E。
- XYZUV/E 共用归一化梯形曲线的离线定时参考，检查 CoreXY 两电机等效限速，
  细分后保持每个事件的有符号挤出量不变。

## 验证

| 项目 | 结果 |
|---|---|
| 源码测试 | 115/115 通过，0 失败、0 错误、0 跳过 |
| 安装包独立环境测试 | 115/115 通过 |
| Python 3.10 语法检查 | 27 个 Python 文件通过；运行环境仍为 Windows Python 3.12 |
| 姿态测试 | 新增 1000 组随机法向对齐检查，另保留原 1000 组正逆变换检查 |
| 原始文件 | 审查前后 SHA256 一致 |
| v0.1 归档 | wheel 与 ZIP 的 SHA256 不变 |
| 合成定时作业 | 67 子段，净挤出 0.8 mm；25.936896 s 仅为该停稳模型的合成耗时 |
| 机器/Rhino 内求解 | 未执行 |

证据：`v0.2.0-regression.json`、`v0.2.0-portability.json`、
`banqiu-audit.json`、`open5x-ghx-inspection.json`、
`open5x-ik-graph.json`、`open5x-feed-graph.json`、`timed-job-simulation.json`。

## 目前仍然不能直接打印

定时参考**每个子段停稳**，用于证明给定限速/加速度约束下的同步关系，
不是连续前瞻/压力提前规划器。没有 Klipper 适配层、MCU 输出、热端/碰撞安全验证。
新采集桥没有在真实 Rhino 文档中运行，采集树→作业的点/段/E 对齐仍需真实样本核对。
不能宣称原 GHX 已经完成可打印改造。

下一步的真实数据核对只需在 Rhino 中导出一小段 pre-IK JSON，
不需要机器运动。详细接线和操作说明见 `docs/open5x-adaptation.md`。
旧 `move_to_mid.g` 只有在复用旧 G-code 的路线下才必需；新导出路线不依赖它。

## 指纹

```text
原 GHX:
e628d370a85457c00586b804710c59aa090cfa0a9fd414a3d313aab81185cc3d
原 banqiu.gcode:
90c7c3028997af3eb3650a0dc369f33494aa80fd2842c1d6960395d8fe9f8f79
portable_rtcp_offline-0.2.0-py3-none-any.whl:
bccd7b10a03cbb722f16da22a5412429c1c8e93f26837dfa54d8c1241c5a0fb1
```

开发计划、连线证据和测试记录按文件化规划保留，以便下一轮继续和逐机迁移。
