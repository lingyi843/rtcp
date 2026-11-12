# Open5x 实际文件审查与离线适配 v0.2

## 结论

这两个文件足以继续离线开发，不需要现在连接机器。
它们**不是可直接作为新 RTCP 输入的一组已验证模型点文件**。
本轮保留原 GHX/G-code 不变，也没有在 Rhino 中求解用户脚本。

### 实际 G-code

`banqiu.gcode` 共 8,570 行、8,548 条 G0/G1；
其中 8,540 条包含完整 XYZUV，**全部 X=Y=0**。
U 字面范围 0～62.43°，V 为 -463.8～0.1°，不能自动对 V 取模回到 ±180°。
这些是文件字面值，不是经过标定的物理行程结论。

- G90：显式绝对空间坐标；M83：显式相对挤出。
- 第 7 行已经移动 Z80，第 11 行才有 G21；文件依赖启动前状态。
- 第 13～14 行有 U/V 的“kick”动作，不应原样保留到 RTCP 打印入口。
- 第 19 行 `M98 P"/macros/move_to_mid.g"` 依赖外部宏，内容未知。
- 文件内有加热/等待加热、回抽/恢复、结束加热关闭及 Z80 运动。

审查器不会假定 M98 只移动、不改坐标/模式。该宏之后状态标为未知，
不据此报告可信的总挤出量或打印时间。`known_signed_e_sum_mm=0` 不是“没有挤出”，
需同时看 `unknown_e_delta_count=8544`。

### GHX 的真实导出链

顶层 122 个对象中：

```text
78 Tool Path Evalauation_fixing
  → 112 Plane relay（模型空间平面/法向，新的采集位置）
  → 16 Inverse Kinematics
  → 17 Explode Tree（ACXYZ）
  → 18 Concatenate（写为 x/y/z/u/v）
  → 60/66 插入回抽、恢复
  → 35 Merge 起止代码
  → 37/107 输出 Panel
```

因此，虽然输出字母已经叫 U/V，**XYZ 仍来自旧逆运动学的结果**。
旧 IK 簇内部通过 acos(normal.z)、-atan2(normal.y,normal.x)、
XZ 平面旋转和随动平面旋转计算姿态，模型平面经过两次 Transform 才取出 XYZ。
其倾斜机构属于绕 Y 的旧几何，不能只改轴名来匹配现在绕 X 的 U。
详细连线见 `reports/open5x-ik-graph.json`；不依赖“看起来像半球”的猜测。

44 Speed Compensation 簇先计算：

```text
D = sqrt(ΔA² + ΔC² + ΔX² + ΔY² + ΔZ² + ΔE²)
候选 F = D / 原始路径段长度 × 请求进给
```

然后还有限幅和旅行/挤出分支处理。其 F 不是新格式的直接 TCP mm/min。
旧簇中旅行补偿的除数连接到了路径切换索引流，而不是旁边的旅行长度流，
属于需人工核对的可疑连线；并未据此断言历史打印必然出错。
当前 GHX 的打印速度滑块是 3 mm/s，但不能证明历史备份当时也是该值。

这次读取并静态解包了五个顶层簇。只调用 GH_IO 的归档序列化函数，
没有加载/求解 Grasshopper 文档、没有运行任何嵌入 C#/Python。
解包只用于本地审查，运行时包不依赖 GH_IO。

## 新路线：在旧 IK 之前取数据

保留路径生成，绕开旧 Inverse Kinematics 和 Speed Compensation：

```text
模型点/法向/路径事件
  → 当前 Rx(U)Rz(V) 的姿态求解
  → 实测中心 + 本次工件配准
  → 有误差界的 RTCP 细分
  → XYZUV/E 同一时间参数
```

新 `normal_to_uv()` 把表面外法向对齐机器 +Z（喷嘴尖端指向喷嘴座的方向）。
它检查两组等价姿态分支和连续圈数，受 UV 限位及调用者显式最大角度步长约束。
正极点保留上一 V 值，不为了任意法向方位突然转盘；无合法分支则拒绝，不自动回卷。
这是新模型的法向求解，不是对旧 G-code 角度的隐式取模。
它只约束法向，不提供喷嘴绕自身轴的第三旋转自由度或碰撞规避。

## 已提供的 GhPython 采集桥

文件：`bridges/ghpython_capture.py`。
建议在 GHX 的副本中新增组件，不替换原有输出，不连接任何机器。
输入 P/L/I/T 均设为 **Tree access**，units 设为 Item access：

| 新组件输入 | 现有顶层对象 | 含义 |
|---|---|---|
| P | 112，昵称 Plane | 旧 IK 前的平面树 |
| L | 113，Segment length | 路径段长度树 |
| I | 116，Tool_changing_points | 换路径索引树 |
| T | 117，Path_length | 旅行长度树 |
| units | 手动字符串 `mm` | 先确认 Rhino 文档单位确实为毫米 |

对象索引只针对本次文件；修改组件后可能变化，以连线用途及审查报告为准。
脚本输出 `capture_json`、`status`，**不自动保存文件，不发送命令**。
将 JSON 输出保存为新文件后：

```console
python -m rtcp_portable inspect-capture my-capture.json --output capture-report.json
```

本轮没有实际在 Rhino 内运行这个组件，因此不能宣称原 GHX 已改好且运行通过。
采集桥已用模拟 Grasshopper 数据树做离线测试。

特别注意：不把多个树盲目 flatten 后 zip。Plane 数量、段长数量、换路径索引
可能有不同的首项/分支语义。采集桥保留全部分支路径，验证器不自动批准转换。
下一次真正的 pre-IK 采集结果用于核对这些对应关系、法向正负和原点位置。

## 新定时事件格式

`examples/timed-job.json` 使用 schema_version=2，必须声明：

- `coordinate_space=model_bed_zero`：尚未做机器运动学的模型点。
- `angle_convention=rx_u_rz_v_controller_degrees`：当前配置的 U/V 平台角。
- `initial_pose` 和显式事件；不依赖机器启动前的 G-code 模态。

| 事件 | 进给语义 | 挤出 |
|---|---|---|
| move | 模型路径 TCP mm/min | 带符号相对耗材长度 `e_delta_mm` |
| orient | max(|ΔU|,|ΔV|) 定义的角速度 deg/min | 固定 0 |
| extrude | 耗材 mm/min | 正数恢复/挤出，负数回抽 |

XYZUV/E 各轴共用归一化梯形速度曲线，细分按原始段参数分配 E，末段保留余量，
不按补偿后 XYZ 路长重新计算材料量。额外检查 CoreXY 的 dx+dy、dx-dy 电机等效约束。
无料空走或负 E 不会触发 RTCP 开关；旧加热/宏/坐标切换不允许穿透该格式。

**当前每个子段均停到零速**：它是便于验证的定时可行性基准，
不是生产用的连续前瞻规划器，也没有压力提前、热端检查或 MCU 提交。
由此得到的耗时不代表最终打印耗时，给定的 timing.simulation 参数也不是现场标定值。

## 还需要什么

现在不用补文件，可以继续离线算法/接入契约开发。

进一步闭合“真实 GHX → 新作业”链路时需要：

1. 使用此采集桥从 Rhino 导出一小段真实 pre-IK JSON，核对数据树及法向。
2. 核对该次导出的工艺参数：速度、线宽、层高、耗材直径、挤出倍率。
3. 上机前才需要实测机器参数与届时最新 Klipper 配置。

只有坚持复用旧 G-code 时，才还需要旧 `move_to_mid.g` 及其当时机器/坐标约定。
推荐的新导出路线不依赖这个旧宏；本轮未自动取它，也未连接树莓派。
