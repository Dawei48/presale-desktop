"""
Word 导出 - 预售生产单
只导出「预售 + 未发货」订单，按 工艺|画片|器型|窑口 合并
无法识别的商品名归「待确认」组单独列出
"""
import os
import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from PIL import Image as PILImage
from utils.goods_parser import parse_goods_name, merge_key


def compress_image(img_path, max_size=(300, 300), quality=60):
    """压缩图片并返回字节流（支持本地路径和URL）"""
    if not img_path:
        return None
    try:
        if img_path.startswith("http"):
            import urllib.request
            with urllib.request.urlopen(img_path, timeout=10) as resp:
                img = PILImage.open(resp)
        else:
            img = PILImage.open(img_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


def export_brand_orders_docx(brand_name, orders, filepath, title=None):
    """导出预售生产单 - 只导「预售 + 未发货」，按词表拆解合并"""
    # 只取预售且未发货订单
    presale = [o for o in orders if o.get("order_type") == "presale" and o.get("status") == "pending"]
    if not presale:
        presale = [o for o in orders if o.get("status") == "pending"]  # 兼容旧数据

    if title is None:
        title = f"{brand_name} - 预售生产单"

    # 词表拆解 + 合并
    item_map = {}
    unknown = []
    for o in presale:
        parsed = parse_goods_name(o.get("goods_name") or o.get("product_name") or "")
        display = " ".join(x for x in [parsed["窑口"], parsed["工艺"], parsed["画片"], parsed["器型"]] if x)
        # 完全无法识别（工艺/画片/器型全空）→ 待确认
        if not parsed["工艺"] and not parsed["画片"] and not parsed["器型"]:
            unknown.append({
                "name": o.get("goods_name") or o.get("product_name") or "未知商品",
                "qty": o.get("quantity", 0),
            })
            continue
        key = merge_key(parsed)
        if key not in item_map:
            item_map[key] = {
                "display": display,
                "image_path": o.get("product_image_path", ""),
                "total_qty": 0,
                "notes": [],
            }
        item_map[key]["total_qty"] += o.get("quantity", 0)
        note = o.get("notes", "")
        if note and note not in item_map[key]["notes"]:
            item_map[key]["notes"].append(note)

    if not item_map and not unknown:
        doc = Document()
        doc.add_paragraph("暂无预售订单")
        doc.save(filepath)
        return filepath

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    # Logo + 标题
    from config import _find_resource
    logo_path = _find_resource("assets/logo.png")
    if os.path.exists(logo_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(logo_path, width=Cm(2.5))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"生成日期：{datetime.now().strftime('%Y-%m-%d')}")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    doc.add_paragraph()

    # 主表: 图片 | 产品名称 | 数量 | 备注
    headers = ["产品图片", "产品名称", "数量", "备注"]
    rows_count = len(item_map) + (1 if unknown else 0)
    if item_map:
        table = doc.add_table(rows=1 + len(item_map), cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        for row in table.rows:
            row.cells[0].width = Cm(2.5)
            row.cells[1].width = Cm(7)
            row.cells[2].width = Cm(2)
            row.cells[3].width = Cm(6)

        # 表头
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            for par in cell.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in par.runs:
                    run.font.size = Pt(10)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0F172A"/>')
            cell._tc.get_or_add_tcPr().append(shading)

        # 数据行
        for ri, data in enumerate(item_map.values()):
            row = table.rows[ri + 1]
            row.height = Cm(2.5)

            # 图片
            cell_img = row.cells[0]
            cell_img.paragraphs[0].clear()
            img_path = data.get("image_path", "")
            has_img = img_path and (img_path.startswith("http") or os.path.exists(img_path))
            if has_img:
                buf = compress_image(img_path, max_size=(200, 200), quality=50)
                if buf:
                    p = cell_img.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(buf, width=Cm(2.2))

            # 名称
            cell_name = row.cells[1]
            cell_name.text = data["display"]
            for par in cell_name.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in par.runs:
                    run.font.size = Pt(11)
                    run.font.bold = True

            # 数量
            cell_qty = row.cells[2]
            cell_qty.text = str(data["total_qty"])
            for par in cell_qty.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in par.runs:
                    run.font.size = Pt(11)
                    run.font.bold = True

            # 备注
            cell_notes = row.cells[3]
            cell_notes.text = "、".join(data["notes"]) if data["notes"] else "-"
            for par in cell_notes.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in par.runs:
                    run.font.size = Pt(9)

            # 斑马纹
            if ri % 2 == 0:
                for ci in range(len(headers)):
                    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>')
                    row.cells[ci]._tc.get_or_add_tcPr().append(shading)

    # 待确认组
    if unknown:
        doc.add_paragraph()
        p = doc.add_paragraph()
        run = p.add_run("⚠️ 待人工确认（商品名无法自动识别，请手动补画片/器型）")
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xC9, 0x8A, 0x2E)
        for u in unknown:
            p = doc.add_paragraph()
            run = p.add_run(f"• {u['name']}  ×{u['qty']}")
            run.font.size = Pt(10)

    # 页脚
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("— 放心预 —")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    doc.save(filepath)
    return filepath
