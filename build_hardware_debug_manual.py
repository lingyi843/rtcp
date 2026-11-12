from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT = Path(r"C:\Users\zhangyi\Documents\五轴曲面打印\文档\硬件电子部_机器基础打印调试与技术文档管理手册_初稿.docx")

# compact_reference_guide preset + named CJK/manual-title overrides
PAGE_W = 12240  # Letter portrait, DXA
PAGE_H = 15840
CONTENT_W = 9360
TABLE_INDENT = 120
FONT_LATIN = "Calibri"
FONT_CJK = "Microsoft YaHei"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
NAVY = "17365D"
INK = "222222"
MUTED = "667085"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
PALE_BLUE = "F4F7FB"
GREEN = "E2F0D9"
GOLD = "FFF2CC"
RED = "FCE4D6"
WHITE = "FFFFFF"
BORDER = "B7C9DC"


def set_run_font(run, size=11, bold=None, color=INK, italic=None, name=FONT_LATIN):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT_CJK)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        tag = qn(f"w:{edge}")
        node = tc_mar.find(tag)
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=BORDER, size=6):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        border = borders.find(tag)
        if border is None:
            border = OxmlElement(f"w:{edge}")
            borders.append(border)
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(size))
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def set_table_geometry(table, widths_dxa, indent_dxa=TABLE_INDENT):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            if idx >= len(widths_dxa):
                continue
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths_dxa[idx] / 1440)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def style_cell_paragraph(p, size=9.5, bold=False, color=INK, align=WD_ALIGN_PARAGRAPH.LEFT):
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    for run in p.runs:
        set_run_font(run, size=size, bold=bold, color=color)


def add_table(doc, headers, rows, widths, header_fill=LIGHT_BLUE, font_size=9.3,
              alignments=None, row_fills=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    set_cant_split(hdr)
    for i, value in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = str(value)
        set_cell_shading(cell, header_fill)
        style_cell_paragraph(cell.paragraphs[0], size=9.2, bold=True, color=NAVY,
                             align=WD_ALIGN_PARAGRAPH.CENTER)
    for r_idx, row_values in enumerate(rows):
        row = table.add_row()
        set_cant_split(row)
        fill = None if row_fills is None else row_fills[r_idx]
        for i, value in enumerate(row_values):
            cell = row.cells[i]
            cell.text = str(value)
            if fill:
                set_cell_shading(cell, fill)
            align = WD_ALIGN_PARAGRAPH.LEFT
            if alignments and i < len(alignments):
                align = alignments[i]
            style_cell_paragraph(cell.paragraphs[0], size=font_size, align=align)
    set_table_geometry(table, widths)
    set_table_borders(table)
    after = doc.add_paragraph()
    after.paragraph_format.space_before = Pt(0)
    after.paragraph_format.space_after = Pt(2)
    return table


def set_keep_with_next(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    keep = OxmlElement("w:keepNext")
    p_pr.append(keep)
    keep_lines = OxmlElement("w:keepLines")
    p_pr.append(keep_lines)


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    set_keep_with_next(p)
    return p


def add_body(doc, text, bold_label=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.25
    if bold_label and text.startswith(bold_label):
        r1 = p.add_run(bold_label)
        set_run_font(r1, bold=True)
        r2 = p.add_run(text[len(bold_label):])
        set_run_font(r2)
    else:
        r = p.add_run(text)
        set_run_font(r)
    return p


def add_callout(doc, label, text, fill=PALE_BLUE, accent=BLUE):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.right_indent = Inches(0.10)
    p.paragraph_format.line_spacing = 1.18
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)
    borders = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), accent)
    borders.append(left)
    p_pr.append(borders)
    r1 = p.add_run(label + "  ")
    set_run_font(r1, size=10.5, bold=True, color=accent)
    r2 = p.add_run(text)
    set_run_font(r2, size=10.5, color=INK)
    return p


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    set_run_font(run, size=9, color=MUTED)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)
    run2 = paragraph.add_run(" 页")
    set_run_font(run2, size=9, color=MUTED)


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_LATIN
    normal._element.rPr.rFonts.set(qn("w:ascii"), FONT_LATIN)
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), FONT_LATIN)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    heading_tokens = {
        1: (16, BLUE, 18, 10),
        2: (13, BLUE, 14, 7),
        3: (12, DARK_BLUE, 10, 5),
    }
    for level, (size, color, before, after) in heading_tokens.items():
        style = doc.styles[f"Heading {level}"]
        style.font.name = FONT_LATIN
        style._element.rPr.rFonts.set(qn("w:ascii"), FONT_LATIN)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), FONT_LATIN)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    header = section.header
    hp = header.paragraphs[0]
    hp.paragraph_format.space_after = Pt(0)
    hp.paragraph_format.tab_stops.add_tab_stop(Inches(6.5))
    r1 = hp.add_run("硬件电子部｜机器基础打印调试手册")
    set_run_font(r1, size=8.5, bold=True, color=MUTED)
    r2 = hp.add_run("\t初稿 · 2026-08-21")
    set_run_font(r2, size=8.5, color=MUTED)

    footer = section.footer
    fp = footer.paragraphs[0]
    add_page_number(fp)


def add_cover(doc):
    for _ in range(4):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(12)

    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker.paragraph_format.space_after = Pt(16)
    r = kicker.add_run("硬件电子部 · 多机调试标准化")
    set_run_font(r, size=11, bold=True, color=BLUE)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(12)
    r = title.add_run("机器基础打印调试与\n技术文档管理手册")
    set_run_font(r, size=28, bold=True, color=NAVY)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(34)
    r = subtitle.add_run("适用于 CoreXY / 多轴打印设备的基础功能调通阶段")
    set_run_font(r, size=13.5, color=MUTED)

    add_callout(
        doc,
        "当前优先级",
        "先让每台机器安全运动并完成完整打印；视觉、激光定位和 RTCP 等高级功能在基础打印版本冻结后再独立开发。",
        fill=LIGHT_BLUE,
        accent=BLUE,
    )

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Pt(24)
    meta.paragraph_format.space_after = Pt(4)
    r = meta.add_run("版本：V0.1（讨论初稿）")
    set_run_font(r, size=10.5, bold=True, color=DARK_BLUE)
    meta2 = doc.add_paragraph()
    meta2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta2.paragraph_format.space_after = Pt(4)
    r = meta2.add_run("日期：2026年8月21日")
    set_run_font(r, size=10.5, color=MUTED)
    meta3 = doc.add_paragraph()
    meta3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta3.add_run("状态：供内部评审、补充与修改")
    set_run_font(r, size=10.5, color=MUTED)

    doc.add_page_break()


def build_document():
    doc = Document()
    configure_document(doc)
    add_cover(doc)

    add_heading(doc, "1. 文档目的与适用范围", 1)
    add_body(doc, "本手册用于统一硬件电子部多台打印设备的调试、记录、验收和交接方式。现阶段的唯一主目标，是让在调机器安全、稳定地完成基础打印，并形成可以恢复、复制和持续修改的技术基线。")
    add_callout(doc, "范围边界", "本阶段聚焦供电、主板、通信、XYZ运动、限位归零、温控、风扇、挤出、基础标定和完整打印。视觉、激光定位、RTCP及复杂五轴联动统一进入后续研发池。", fill=GOLD, accent="7A5A00")

    add_heading(doc, "2. 管理原则", 1)
    principles = [
        ("一机一档", "以机器编号为主线建立唯一档案，不能只保存在个人电脑、聊天记录或口头经验中。"),
        ("一问题一记录", "所有阻断性或重复出现的问题必须形成问题单，记录现象、证据、根因、解决方案和验证结果。"),
        ("一版本一备份", "每次达到可用里程碑后冻结配置、固件、源码版本和恢复说明，后续研发不得覆盖基础打印基线。"),
    ]
    for label, text in principles:
        add_callout(doc, label, text)

    add_heading(doc, "3. 基础打印调试阶段门", 1)
    phase_rows = [
        ("M0", "机器建档", "完成机器编号、主板、树莓派、IP、接线和负责人登记", "资料完整，可以唯一识别机器"),
        ("M1", "通信连接", "检查树莓派、Moonraker、Klipper和MCU通信", "Mainsail稳定显示 Ready"),
        ("M2", "基础运动", "核对X/Y/Z/E方向、距离、使能和安全速度", "无撞机；方向和运动距离正确"),
        ("M3", "归零限位", "验证限位类型、触发逻辑、归零方向和重复性", "连续归零3次位置稳定"),
        ("M4", "温控风扇", "验证热端、热床、热敏、加热保护和风扇", "稳定控温，无异常升温"),
        ("M5", "挤出系统", "验证进料、退料、挤出方向和挤出量", "连续挤出正常，无明显打滑或堵料"),
        ("M6", "基础标定", "标定运动距离、挤出量、PID和首层", "尺寸和首层满足基础打印要求"),
        ("M7", "打印验收", "打印统一测试件并记录全过程", "完整打印，无中断或安全异常"),
        ("M8", "版本冻结", "备份配置、固件、源码、日志和恢复步骤", "形成可恢复、可复制的基线包"),
    ]
    add_table(
        doc,
        ["阶段", "名称", "主要任务", "通过标准"],
        phase_rows,
        [720, 1320, 3900, 3420],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        row_fills=[None, LIGHT_GRAY, None, LIGHT_GRAY, None, LIGHT_GRAY, None, LIGHT_GRAY, None],
    )

    add_heading(doc, "4. 多机调试档案结构", 1)
    add_body(doc, "技术资料以机器编号为第一层目录。人员是记录的责任人，但机器档案才是最终交付物。公共资料和高级研发内容分别管理，避免不同机器之间误用配置。")
    tree = (
        "机器调试/\n"
        "├─ 00_公共资料/\n"
        "│  ├─ 主板引脚与接线规范\n"
        "│  ├─ 公共安全规范\n"
        "│  └─ 标准测试G-code\n"
        "├─ MACHINE-01/\n"
        "│  ├─ 01_机器信息\n"
        "│  ├─ 02_接线与引脚\n"
        "│  ├─ 03_调试进度\n"
        "│  ├─ 04_问题记录\n"
        "│  ├─ 05_测试与验收\n"
        "│  ├─ config/  firmware/  logs/  photos/\n"
        "│  └─ release/\n"
        "├─ MACHINE-02/\n"
        "└─ 90_后续研发池/\n"
        "   ├─ 视觉定位/  激光定位/\n"
        "   └─ RTCP与五轴联动/"
    )
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.line_spacing = 1.15
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), LIGHT_GRAY)
    p_pr.append(shd)
    r = p.add_run(tree)
    set_run_font(r, size=9.5, color=INK, name="Consolas")

    add_heading(doc, "5. 单机状态卡模板", 1)
    add_table(
        doc,
        ["字段", "填写内容", "字段", "填写内容"],
        [
            ("机器编号", "MACHINE-____", "当前阶段", "M____"),
            ("主负责人", "", "参与人员", ""),
            ("主板型号", "", "MCU序列号", ""),
            ("树莓派IP", "", "Klipper版本", ""),
            ("活动配置", "", "最后更新时间", ""),
            ("当前阻断", "", "下一步动作", ""),
        ],
        [1500, 3180, 1500, 3180],
        font_size=9.5,
    )

    add_heading(doc, "6. 功能进度看板模板", 1)
    add_table(
        doc,
        ["功能", "状态", "负责人", "证据/备注"],
        [
            ("Klipper与MCU连接", "未开始 / 调试中 / 通过", "", ""),
            ("X/Y/Z基础运动", "", "", ""),
            ("限位与归零", "", "", ""),
            ("热端与热床", "", "", ""),
            ("风扇", "", "", ""),
            ("挤出与进退料", "", "", ""),
            ("首层与基础标定", "", "", ""),
            ("完整打印", "", "", ""),
        ],
        [2400, 2100, 1500, 3360],
        font_size=9.2,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
    )

    add_heading(doc, "7. 每日调试记录模板", 1)
    add_body(doc, "每日记录以“操作前状态—本次操作—结果证据—最终状态—下一步”为固定顺序。重要参数必须写明修改前后值，禁止只写“已修好”。")
    add_table(
        doc,
        ["项目", "填写内容"],
        [
            ("日期/人员", "日期：____________    调试人员：________________"),
            ("机器/阶段", "机器编号：____________    当前阶段：____________"),
            ("操作前状态", "Klipper状态、坐标、温度、已知报警及机械状态"),
            ("本次目标", "本次只解决什么问题或验证什么功能"),
            ("执行操作", "命令、接线、参数或文件修改；注明修改前后值"),
            ("结果与证据", "日志路径、配置差异、照片、视频、测量数据"),
            ("最终状态", "是否Ready、是否断电、加热目标、各轴使能状态"),
            ("下一步", "下一次调试的单一优先动作"),
        ],
        [1800, 7560],
        font_size=9.5,
    )

    add_heading(doc, "8. 关键问题单模板", 1)
    issue_rows = [
        ("问题编号", "ISSUE-[模块]-[三位序号]", "严重程度", "阻断 / 高 / 中 / 低"),
        ("发现人/时间", "", "当前状态", "待分析 / 调试中 / 已解决 / 规避"),
        ("问题现象", "准确描述报错、异常运动或测量结果", "复现条件", "配置、版本、命令和硬件状态"),
        ("证据", "日志、串口数据、配置差异、照片或测量", "影响范围", "涉及机器、功能和安全风险"),
        ("排查过程", "按顺序记录每次检查及排除的假设", "根本原因", "不能只写“修改参数后恢复”"),
        ("解决与验证", "解决方案、测试次数、测量结果", "回滚方法", "失败时如何恢复原状态"),
    ]
    add_table(doc, ["字段", "填写内容", "字段", "填写内容"], issue_rows,
              [1500, 3180, 1500, 3180], font_size=9.1)
    add_callout(doc, "强制要求", "阻断打印、安全相关、重复出现、跨机器复现的问题必须建立独立问题单，并在中央问题台账中登记。", fill=RED, accent="9B1C1C")

    add_heading(doc, "9. 中央问题汇总台账", 1)
    add_table(
        doc,
        ["问题编号", "机器/模块", "问题摘要", "负责人", "严重度", "状态"],
        [
            ("ISSUE-MCU-001", "MACHINE-01 / 主板", "示例：MCU启动后无法连接", "", "高", "已定位"),
            ("", "", "", "", "", ""),
            ("", "", "", "", "", ""),
        ],
        [1650, 1650, 3000, 1200, 900, 960],
        font_size=8.8,
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
    )

    add_heading(doc, "10. 基础打印验收清单", 1)
    checklist = [
        ("□", "冷启动后Klipper可稳定进入Ready", "", ""),
        ("□", "X/Y/Z方向及运动距离正确", "", ""),
        ("□", "限位和归零连续测试至少3次正常", "", ""),
        ("□", "热端、热床及热敏工作正常，温控稳定", "", ""),
        ("□", "风扇启停及方向正确", "", ""),
        ("□", "挤出机可正常进料、退料和连续挤出", "", ""),
        ("□", "急停、断电及故障恢复方法已验证", "", ""),
        ("□", "完成统一标准测试件，打印过程无异常中断", "", ""),
        ("□", "已保存配置、固件、源码版本和日志证据", "", ""),
        ("□", "已完成从零恢复说明和负责人签字", "", ""),
    ]
    add_table(
        doc,
        ["确认", "验收项目", "结果/数据", "验收人/日期"],
        checklist,
        [720, 4560, 2280, 1800],
        font_size=9.4,
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER],
    )
    add_callout(doc, "判定规则", "全部项目通过后，机器才可以标记为“基础打印完成（BASE_PRINT）”。存在未解释报警、安全风险或无法回滚的临时修改时，不得冻结版本。", fill=GREEN, accent="37692A")

    add_heading(doc, "11. 基础打印版本冻结与恢复包", 1)
    release_rows = [
        ("配置", "活动printer.cfg及全部include文件", "必须标注实际启动入口"),
        ("主板固件", "klipper.bin及编译.config", "记录MCU型号、引导区和通信方式"),
        ("主机源码", "Klipper提交号、分支和本地修改", "dirty状态必须保留diff"),
        ("硬件资料", "接线图、主板照片、驱动器与跳线", "照片需能辨认接口和线序"),
        ("标定结果", "PID、rotation_distance、限位和平台参数", "记录日期、方法和测量值"),
        ("验收证据", "测试件照片、日志和验收表", "可以证明版本完成过实际打印"),
        ("恢复说明", "从空白系统恢复到Ready及打印的步骤", "由非原调试人员复核一次"),
    ]
    add_table(doc, ["类别", "必须保存", "要求"], release_rows,
              [1560, 3900, 3900], font_size=9.2)
    add_body(doc, "建议版本名称：MACHINE-01_BASE_PRINT_YYYYMMDD_V01。每台机器的基础打印版本只允许通过新版本迭代，不允许被视觉、激光或RTCP试验直接覆盖。")

    add_heading(doc, "12. 高级功能后续研发原则", 1)
    add_body(doc, "视觉、激光定位、RTCP和五轴联动应从已经冻结的BASE_PRINT版本复制独立开发版本。高级功能开发失败时，必须能够在短时间内恢复到基础打印状态。")
    add_table(
        doc,
        ["版本线", "用途", "允许内容", "保护规则"],
        [
            ("BASE_PRINT", "日常基础打印与故障回退", "XYZ/E、归零、温控、挤出、基础宏", "只做已验证修复"),
            ("VISION_DEV", "视觉识别与对准", "相机、标定、识别服务", "不得覆盖基础配置"),
            ("LASER_DEV", "激光定位", "激光器、传感器、坐标转换", "独立安全联锁"),
            ("RTCP_DEV", "五轴和RTCP", "A/C轴、运动学、坐标补偿", "空载验证后方可联机"),
        ],
        [1800, 2580, 3000, 1980],
        font_size=9.1,
    )

    doc.add_page_break()
    add_heading(doc, "13. 角色与评审机制", 1)
    role_rows = [
        ("单机负责人", "维护机器状态、协调调试顺序、确保记录完整"),
        ("执行调试人员", "按流程操作，保存修改前后状态和测试证据"),
        ("模块负责人", "处理主板、运动、温控、挤出等专业问题并复核根因"),
        ("文档汇总人", "维护中央台账、版本索引和跨机器共性问题"),
        ("验收人", "不直接依赖调试人员口头结论，按验收清单复测"),
    ]
    add_table(doc, ["角色", "主要责任"], role_rows, [2100, 7260], font_size=9.6)

    add_heading(doc, "14. 建议执行节奏", 1)
    cadence = [
        ("每天开始前", "确认机器编号、当前阶段、唯一目标和安全状态。"),
        ("每次修改后", "记录修改前后值、配置差异、测试结果和回滚方法。"),
        ("每天结束前", "更新单机状态卡、问题台账和最终设备状态。"),
        ("每周一次", "汇总共性问题、配置差异和已通过阶段，调整机器优先级。"),
        ("达到M7后", "由另一人按验收清单复测，通过后才能进入M8版本冻结。"),
    ]
    for label, text in cadence:
        add_body(doc, f"{label}：{text}", bold_label=f"{label}：")

    doc.add_page_break()
    add_heading(doc, "15. 首轮实施清单", 1)
    add_table(
        doc,
        ["序号", "动作", "负责人", "完成日期", "状态"],
        [
            ("1", "为全部在调机器分配唯一MACHINE编号", "", "", ""),
            ("2", "为每台机器创建档案目录和状态卡", "", "", ""),
            ("3", "盘点当前配置、源码、固件和接线", "", "", ""),
            ("4", "确定每台机器所处的M0-M8阶段", "", "", ""),
            ("5", "建立中央问题台账并录入当前阻断问题", "", "", ""),
            ("6", "选定统一基础打印测试件和验收方法", "", "", ""),
            ("7", "完成首台机器BASE_PRINT版本冻结", "", "", ""),
            ("8", "复制流程到其余机器并持续修订本手册", "", "", ""),
        ],
        [720, 4440, 1440, 1440, 1320],
        font_size=9.3,
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER],
    )

    add_callout(doc, "初稿说明", "本手册用于第一轮讨论。请重点修改阶段划分、验收指标、人员职责、文件命名和实际执行难度；确认后再形成正式V1.0版本。", fill=GOLD, accent="7A5A00")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.core_properties.title = "硬件电子部机器基础打印调试与技术文档管理手册"
    doc.core_properties.subject = "多机基础打印调试、技术记录、验收与版本冻结"
    doc.core_properties.author = "硬件电子部"
    doc.core_properties.keywords = "CoreXY, Klipper, 机器调试, 基础打印, 技术文档"
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build_document()
