# 可移植性与逐机标定

## 换树莓派，不等于换机器

代码无 IP、用户名、凭据和绝对安装路径；运行只依赖 Python 标准库。
`py3-none-any` wheel 无平台原生扩展，目标解释器需 Python 3.10+。
本次干净安装只在 Windows/Python 3.12 验证；ARM/Linux/其他 Python 版本仍需实测。

将项目文件夹或分发包复制到新主机的独立开发目录后，可仅在新虚拟环境离线运行：

```console
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --no-deps dist/portable_rtcp_offline-0.2.0-py3-none-any.whl
.venv/bin/python -m rtcp_portable selfcheck
.venv/bin/python -m rtcp_portable validate profiles/simulation.json
.venv/bin/python -m rtcp_portable simulate profiles/simulation.json examples/arc.json --output report.json
```

这些是离线测试命令，不是 Klipper 安装步骤，不要安装到现有 Klipper 虚拟环境中。
若新主机没有 venv/pip，先单独准备 Python 开发环境；本包不自动修改系统软件。
也可在项目目录直接 `python3 -m rtcp_portable selfcheck`，无需安装。

wheel 只含库与 CLI，配置/文档/测试随项目文件夹或源码分发包提供，不写入 Klipper 目录。
GHX 二进制簇解包辅助脚本仅审查时依赖本地 GH_IO.dll；
正常 RTCP 算法、G-code 审查、定时验证不依赖 Rhino/GH_IO，也不需要把该 DLL 搬到树莓派。
新建 `OfflineSession` 总是 OFF、XYZ/UV 未建立参考；不迁移 ACTIVE/homed/队列状态。
同一物理机器也要重新建立当次参考并验证工作配准，不能恢复上次进程内状态。

## 换机器：换配置，不改矩阵代码

从 `profiles/machine.template.json` 复制出新机器专用文件，保持稳定 machine_id。
以下项目都必须逐机确认；不可复制合成示例中的中心或限位：

| 配置项 | 含义/确认方式 |
|---|---|
| `pivot_mm` | 实际共同轴心 Cx/Cy/Cz，必须与喷嘴点机器坐标同一基准 |
| `u.sign/v.sign` | 平台实际正转方向与右手角度的对应 ±1 |
| `u.zero_deg/v.zero_deg` | 与建模零姿态对应的控制器角度；不是未知角度的代用品 |
| `u/v.limits_deg` | 包含机械干涉、线缆等约束的保守允许范围 |
| `xyz_limits_mm` | 实际有效喷嘴机器行程，不能由模型边界代替 |
| `u/v.gear_ratio` | 与现场驱动配置一致；本机 U 已确认 260:18，V 待核实 |
| `chord_tolerance_mm` | 几何离散误差目标，不代表整机精度 |

“轴心设计在床面”允许第一轮令相对高度 d.z=0，
但需要独立测量机器 Cz，并评估 U/V 轴线不相交与盘面跳动的残余误差。
不在本版偷偷加入第二个偏心常数；超出共点近似时应升级几何模型及标定协议。

当前机器参数中不包含驱动引脚、电机方向或步距；本包不会覆盖 `printer.cfg`。
未来适配层要比对现场这些参数，不一致即阻止启用，而不是静默修改它们。

## 作业配准不是机器标定

机器中心/符号属于逐机参数；视觉 dx/dy/dz 属于本次工件。
本版在 U/V 零姿态采集视觉，配准与当前参考代数绑定；重新设零后失效。
`examples/arc.json` 中的 offset 是离线示例，不是可自动用于下一次打印的作业记录。
如果工件还存在转角或倾斜，只有 dx/dy 不够；需扩展为完整刚体配准再验证。

## 联调/部署前需要的最小资料

1. 当时机器正在使用的 Klipper 版本及 `corexy_uv.py`、toolhead、宏配置。
2. 实测 Cx/Cy/Cz、U/V 正方向、安全角度范围，V 参考建立方式和真实减速比。
3. 视觉测量时 U/V 姿态、dx/dy 单位和轴向；是否存在工件 yaw/高度误差。
4. 一段 Rhino/Open5x 原始导出样本及预期几何姿态。

资料缺失不妨碍继续离线算法开发，但会阻止真实运动部署。
