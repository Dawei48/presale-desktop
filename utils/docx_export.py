"""
Word 导出 - 按品牌导出所有预售订单
包含: 产品图片 + 产品名 + 价格 + 预售总数量 + 订单明细表
"""
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml


def export_brand_orders_docx(brand_name, orders, filepath, title=None):
    """按品牌导出所有订单"""
    if title is None:
        title = f"{brand_name} - 预售订单汇总"
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # 标题
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"生成日期：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    doc.add_paragraph()

    # 统计
    total_qty = sum(o.get("quantity", 0) for o in orders)
    status_count = {}
    for o in orders:
        s = o.get("status", "pending")
        status_count[s] = status_count.get(s, 0) + 1

    status_labels = {"pending": "未发货", "shipped": "已发货", "completed": "已完成", "cancelled": "已取消"}

    p = doc.add_paragraph()
    run = p.add_run("统计摘要")
    run.font.size = Pt(14)
    run.font.bold = True

    for label, value in [("订单总数", f"{len(orders)} 笔"), ("总数量", f"{total_qty} 件")]:
        p = doc.add_paragraph()
        run = p.add_run(f"  {label}：")
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        run = p.add_run(value)
        run.font.size = Pt(11)
        run.font.bold = True

    for sk, count in status_count.items():
        p = doc.add_paragraph()
        run = p.add_run(f"  {status_labels.get(sk, sk)}：{count} 笔")
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    doc.add_paragraph()

    # 按产品分组
    products = {}
    for o in orders:
        pname = o.get("product_name", "未知")
        if pname not in products:
            products[pname] = {"orders": [], "price": o.get("product_price", 0),
                               "image_path": o.get("product_image_path", "")}
        products[pname]["orders"].append(o)

    for pdata in products.values():
        porders = pdata["orders"]
        pname = porders[0].get("product_name", "未知") if porders else "未知"
        pprice = pdata.get("price", 0)
        pimage = pdata.get("image_path", "")
        pqty = sum(o.get("quantity", 0) for o in porders)

        # 产品卡片: 图片 + 信息
        if pimage and os.path.exists(pimage):
            try:
                p = doc.add_paragraph()
                run = p.add_run()
                run.add_picture(pimage, width=Cm(4))
                # 图片放在产品名前面
            except Exception:
                pass

        # 产品名 + 价格 + 总数量
        p = doc.add_paragraph()
        run = p.add_run(f"产品: {pname}")
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

        p = doc.add_paragraph()
        run = p.add_run(f"  单价: ¥{pprice:,.0f}    预售数量: {pqty} 件    订单数: {len(porders)} 笔")
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

        doc.add_paragraph()

        # 订单明细表
        headers = ["订单号", "客户", "数量", "状态", "备注", "日期"]
        table = doc.add_table(rows=1 + len(porders), cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

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

        for ri, o in enumerate(porders):
            vals = [
                o.get("order_no", ""),
                o.get("customer", ""),
                str(o.get("quantity", 0)),
                status_labels.get(o.get("status", ""), o.get("status", "")),
                o.get("notes", ""),
                o.get("created_at", "")[:10],
            ]
            for ci, v in enumerate(vals):
                cell = table.rows[ri + 1].cells[ci]
                cell.text = v
                for par in cell.paragraphs:
                    for run in par.runs:
                        run.font.size = Pt(9)
            if ri % 2 == 0:
                for ci in range(len(headers)):
                    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
                    table.rows[ri + 1].cells[ci]._tc.get_or_add_tcPr().append(shading)

        doc.add_paragraph()

    # 页脚
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("— 放心预 · 预售管理系统 —")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    doc.save(filepath)
    return filepath
