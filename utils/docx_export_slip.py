"""
docx_export_slip.py — 生产单导出（商务单据风格）

设计取向：这是给窑口师傅照着做活的单子，不是给评审看的排版作品。
· 有 logo、有格子、有斑马纹 —— 一眼看清哪行是哪行
· 表头用暖墨色，和朱砂印章呼应（老版本用深蓝 #0F172A，和红印章打架）
· 边框细而软，不用 Word 默认的黑框
· 保留「— 放心预 —」落款
"""
import io
import os
from datetime import datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

FONT_CN = "等线"
FONT_EN = "Arial"

INK = RGBColor(0x2B, 0x27, 0x24)        # 暖墨（正文）
INK_2 = RGBColor(0x6B, 0x66, 0x60)      # 次级
INK_3 = RGBColor(0x9A, 0x95, 0x8E)      # 弱
HEAD_BG = "2B2724"                       # 表头底色：暖黑
ZEBRA = "F0EBE4"                         # 斑马纹：暖砂色，打印能看见
GRID = "D6D1CA"                          # 网格线


def _set_run(run, size=10.5, bold=False, color=INK, cn=FONT_CN):
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


def _shade(cell, fill):
    cell._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:fill="{fill}"/>'))


def _table_borders(table, color=GRID, sz=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _valign(cell, val="center"):
    tcPr = cell._tc.get_or_add_tcPr()
    va = tcPr.find(qn("w:vAlign"))
    if va is None:
        va = OxmlElement("w:vAlign")
        tcPr.append(va)
    va.set(qn("w:val"), val)


def _cell(cell, text, size=10.5, bold=False, color=INK,
          align=WD_ALIGN_PARAGRAPH.LEFT):
    p = cell.paragraphs[0]
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run(str(text) if text is not None else "")
    _set_run(run, size=size, bold=bold, color=color)
    _valign(cell)


def _row_height(row, cm):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(cm * 567)))
    h.set(qn("w:hRule"), "atLeast")
    trPr.append(h)


def _image_stream(path, max_px=520):
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
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


def export_production_docx(kiln_name, orders, filepath, brand_name=None):
    """返回合并后的款数。"""
    merged = {}
    for o in orders:
        name = (o.get("goods_name") or o.get("product_name") or "未命名商品").strip()
        spec = (o.get("spec") or "").strip()
        key = (name, spec)
        if key not in merged:
            merged[key] = {
                "name": name, "spec": spec, "qty": 0, "notes": [], "amount": 0.0,
                "image": o.get("product_image_path") or o.get("image_path") or "",
            }
        merged[key]["qty"] += int(o.get("quantity") or 1)
        try:
            merged[key]["amount"] += float(o.get("amount") or 0)
        except (TypeError, ValueError):
            pass
        note = (o.get("notes") or "").strip()
        if note and note not in merged[key]["notes"]:
            merged[key]["notes"].append(note)
    items = list(merged.values())

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = Cm(1.6)
    sec.bottom_margin = Cm(1.6)
    sec.left_margin = Cm(1.8)
    sec.right_margin = Cm(1.8)

    style = doc.styles["Normal"]
    style.font.name = FONT_EN
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)

    # ── 抬头：logo ──
    try:
        from config import _find_resource
        logo = _find_resource("assets/logo.png")
        if os.path.exists(logo):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            p.add_run().add_picture(logo, width=Cm(2.2))
    except Exception:
        pass

    # ── 标题 ──
    title = (f"{kiln_name} 生产单"
             if kiln_name and kiln_name not in ("生产单", "全部") else "生产单")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(3)
    _set_run(p.add_run(title), size=17, bold=True, color=INK)

    # ── 副信息 ──
    total_qty = sum(i["qty"] for i in items)
    total_amt = sum(i.get("amount") or 0 for i in items)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    meta = f"{datetime.now():%Y年%m月%d日}　共 {len(items)} 款　{total_qty} 件"
    if total_amt:
        meta += f"　¥{total_amt:,.0f}"
    if brand_name:
        meta = brand_name + "　" + meta
    _set_run(p.add_run(meta), size=9.5, color=INK_2)

    # ── 表格 ──
    headers = [("产品图片", Cm(2.9)), ("产品名称", Cm(7.6)),
               ("数量", Cm(1.5)), ("价格", Cm(2.4)), ("备注", Cm(2.9))]
    table = doc.add_table(rows=1 + len(items), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_borders(table)

    for ci, (_, w) in enumerate(headers):
        for cell in table.columns[ci].cells:
            cell.width = w

    hdr = table.rows[0]
    _row_height(hdr, 0.95)
    for ci, (label, _) in enumerate(headers):
        c = hdr.cells[ci]
        c.width = headers[ci][1]
        _cell(c, label, size=9.5, bold=True,
              color=RGBColor(0xFF, 0xFF, 0xFF), align=WD_ALIGN_PARAGRAPH.CENTER)
        _shade(c, HEAD_BG)

    for ri, it in enumerate(items):
        row = table.rows[ri + 1]
        _row_height(row, 2.3)
        for ci in range(len(headers)):
            row.cells[ci].width = headers[ci][1]

        cell_img = row.cells[0]
        buf = _image_stream(it["image"])
        if buf:
            p_img = cell_img.paragraphs[0]
            for r in list(p_img.runs):
                r._element.getparent().remove(r._element)
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(3)
            p_img.paragraph_format.space_after = Pt(3)
            p_img.add_run().add_picture(buf, width=Cm(1.9))
            _valign(cell_img)
        else:
            _cell(cell_img, "—", size=9, color=INK_3, align=WD_ALIGN_PARAGRAPH.CENTER)

        _cell(row.cells[1], it["name"], size=10.5, bold=True)
        _cell(row.cells[2], it["qty"], size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        amt = it.get("amount") or 0
        _cell(row.cells[3], f"¥{amt:,.0f}" if amt else "—", size=10,
              color=INK, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell(row.cells[4], "、".join(it["notes"]) or "", size=9, color=INK_2)

        if ri % 2 == 0:
            for ci in range(len(headers)):
                _shade(row.cells[ci], ZEBRA)

    # ── 合计行 ──
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    tail = f"合计　{len(items)} 款　{total_qty} 件"
    if total_amt:
        tail += f"　¥{total_amt:,.0f}"
    _set_run(p.add_run(tail), size=10.5, bold=True)

    # ── 落款 ──
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run(p.add_run("— 放心预 —"), size=9.5, color=INK_2)

    doc.save(filepath)
    return len(items)
