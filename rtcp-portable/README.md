# 可移植 RTCP 开发版 v0.3

这是独立 Python 算法、离线验证包与 Klipper v1 适配层。
Klipper 适配层默认关闭，真机打印前仍必须完成本机参数、小角度空跑和回退验证。

## 已实现

- 共点摇篮结构：外 U 绕 X、内 V 绕随 U 倾斜的局部 Z，`Rx(U) × Rz(V)`。
- 正/逆变换：机器旋转中心 XYZ、实际轴心相对的工件偏移、U/V 方向与角度零点。
- 自适应路径细分：解析曲率上界、物理 XYZ 行程与 UV 角度限制、资源上限。
- 离线启停状态机：空队列无跳变启停、暂停保留状态、重新设零使视觉配准失效、
  故障/电机失能后必须重新建立参考。
- 严格 JSON 配置、离线路径报告、本地历史快照兼容性检查、标准库回归测试。
- 新增旧 G-code 模态审查、GHX 静态连线审查、逆运动学之前的 Plane 数据采集桥。
- 新增法向→UV 分支求解、显式回抽/空走事件、XYZUV/E 共用梯形时间曲线的离线可行性检查。
- 无运行时第三方依赖；Python 3.10+。实测版本见 `reports/`，不等于已在树莓派验证。
- 新增 `klipper/klippy/extras/rtcp.py`：适配原生 `corexy_uv`，G1/G0 在提交前
  做误差有界的 XYZUV/E 细分，再交给既有 Klipper 队列。
- RTCP 默认关闭，具备 `RTCP_ENABLE/RTCP_DISABLE/RTCP_STATUS/RTCP_SET_OFFSET`；
  回零、激光、Eddy、G92、调平、电机失能等入口有保护检查。

## 尚未实现

没有打印任务自动钩子，不会自动修改 `START_PRINT/END_PRINT`。
不输出真实 E/F 控制、连续前瞻、压力提前或热端控制。v0.2 的定时模型
**每个离散子段都从零速到零速**，仅用于速度/加速度约束验证，不是正式打印规划器。
旧 G-code 只审查、不自动转换；不做网床/探针/工具偏置叠加，也没有完整机器碰撞仿真。
不支持分离的 U/V 轴心、轴线不正交、工件旋转配准或任意倾斜姿态下的二维视觉配准。
因此不能把离线通过理解为实机安全或可打印。

## 坐标契约

```text
机器喷嘴点 = C + Rx(sU × (U-U0)) × Rz(sV × (V-V0)) × (模型点 + d)
```

- `C`：实测共同旋转中心，在**机器喷嘴点 XYZ 坐标系**内的坐标。
- `d`：工件相对实际旋转中心的位移，在床面零姿态轴向表达。
  dx/dy 正数表示工件向机器 +X/+Y 位移；不是取负号的“纠偏指令”。
- 本版假定模型轴向与床面零姿态轴向一致，只有平移配准。
- `sU/sV`：±1，修改配置即可改变几何角度正向；不能同时随意反转电机方向。
- U/V 输入输出都是**平台角度，单位度**。U 减速比为 260:18，但不在矩阵里再乘一次。
- Rhino 原点可以是床面旋转中心；这**不等于机器中心 C=(0,0,0)**。
  `d.z=0` 表示采用工件/床面相对高度为零的假设，不是强制机器 `Cz=0`。
- 视觉结果已经相对实测轴心：不再额外叠加一次“圆盘偏心”。
- 零姿态要求 U=U0、V=V0。V 必须先设本次参考再测视觉；
  再设 V 零点后原配准不能直接复用。

CoreXY 电机混合以及四 Z 电机驱动留给底层运动学，不在 RTCP 几何内重复实现。
外 U / 内 V 的安装次序是本版建模假设，上机前仍须与实物核对。

## 本地使用

在项目目录执行（Windows 可用实际 Python 路径替换 `python`）：

```console
python -m rtcp_portable selfcheck
python -m unittest discover -s tests -v
python -m rtcp_portable validate profiles/simulation.json
python -m rtcp_portable simulate profiles/simulation.json examples/arc.json --output my-report.json
```

`my-report.json` 必须不存在，避免覆盖原文件。输出只有 JSON，无可执行 G-code。
`profiles/simulation.json` 的中心、限位、方向都是**合成测试参数，不可当作机器标定**。
`profiles/machine.template.json` 的未知项为 null，校验应当失败；逐机完成标定后才能填入。
命令行拒绝缺失字段、重复字段、NaN/Infinity、旧 A/C 字段以及未实现的 E/F 字段。
上述限制针对 v1 几何格式。v2 显式事件格式支持相对 E 增量和分类型的进给，
不会把旧混合轴补偿 F 当作 TCP mm/min。示例见 `examples/timed-job.json`。

```console
python -m rtcp_portable audit-gcode path/to/backup.gcode --output backup-audit.json
python -m rtcp_portable inspect-ghx path/to/slicer.ghx --output ghx-audit.json
python -m rtcp_portable plan-timing profiles/simulation.json profiles/timing.simulation.json examples/timed-job.json --offset 5 -3 0 --output timing-report.json
```

`timing.simulation.json` 所有速度/加速度同样都是合成值，不是机器安全参数。
详细接线位置、审查结果与仍需核对的流对齐见 `docs/open5x-adaptation.md`。

生成验证报告及可移植安装包：

```console
python scripts/verify.py --output new-test-report.json
python scripts/build_verify.py --output new-install-report.json
```

第二条需要本机已有 pip/setuptools/venv，关闭包索引访问；
它只在项目 `.artifacts/` 中建干净虚拟环境，不修改 Klipper 环境。
同版本 wheel 若已在 `dist/` 中存在则拒绝覆盖。
复测已有 wheel 可使用 `build_verify.py --wheel dist/对应文件.whl --output 新报告.json`。
v0.2 最终测试/迁移证据分别是 `reports/v0.2.0-regression.json`、
`reports/v0.2.0-portability.json`。旧 v0.1 wheel/ZIP/报告保留，不覆盖。

## 文件布局

| 文件/目录 | 用途 |
|---|---|
| `rtcp_portable/geometry.py` | 正逆变换，不依赖 Klipper |
| `rtcp_portable/path.py` | 几何细分及保守的物理轴行程检查 |
| `rtcp_portable/session.py` | 离线参考/启停状态模型 |
| `rtcp_portable/timing.py` | XYZUV/E/CoreXY 共时间轴的离线定时参考 |
| `rtcp_portable/gcode.py` | 旧 G-code 审查，不自动导入 |
| `klipper/klippy/extras/rtcp.py` | Klipper v1 RTCP 适配层，默认关闭 |
| `klipper/printer_data/config/rtcp.cfg` | 每机中心、方向、限位和细分参数模板 |
| `control-console-overlay/` | 五轴操作台后端接口与右下角 RTCP ON/OFF 开关 |
| `bridges/ghpython_capture.py` | 新建 GhPython 组件中采集 pre-IK 数据，无文件/网络输出 |
| `profiles/` | 每机配置与合成示例 |
| `tests/` | 数学、限位、生命周期、CLI 回归 |
| `docs/integration.md` | 后续接入与打印生命周期边界 |
| `docs/klipper-v1.md` | 当前 Klipper RTCP 坐标语义、命令与限制 |
| `docs/migration.md` | 迁移及标定清单 |
| `reports/` | 本次本地验证证据 |
| `dist/` | 安装 wheel，构建后生成 |

已有审计报告反映的是**之前下载的快照**，不是当前实时配置。
另一进程可能已修改树莓派，正式接入前必须重新进行版本/接口确认。
