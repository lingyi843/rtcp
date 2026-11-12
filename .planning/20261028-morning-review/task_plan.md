# 晨间 Review 手册

## Goal
制作可编辑的中文 Word 手册和每日复制模板，支持每天早上回顾最近 3–7 天的五轴曲面打印项目进展。

## Next Step
交付已验证的 Word 手册和每日复制模板。

## Phases
### Phase 1 - 确定使用场景与资料边界
**Status:** complete
- 每天 10–15 分钟，重点是状态变化、证据、阻塞和今日交付。
- 已读取项目基线；2026-10-16 历史记录不自动认定为当前状态。

### Phase 2 - 生成手册和每日模板
**Status:** complete
- 计划 5 页：操作流程、每日单页、跨日台账、项目议题、示例与收口规则；日常只填第 2 页。
- 不修改已有任务表或项目台账，不连接机器，不创建提醒。

### Phase 3 - 渲染、逐页检查与交付
**Status:** complete
- 先尝试标准 renderer；如运行时缺少 LibreOffice，使用独立隐藏 Word 实例导出 PDF 并逐页渲染检查。

## Errors Encountered
| Error | Resolution |
|---|---|
| bundled Python 无 fitz | 已确认 pypdfium2 可用，用于 PDF 页面渲染。 |
| 读取任务表时工作表 max_row 为 None | 使用 islice 限定迭代行数，成功读取；原表未修改。 |
| 标准 render_docx.py 找不到 soffice.exe | 不调用系统 LibreOffice；改用独立隐藏 Word COM 导出 PDF，再用 bundled pypdfium2 逐页检查。 |
| 初版 Word 分页超出 5 页 | 改用固定且足够的行距、调整表格留白，最终保持 5 页；未缩小正文字号。 |
| QA 预期表格数量误写 10 | 复核含两处提示框的真实表格结构，共 11 张，修正检查后通过。 |
