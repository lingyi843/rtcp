# P1S 一体式热端：参数与 CAD 资料

整理日期：2026-09-20

## 1. 型号判断

根据实物照片（黑色散热器标注 `0.4mm`、2510 风扇、金色触点转接板），与市售 **LANKEGU / 同结构第三方 P1P、P1S 一体式热端总成**外观高度一致。

它不是拓竹官方标准版的完全相同结构，更像是将热端、加热器、热敏电阻、2510 风扇和触点接口集成在一起的第三方替换件。

## 2. 能够确认的参数

| 项目 | 参数/说明 | 确定程度 |
|---|---|---|
| 适用机型 | Bambu Lab P1P / P1S | 商品信息可确认 |
| 喷嘴直径 | 0.4 mm | 实物标注可确认 |
| 耗材直径 | 1.75 mm | P1 系列系统规格 |
| 风扇规格 | 2510，外形尺寸 25 × 25 × 10 mm | 型号含义可确认 |
| 加热器 | 陶瓷加热器，市售页面标称 24 V / 48 W | 第三方商品信息 |
| 加热器理论阻值 | 约 12 Ω，按 R=24²/48 计算 | 通电前建议万用表复核 |
| 喷嘴材质 | 相同外形商品多标称硬化钢 | 仅凭照片不能最终确认 |
| 加热块 | 商品信息标称铝合金加热块 | 第三方商品信息 |
| 温度传感器 | NTC 热敏电阻，已与热端线路集成 | R25 和 B 值未公开 |
| 触点小板 | 加热电源和温度信号转接板 | 不是 CAN/UART 通信主板 |
| 官方 P1 热端长度参考 | 47.3 mm | 拓竹官方商城参数 |
| 官方 P1 热端温度参考 | 官方当前页面标称最高 320 ℃ | 不等于第三方件也通过相同认证 |

## 3. 暂时不能从公开资料确认的项目

- 2510 风扇的准确电压、电流、转速和线序。P1 兼容风扇常见为 5 V，但不应只根据外形直接供电。
- NTC 热敏电阻的 R25、B 值和温度曲线。
- 转接板每一个金色触点的引脚定义。
- 第三方喷嘴的安全长期工作温度。未拿到厂家曲线前，不建议把官方热端的 320 ℃指标直接套用到这个第三方件上。

## 4. CAD 文件

### A. 最接近实物的缩放准确模型

MakerWorld 模型：**X1/P1 Hotend CAD Model (both stock & Revo)**

- 模型页：https://makerworld.com/en/models/1074117-x1-p1-hotend-cad-model-both-stock-revo
- STEP 文件名：`BBL_X1-Hotend_V1.step`
- 文件大小：15,116,868 bytes
- 许可：BY
- 注意：MakerWorld 要求登录后才返回 STEP 下载地址。该模型包含原装 X1/P1 热端和 Panda Revo 组件，适合做安装空间、支架和干涉校核。

### B. 已下载的开源兼容参考 CAD

`Panda_Revo_mockup_兼容安装参考.STEP`

来源：BIGTREETECH Panda Revo GitHub 仓库。这个文件可用来参考 P1/X1 工具头的安装位置，但不是照片中 LANKEGU/第三方一体式热端的原厂 CAD，不可直接当成精确外形。

### C. 其他参考模型

- GrabCAD：https://grabcad.com/library/complete-hotend-assembly-bambu-lab-x1c-steel-nozzle-1
- BIGTREETECH Panda Revo：https://github.com/bigtreetech/Panda_Revo/blob/master/3D/Panda%20Revo%20mockup.STEP

## 5. 安装和原厂资料

- 拓竹 P1 系列热端更换指南：https://wiki.bambulab.com/en/p1/maintenance/complete-hot-end-assembly
- 拓竹 P1 系列热端产品页：https://eu.store.bambulab.com/products/bambu-hotend-p1-series

## 6. 通电前建议检查

1. 万用表测加热回路：如确实是 24 V / 48 W，冷态阻值应大致接近 12 Ω，不应接近 0 Ω或完全开路。
2. 测温度传感器回路：常温应为稳定的高阻值，用手指加热时阻值应平稳变化。
3. 不要根据线色猜测触点定义，先做通断测量。
4. 如果不是直接接入 P1S 原机，需要单独确认风扇电压、NTC 曲线和接口引脚后再设计转接板。

