# Open5x 资料汉化与整理

## Goal
以用户指定的本地 Open5x 原始资料为唯一主源，完成**第一期局部汉化整理**：建立中文索引、项目/机械/控制/切片导读和术语安全提示。暂不进行全部文件、配置、宏、CAD、PDF 或 Grasshopper 定义的逐项/逐行汉化；后续范围严格按用户指令推进。

## Current Phase
Phase 3 - 等待用户指定下一批汉化范围。

## Phases

### Phase 1 - 上游资料盘点
**Status:** complete

- 确认官方仓库、论文及项目说明页。
- 获取仓库目录与文字类资料清单，区分可直接汉化内容与二进制设计文件。

### Phase 2 - 中文资料结构与术语
**Status:** complete

- 创建中文索引、项目概览、硬件资料说明、软件工作流和术语表。
- 标注原始资料位置和版本/提交信息。

### Phase 3 - 技术核对与交付
**Status:** complete

- 已按用户指定，完整汉化 `3D_Model/Prusa i3/Materials_and_supplier.md`。
- 每次保持原文件不动，将中文整理件单独写入本工作区。

## Next Step
等待用户指定下一批需要汉化或优先整理的文件；不继续自动扩展汉化范围。

## Decisions Made

| Decision | Reason |
|---|---|
| 以用户指定的本地 `Open5x-main-origin` 目录为主源 | 用户明确该目录是从 GitHub 下载的原始文件；不修改其中任何文件。 |
| 将可执行机器配置视为参考而非可直接部署的配置 | 当前工作区的 Klipper/RTCP 设备与 Open5x 的 Prusa/Duet 体系不同。 |
| 第一阶段止于导读级局部汉化 | 用户明确要求暂不进行完整汉化，后续逐批吸收指令。 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| None | 0 | — |
| `git sparse-checkout add` rejected `--no-cone` | 1 | The repository is already in non-cone mode; retry `add` without that unsupported option, then re-run source and document checks. |
| Markdown link-check command had an incomplete second `-notmatch` operand | 1 | The validation script did not execute; use an explicit second `$target` operand, then rerun link and source checks. |
| Link-check report used a PowerShell calculated-property hashtable that this shell parsed incorrectly | 1 | Replace the formatted object projection with simple per-file output; preserve the already-correct link/source validation logic. |
| In-app browser tool blocked inspection of local `file:///` HTML | 1 | The generated HTML has already been syntax/row-count validated locally; use the user's browser-opened HTML page as the rendered preview rather than retrying blocked local-file navigation. |
