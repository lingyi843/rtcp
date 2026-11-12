# 朱雀打印机热端与挤出机文件核查

## Goal
从采购清单、三份 STEP 文件和参考图片中，确认朱雀打印机热端型号，识别三份挤出机模型各自内容，并判断现有文件是否齐全、还缺什么。

## Phases

### Phase 1: 来源与工具盘点
- [x] 核对附件存在性、文件大小与可用解析工具
- [x] 记录 Excel 工作表和 STEP 基础元数据
**Status:** complete

### Phase 2: 采购清单核查
- [x] 检索热端、喷嘴、挤出机、喉管、加热棒、热敏、风扇等相关条目
- [x] 检查超链接、图片、批注或隐藏内容是否补充型号信息
**Status:** complete

### Phase 3: STEP 几何与装配核查
- [x] 提取每份 STEP 的产品名、装配关系、实体数量与包围盒
- [x] 生成或查看模型预览，判定各自对应部件
**Status:** complete

### Phase 4: 对照与结论
- [x] 对照采购清单、模型和参考照片
- [x] 明确已确认项、推断项和缺失项
**Status:** complete

## Next Step
已完成；向用户说明热端型号、三件作用和文件缺失边界。

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Python 向 Windows GBK 控制台输出 STEP 中的 Latin-1 字符时触发 `UnicodeEncodeError` | 1 | 将脚本 stdout 显式设为 UTF-8 后重试 |

## Decisions Made
| Decision | Rationale |
|---|---|
| 只读检查，不修改附件 | 用户询问识别与缺失情况，没有授权修改源文件 |
| 为本任务建立独立计划目录 | 工作区已有多个其他任务计划，需避免混淆 |
