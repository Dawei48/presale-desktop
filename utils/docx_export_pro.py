"""
docx_export_pro.py — 生产单导出（出版级三线表）

为什么单独写这个文件：老 docx_export.py 的表格是"每个格子都画框"，
打印出来像 Excel 截图。专业排版用三线表（booktabs）：
    顶线粗、表头上方线细、表头下细线、底线粗，中间无竖线。
这是学术出版和商务单据的通行做法，打印最干净，窑口师傅也最好读。

结构：
    标题（窑口 + 生产单）
    副信息（日期 / 单号 / 件数）
    表格（序号｜图片｜商品｜规格｜数量｜备注）
    页脚签字区（制单 / 窑口签收 / 日期）
"""
import io
import os
from datetime import datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ── 排版常量 ────────────────────────────────────────────────
FONT_CN = "等线"
FONT_EN = "Arial"
INK = RGBColor(0x1A, 0x1A, 0x1A)
INK_2 = RGBColor(0x55, 0x55, 0x55)
INK_3 = RGBColor(0x8A, 0x8A, 0x8A)
RULE = "262626"


# ── 底层工具 ────────────────────────────────────────────────
def _set_run(run, size=10, bold=False, color=INK, cn=FONT_CN):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT_EN
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn)
    rfonts.set(qn("w:ascii"), FONT_EN)
    rfonts.set(qn("w:hAnsi"), FONT_EN)


def _cell_border(cell, edge, sz, color=RULE, val="single"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    tag = "w:" + edge
    el = borders.find(qn(tag))
    if el is None:
        el = OxmlElement(tag)
        borders.append(el)
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(sz))        # 1/8 pt
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), color)


def _cell_text(cell, text, size=10, bold=False, color=INK,
               align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0):
    p = cell.paragraphs[0]
    # 清掉已有的 run（cell.text = "" 会留一个空 run，字号读出来是 None）
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run(str(text) if text is not None else "")
    _set_run(run, size=size, bold=bold, color=color)
    # 垂直居中
    tcPr = cell._tc.get_or_add_tcPr()
    va = tcPr.find(qn("w:vAlign"))
    if va is None:
        va = OxmlElement("w:vAlign")
        tcPr.append(va)
    va.set(qn("w:val"), "center")


def _set_row_height(row, cm):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(cm * 567)))   # twips
    h.set(qn("w:hRule"), "atLeast")
    trPr.append(h)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _no_borders_table(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tblPr.append(borders)


# ── 图片 ────────────────────────────────────────────────────
def _image_stream(path, max_px=420):
    if not path:
        return None
    try:
        from PIL import Image
        if str(path).startswith("http"):
            import urllib.request
            with urllib.request.urlopen(path, timeout=8) as resp:
                img = Image.open(io.BytesIO(resp.read()))
        else:
            if not os.path.exists(path):
                return None
            img = Image.open(path)
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=82, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


# ── 主函数 ──────────────────────────────────────────────────
def export_production_docx(kiln_name, orders, filepath, brand_name=None):
    """
    orders: [{goods_name, spec, quantity, notes, image_path/product_image_path}]
    返回合并后的品项数
    """
    # 合并同款同规格
    merged = {}
    for o in orders:
        name = (o.get("goods_name") or o.get("product_name") or "未命名商品").strip()
        spec = (o.get("spec") or "").strip()
        key = (name, spec)
        if key not in merged:
            merged[key] = {
                "name": name, "spec": spec, "qty": 0, "notes": [],
                "image": o.get("product_image_path") or o.get("image_path") or "",
            }
        merged[key]["qty"] += int(o.get("quantity") or 1)
        note = (o.get("notes") or "").strip()
        if note and note not in merged[key]["notes"]:
            merged[key]["notes"].append(note)

    items = list(merged.values())

    doc = Document()

    # 页面：A4 纵向
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)

    # 默认样式
    style = doc.styles["Normal"]
    style.font.name = FONT_EN
    style.font.size = Pt(10)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)

    # ── 标题区 ──
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("生 产 单")
    _set_run(r, size=17, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)
    sub = kiln_name if kiln_name and kiln_name not in ("生产单", "全部") else ""
    r = p.add_run(sub or "全部窑口")
    _set_run(r, size=12.5, bold=True, color=INK_2)

    total_qty = sum(i["qty"] for i in items)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(12)
    meta = f"{datetime.now():%Y年%m月%d日}　　共 {len(items)} 款　{total_qty} 件"
    if brand_name:
        meta = brand_name + "　　" + meta
    r = p.add_run(meta)
    _set_run(r, size=9, color=INK_3)

    # ── 表格 ──
    cols = [("序号", 1.1), ("图片", 2.1), ("商品", 7.6), ("规格", 2.9), ("数量", 1.3), ("备注", 2.8)]
    table = doc.add_table(rows=1, cols=len(cols))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _no_borders_table(table)

    widths = [Cm(w) for _, w in cols]
    for i, w in enumerate(widths):
        for cell in table.columns[i].cells:
            cell.width = w

    # 表头
    hdr = table.rows[0]
    _set_row_height(hdr, 1.0)
    _repeat_header(hdr)
    for i, (label, _) in enumerate(cols):
        c = hdr.cells[i]
        c.width = widths[i]
        _cell_text(c, label, size=8.5, bold=True, color=INK_2, space_after=3)
        _cell_border(c, "top", 12)            # 顶线 1.5pt
        _cell_border(c, "bottom", 4)          # 表头下线 0.5pt

    # 数据行
    for idx, it in enumerate(items, 1):
        row = table.add_row()
        _set_row_height(row, 1.85 if it["image"] else 1.15)
        for i in range(len(cols)):
            row.cells[i].width = widths[i]

        _cell_text(row.cells[0], idx, size=9, color=INK_3, align=WD_ALIGN_PARAGRAPH.CENTER)

        # 图片
        cell_img = row.cells[1]
        cell_img.text = ""
        buf = _image_stream(it["image"])
        if buf:
            p_img = cell_img.paragraphs[0]
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(2)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.add_run().add_picture(buf, width=Cm(1.55))
        else:
            _cell_text(cell_img, "—", size=9, color=INK_3, align=WD_ALIGN_PARAGRAPH.CENTER)

        # 商品名（窑口·工艺·画片·器型）
        _cell_text(row.cells[2], it["name"], size=10)
        _cell_text(row.cells[3], it["spec"] or "—", size=9, color=INK_2)
        _cell_text(row.cells[4], it["qty"], size=10, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[5], "、".join(it["notes"]) or "", size=8.5, color=INK_2)

        # 只画极淡的内部横线，不画竖线
        for c in row.cells:
            _cell_border(c, "bottom", 3, color="D8D8D8")

    # 底线加粗（最后一行的 bottom 改粗）
    for c in table.rows[-1].cells:
        _cell_border(c, "bottom", 12)

    # ── 签字区 ──
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    sign = doc.add_table(rows=1, cols=3)
    _no_borders_table(sign)
    labels = [("制单", Cm(6.2)), ("窑口签收", Cm(6.2)), ("日期", Cm(6.2))]
    for i, (label, w) in enumerate(labels):
        c = sign.rows[0].cells[i]
        c.width = w
        _cell_text(c, f"{label}：________________", size=9, color=INK_3)
        _cell_border(c, "top", 4, color="D8D8D8")

    # ── 页脚 ──
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("放心预 · 陶瓷预售协同")
    _set_run(fr, size=8, color=RGBColor(0xA8, 0xA8, 0xA8))

    doc.save(filepath)
    return len(items)
