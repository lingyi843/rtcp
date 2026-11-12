# 04｜Grasshopper 切片流程

## 上游工作流概述

Open5x 的五轴 G-code 生成逻辑放在 `Grasshopper_Definition/`。Grasshopper 是 Rhino 3D 内的可视化脚本环境；上游将它用于几何处理、路径生成和旋转龙门架的运动仿真。

这意味着五轴切片不是只把普通三轴 G-code 加上两个角度字段。每个路径点都需要同时满足：曲面位置、法向/姿态、喷嘴朝向、平台旋转、运动范围和无碰撞条件。

## 已确认的软件依赖

| 依赖 | 用途 | 备注 |
|---|---|---|
| Rhino 3D | 宿主 CAD 软件 | 上游说明提及 90 天完整试用；许可证与版本须自行确认 |
| Grasshopper | Rhino 内的图形化脚本环境 | 加载 `.gh` 定义文件 |
| Heteroptera | 求取 3D 几何质心 | 上游 README 指定的插件 |
| .NET LINQ | 对列表取最大值/最小值等 | 脚本环境需支持相应 .NET API |
| 旋转龙门架 `.3dm` 模型 | 仿真节点的机械场景 | 用于观察姿态与可能的干涉 |

## 目录中的关键文件

| 文件 | 角色 |
|---|---|
| `Open5x_Gcode_0503.gh` | 五轴 G-code 定义文件之一 |
| `open5x_supportless_slicing_ver2.gh` | 无支撑/保形切片定义文件之一 |
| `2022_03_22_open5x_supportless_surface_Lite.gh` | 轻量化无支撑曲面版本 |
| `Prusa_5axis_profile_v2.3dm` | Prusa 五轴机构的仿真/配置模型 |
| `Supportless_sample_2.3dm` | 用于无支撑样例的 Rhino 模型 |

上游 README 表示脚本仍在持续改进，长期目标是迁离 Rhino，转向免费且开源的工作流。因此，这些 `.gh` 文件应视为特定版本的研究原型，而非已经冻结的通用切片器。

## 建议操作顺序

1. 在隔离的 Rhino 项目中安装/确认所需组件版本。
2. 打开对应 `.3dm` 机构模型与待打印几何；先检查单位、原点和旋转中心。
3. 加载一个 `.gh` 文件，定位输入几何、机构仿真、路径输出和 G-code 写出节点。
4. 不连接机器，先生成短路径并在仿真中逐段观察喷嘴、平台和工件的间隙。
5. 对 G-code 做静态检查：轴名、单位、绝对/相对模式、角度范围、进给、温度命令与注释。
6. 冷态、断料、低速执行最小空跑段；核对实际姿态与仿真一致后，再扩大路径范围。

## 与当前 Klipper/RTCP 系统的接口边界

Grasshopper 输出中的旋转轴字母、旋转方向、零位、旋转中心和坐标变换都必须翻译成目标机器的运动学。对当前工作区而言，不能假定上游 G-code 的 U/V 含义等于本机的 U/V 或 A/C，也不能假定其平台姿态由相同的 RTCP 算法解释。

最稳妥的中间产物是“路径点表 + 姿态 + 预期喷嘴位置 + 预期平台角 + 时间/进给”，先离线验证其运动学，再由目标控制栈生成或转换为可执行 G-code。

## 原始资料

- `reference/Open5x-upstream/Grasshopper_Definition/README.md`
- `reference/Open5x-upstream/Grasshopper_Definition/*.gh`
- `reference/Open5x-upstream/Grasshopper_Definition/*.3dm`
