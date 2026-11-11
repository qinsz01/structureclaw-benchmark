"""Deterministic OOXML rendering for the current benchmark catalogue.

The Node entry point validates the canonical schema and safely publishes the
result. This module reads the supplied JSON from stdin and uses only stdlib.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", S)
ET.register_namespace("r", R)

GROUPS = (
    ("family", "任务大类"), ("category", "能力子类"), ("structure", "结构类型"),
    ("dimension", "模型维度"), ("difficulty", "预设难度"), ("modality", "输入模态"),
    ("engine", "求解器"), ("language", "输入语言"),
)
COUNTS = (
    ("cases", "题目数"), ("turns", "交互轮次"), ("states", "模型状态数"),
    ("attachmentFiles", "输入附件文件数"), ("attachmentUses", "附件引用次数"),
    ("markdownFiles", "Markdown 文件数"), ("pngFiles", "PNG 文件数"), ("dxfFiles", "DXF 文件数"),
)
COUNT_NOTES = {
    "cases": "按题目 ID 计数；一道题可包含多轮交互和多个模型状态。",
    "turns": "按题目中的用户交互轮次累加；轮次不是题目数。",
    "states": "按题目的模型状态数累加；模型状态不是交互轮次。",
    "attachmentFiles": "同一题内按公开附件路径去重后累加；不同题的同名文件分别计数。",
    "attachmentUses": "逐轮累计附件引用；同一文件被多轮复用时可高于文件数。",
    "markdownFiles": "输入附件中的 Markdown 文件数；按题目及附件路径去重。",
    "pngFiles": "输入附件中的 PNG 文件数；按题目及附件路径去重。",
    "dxfFiles": "输入附件中的 DXF 文件数；按题目及附件路径去重。",
}
SHEET_NAMES = ("概览", "题目明细", "分类统计", "分类说明")
DIFFICULTY_NOTE = "预设难度，未按模型实测校准"
STATUS_NOTE = "编写、参考就绪、原生核验、输入复核、验收与模型试跑分别记录；已编写或已原生核验不表示已验收。"


def node(parent, name, attributes=None, text=None, namespace=S):
    child = ET.SubElement(parent, f"{{{namespace}}}{name}", attributes or {})
    if text is not None:
        child.text = text
    return child


def xml(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def excel_text(value):
    # Protect literal OOXML escape sequences before encoding XML-forbidden code
    # points. Inline strings keep '=', '+', '-', and '@' titles as text cells.
    value = re.sub(r"_x[0-9a-fA-F]{4}_", lambda match: "_x005F_" + match.group(0)[1:], value)
    return "".join(
        f"_x{ord(char):04X}_"
        if (ord(char) < 32 and char not in "\t\n") or 0xD800 <= ord(char) <= 0xDFFF or ord(char) in (0xFFFE, 0xFFFF)
        else char
        for char in value
    )


def column(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell(value, style=4):
    return value, style


def worksheet(rows, widths, freeze_rows=1, freeze_columns=0, filtering=True, merges=(), heights=None):
    root = ET.Element(f"{{{S}}}worksheet")
    last_column = column(len(widths))
    node(root, "dimension", {"ref": f"A1:{last_column}{len(rows)}"})
    view = node(node(root, "sheetViews"), "sheetView", {"workbookViewId": "0", "zoomScale": "85"})
    pane_attributes = {"state": "frozen", "topLeftCell": f"{column(freeze_columns + 1)}{freeze_rows + 1}"}
    if freeze_rows:
        pane_attributes["ySplit"] = str(freeze_rows)
    if freeze_columns:
        pane_attributes["xSplit"] = str(freeze_columns)
    pane_attributes["activePane"] = "bottomRight" if freeze_columns and freeze_rows else "bottomLeft" if freeze_rows else "topRight"
    node(view, "pane", pane_attributes)
    node(view, "selection", {"pane": pane_attributes["activePane"], "activeCell": pane_attributes["topLeftCell"], "sqref": pane_attributes["topLeftCell"]})
    node(root, "sheetFormatPr", {"defaultRowHeight": "24"})
    cols = node(root, "cols")
    for index, width in enumerate(widths, 1):
        node(cols, "col", {"min": str(index), "max": str(index), "width": str(width), "customWidth": "1"})
    data = node(root, "sheetData")
    for row_index, values in enumerate(rows, 1):
        attributes = {"r": str(row_index)}
        if heights and row_index in heights:
            attributes.update({"ht": str(heights[row_index]), "customHeight": "1"})
        row = node(data, "row", attributes)
        for col_index, (value, style) in enumerate(values, 1):
            attributes = {"r": f"{column(col_index)}{row_index}", "s": str(style)}
            if isinstance(value, int) and not isinstance(value, bool):
                attributes["t"] = "n"
                node(node(row, "c", attributes), "v", text=str(value))
            else:
                attributes["t"] = "inlineStr"
                text_node = node(node(node(row, "c", attributes), "is"), "t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
                text_node.text = excel_text(str(value))
    if filtering:
        node(root, "autoFilter", {"ref": f"A1:{last_column}{len(rows)}"})
    if merges:
        merged = node(root, "mergeCells", {"count": str(len(merges))})
        for reference in merges:
            node(merged, "mergeCell", {"ref": reference})
    node(root, "pageMargins", {"left": "0.3", "right": "0.3", "top": "0.5", "bottom": "0.5", "header": "0.2", "footer": "0.2"})
    return xml(root)


def overview(catalogue):
    rows = [
        [cell("Research 300 · 当前题目目录", 1)],
        [cell("统一公开输入 · 全部题目使用同一交付目录", 2)],
        [cell(DIFFICULTY_NOTE, 7)],
        [cell(STATUS_NOTE, 7)],
        [],
        [cell(value, 3) for value in ("统计口径", "数量", "说明")],
    ]
    for key, label in COUNTS:
        rows.append([cell(label, 8), cell(catalogue["totals"][key], 9), cell(COUNT_NOTES[key], 4)])
    rows.extend([[], [cell(value, 3) for value in ("任务大类", "题目数", "交互轮次", "模型状态数", "输入附件文件数", "附件引用次数")]])
    for bucket in catalogue["breakdowns"]["family"]:
        rows.append([cell(bucket["zh"], 6)] + [cell(bucket[key], 5) for key in ("cases", "turns", "states", "attachmentFiles", "attachmentUses")])
    rows.extend([[], [cell("阅读提示", 6)], [cell("题目明细可筛选任务大类、能力子类、结构类型、模型维度、预设难度、输入语言、求解器、输入模态及各项当前状态。", 7)], [cell("分类统计逐项呈现与网页共用的分类数据；分类说明包含分类定义及计数、状态口径。", 7)], [cell("本工作簿为当前目录导出；原始归档工作簿保持不变。", 7)]])
    merges = ["A1:F1", "A2:F2", "A3:F3", "A4:F4"]
    merges.extend(f"A{index}:F{index}" for index in range(len(rows) - 2, len(rows) + 1))
    heights = {1: 36, 2: 25, 3: 28, 4: 36, 6: 30}
    heights.update({index: 42 for index in range(7, 15)})
    heights.update({index: 32 for index in range(len(rows) - 2, len(rows) + 1)})
    return worksheet(rows, [30, 17, 67, 18, 22, 22], freeze_rows=6, filtering=False, merges=merges, heights=heights)


def details(catalogue, choices):
    headers = ("题目 ID", "题目", "任务大类", "能力子类", "结构类型", "模型维度", "预设难度", "预设难度说明", "输入语言", "求解器", "输入模态", "交互轮次", "模型状态数", "输入附件文件数", "附件引用次数", "Markdown 文件数", "PNG 文件数", "DXF 文件数", "已编写", "参考结果就绪", "原生核验", "输入复核", "已验收", "模型试跑", "考查重点")
    rows = [[cell(header, 3) for header in headers]]
    for row in catalogue["cases"]:
        label = lambda group: choices[group][row[group]]["zh"]
        difficulty = label("difficulty")
        if not re.match(rf"^{re.escape(row['difficulty'])}(?:$|[\s·:：–—-])", difficulty):
            difficulty = row["difficulty"] + " · " + difficulty
        values = [row["id"], row["title"], label("family"), label("category"), label("structure"), label("dimension"), difficulty, row["difficultyReason"], label("language"), label("engine"), label("modality")]
        cells = [cell(value, 6 if index == 0 else 4) for index, value in enumerate(values)]
        cells.extend(cell(row[key], 5) for key in ("turns", "states", "attachmentFiles", "attachmentUses", "markdownFiles", "pngFiles", "dxfFiles"))
        cells.extend(cell("是" if row[key] else "否", 10 if row[key] else 11) for key in ("authored", "referenceReady", "nativeVerified"))
        cells.append(cell(row["inputReviewStatus"]))
        cells.append(cell("是" if row["accepted"] else "否", 10 if row["accepted"] else 11))
        cells.extend((cell(row["modelTrialStatus"]), cell(row["focus"])))
        rows.append(cells)
    widths = [16, 48, 20, 27, 20, 14, 22, 48, 12, 17, 16, 13, 15, 20, 17, 20, 16, 16, 12, 18, 14, 17, 12, 17, 64]
    return worksheet(rows, widths, freeze_columns=2, heights={1: 42, **{i: 60 for i in range(2, len(rows) + 1)}})


def statistics(catalogue, choices):
    headers = ("分类维度", "分类键", "分类名称", "English", "所属任务大类") + tuple(label for _, label in COUNTS)
    rows = [[cell(header, 3) for header in headers]]
    for group, label in GROUPS:
        for bucket in catalogue["breakdowns"][group]:
            family = choices["family"][bucket["family"]]["zh"] if bucket.get("family") else ""
            rows.append([cell(value) for value in (label, bucket["key"], bucket["zh"], bucket["en"], family)] + [cell(bucket[key], 5) for key, _ in COUNTS])
    return worksheet(rows, [18, 30, 30, 42, 20, 14, 15, 17, 22, 20, 22, 18, 18], heights={1: 42})


def definitions(catalogue, choices):
    rows = [[cell(header, 3) for header in ("分类维度", "分类键", "中文名称", "English", "所属任务大类", "定义 / 说明")]]
    for group, label in GROUPS:
        for definition in catalogue["definitions"][group]:
            family = choices["family"][definition["family"]]["zh"] if definition.get("family") else ""
            values = (label, definition["key"], definition["zh"], definition["en"], family, definition.get("description", ""))
            rows.append([cell(value) for value in values])
    for key, label in COUNTS:
        rows.append([cell(value) for value in ("统计口径", key, label, "", "", COUNT_NOTES[key])])
    notes = (
        ("difficulty", "预设难度", DIFFICULTY_NOTE + "；L1 / L2 / L3 的具体含义以本表的分类定义及题目难度说明为准。"),
        ("authored", "已编写", "当前题目的编写状态；不代表原生核验、输入复核、验收或模型试跑已完成。"),
        ("referenceReady", "参考结果就绪", "参考结果是否已就绪；此列仅显示状态，不含参考数值。"),
        ("nativeVerified", "原生核验", "是否完成原生求解器核验；与输入复核、验收及模型试跑状态分别记录。"),
        ("inputReviewStatus", "输入复核", "pending＝待复核；passed＝通过；failed＝失败；partial＝部分完成；invalid＝复核无效。"),
        ("accepted", "已验收", "单独记录的验收状态；已编写或已原生核验不表示已验收。"),
        ("modelTrialStatus", "模型试跑", "not-run＝尚无试跑记录；run＝已有试跑记录。试跑状态不表示通过率、难度校准或已验收。"),
    )
    for key, label, description in notes:
        rows.append([cell(value) for value in ("状态与难度口径", key, label, "", "", description)])
    return worksheet(rows, [22, 30, 30, 42, 20, 94], heights={1: 38, **{i: 48 for i in range(2, len(rows) + 1)}})


def styles():
    root = ET.Element(f"{{{S}}}styleSheet")
    fonts = node(root, "fonts", {"count": "7"})
    for size, color, bold in ((10, "243247", False), (20, "FFFFFF", True), (10, "64748B", False), (10, "FFFFFF", True), (10, "243247", True), (17, "1D4ED8", True), (10, "15803D", True)):
        font = node(fonts, "font")
        if bold:
            node(font, "b")
        node(font, "sz", {"val": str(size)})
        node(font, "color", {"rgb": "FF" + color})
        node(font, "name", {"val": "Microsoft YaHei"})
        node(font, "family", {"val": "2"})
    fills = node(root, "fills", {"count": "4"})
    for pattern, color in (("none", None), ("gray125", None), ("solid", "172A46"), ("solid", "EFF6FF")):
        fill = node(node(fills, "fill"), "patternFill", {"patternType": pattern})
        if color:
            node(fill, "fgColor", {"rgb": "FF" + color})
            node(fill, "bgColor", {"indexed": "64"})
    borders = node(root, "borders", {"count": "2"})
    for bordered in (False, True):
        border = node(borders, "border")
        for side in ("left", "right", "top", "bottom", "diagonal"):
            edge = node(border, side, {"style": "hair"} if bordered and side == "bottom" else {})
            if bordered and side == "bottom":
                node(edge, "color", {"rgb": "FFE2E8F0"})
    node(node(root, "cellStyleXfs", {"count": "1"}), "xf", {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
    # font, fill, border, horizontal, wrap; index is used explicitly by cells.
    formats = (
        (0, 0, 0, "left", False), (1, 2, 0, "left", True), (2, 0, 0, "left", True),
        (3, 2, 0, "left", True), (0, 0, 1, "left", True), (0, 0, 1, "center", False),
        (4, 0, 1, "left", True), (2, 3, 0, "left", True), (4, 3, 1, "left", True),
        (5, 3, 1, "center", False), (6, 0, 1, "center", True), (2, 0, 1, "center", True),
    )
    xfs = node(root, "cellXfs", {"count": str(len(formats))})
    for font, fill, border, horizontal, wrap in formats:
        xf = node(xfs, "xf", {"numFmtId": "0", "fontId": str(font), "fillId": str(fill), "borderId": str(border), "xfId": "0", "applyFont": "1", "applyFill": "1", "applyBorder": "1", "applyAlignment": "1"})
        node(xf, "alignment", {"horizontal": horizontal, "vertical": "center" if not wrap else "top", "wrapText": "1" if wrap else "0"})
    node(node(root, "cellStyles", {"count": "1"}), "cellStyle", {"name": "Normal", "xfId": "0", "builtinId": "0"})
    node(root, "dxfs", {"count": "0"})
    node(root, "tableStyles", {"count": "0", "defaultTableStyle": "TableStyleMedium2", "defaultPivotStyle": "PivotStyleLight16"})
    return xml(root)


def workbook():
    root = ET.Element(f"{{{S}}}workbook")
    node(node(root, "bookViews"), "workbookView", {"activeTab": "0"})
    sheets = node(root, "sheets")
    for index, name in enumerate(SHEET_NAMES, 1):
        node(sheets, "sheet", {"name": name, "sheetId": str(index), f"{{{R}}}id": f"rId{index}"})
    return xml(root)


def relationships(items):
    root = ET.Element("Relationships", {"xmlns": P})
    for identifier, kind, target in items:
        ET.SubElement(root, "Relationship", {"Id": identifier, "Type": kind, "Target": target})
    return xml(root)


def content_types():
    root = ET.Element("Types", {"xmlns": CT})
    for extension, mime in (("rels", "application/vnd.openxmlformats-package.relationships+xml"), ("xml", "application/xml")):
        ET.SubElement(root, "Default", {"Extension": extension, "ContentType": mime})
    entries = [("/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"), ("/xl/styles.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"), ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"), ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]
    entries.extend((f"/xl/worksheets/sheet{index}.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml") for index in range(1, 5))
    for name, mime in entries:
        ET.SubElement(root, "Override", {"PartName": name, "ContentType": mime})
    return xml(root)


def properties():
    cp = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    dc = "http://purl.org/dc/elements/1.1/"
    dcterms = "http://purl.org/dc/terms/"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"
    for prefix, namespace in (("cp", cp), ("dc", dc), ("dcterms", dcterms), ("xsi", xsi)):
        ET.register_namespace(prefix, namespace)
    core = ET.Element(f"{{{cp}}}coreProperties")
    node(core, "creator", text="StructureClaw", namespace=dc)
    node(core, "title", text="Research 300 · 当前题目目录", namespace=dc)
    for field in ("created", "modified"):
        node(core, field, {f"{{{xsi}}}type": "dcterms:W3CDTF"}, "1980-01-01T00:00:00Z", namespace=dcterms)
    ep = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
    vt = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
    app = ET.Element("Properties", {"xmlns": ep, "xmlns:vt": vt})
    ET.SubElement(app, "Application").text = "StructureClaw Catalogue"
    parts = ET.SubElement(ET.SubElement(app, "TitlesOfParts"), "vt:vector", {"size": "4", "baseType": "lpstr"})
    for name in SHEET_NAMES:
        ET.SubElement(parts, "vt:lpstr").text = name
    return xml(core), xml(app)


def write_workbook(catalogue, target):
    choices = {group: {choice["key"]: choice for choice in catalogue["definitions"][group]} for group, _ in GROUPS}
    core, app = properties()
    package = [
        ("[Content_Types].xml", content_types()),
        ("_rels/.rels", relationships((("rId1", R + "/officeDocument", "xl/workbook.xml"), ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"), ("rId3", R + "/extended-properties", "docProps/app.xml")))),
        ("docProps/core.xml", core), ("docProps/app.xml", app), ("xl/workbook.xml", workbook()),
        ("xl/_rels/workbook.xml.rels", relationships(tuple((f"rId{index}", R + "/worksheet", f"worksheets/sheet{index}.xml") for index in range(1, 5)) + (("rId5", R + "/styles", "styles.xml"),))),
        ("xl/styles.xml", styles()), ("xl/worksheets/sheet1.xml", overview(catalogue)),
        ("xl/worksheets/sheet2.xml", details(catalogue, choices)),
        ("xl/worksheets/sheet3.xml", statistics(catalogue, choices)),
        ("xl/worksheets/sheet4.xml", definitions(catalogue, choices)),
    ]
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in package:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compresslevel=9)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected one output .xlsx path; catalogue JSON is read from stdin")
        write_workbook(json.load(sys.stdin), Path(sys.argv[1]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Workbook export failed: {error}", file=sys.stderr)
        sys.exit(1)
