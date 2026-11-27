"""
docx_preview.py — 把 .docx 渲染成 HTML（仅用于自检看排版，不是生产功能）

为什么需要：本机没有 Word / WPS / LibreOffice，python-docx 只能验结构，
看不到"长什么样"。这个脚本读 docx 的 XML，还原文字、字号、粗体、颜色、
单元格底色、对齐、边框、图片，吐出一个近似 HTML，再用浏览器截图看。
"""
import os
import sys
import base64

from docx import Document
from docx.oxml.ns import qn


def _run_style(run):
    size = run.font.size.pt if run.font.size else 10.5
    bold = bool(run.font.bold)
    color = "#2b2724"
    try:
        if run.font.color and run.font.color.rgb:
            color = "#" + str(run.font.color.rgb)
    except Exception:
        pass
    return size, bold, color


def _cell_style(tc):
    tcPr = tc._tc.tcPr
    bg = None
    if tcPr is not None:
        shd = tcPr.find(qn("w:shd"))
        if shd is not None:
            fill = shd.get(qn("w:fill"))
            if fill and fill not in ("auto", "FFFFFF"):
                bg = "#" + fill
    return bg


def _para_html(p, part):
    """段落 → html，保留图片与 run 级样式"""
    out = []
    for child in p._p.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "r":
            run_el = child
            # 图片
            drawing = run_el.find(qn("w:drawing"))
            if drawing is not None:
                blobs = drawing.findall(".//" + qn("a:blip"))
                for b in blobs:
                    rid = b.get(qn("r:embed"))
                    if rid and rid in part.related_parts:
                        blob = part.related_parts[rid].blob
                        b64 = base64.b64encode(blob).decode()
                        out.append(
                            f'<img src="data:image/png;base64,{b64}" '
                            f'style="height:1.9cm;object-fit:contain">')
                continue
            text = "".join(t.text or "" for t in run_el.findall(qn("w:t")))
            if not text:
                continue
            # 粗体/字号
            rPr = run_el.find(qn("w:rPr"))
            size, bold, color = 10.5, False, "#2b2724"
            if rPr is not None:
                sz = rPr.find(qn("w:sz"))
                if sz is not None:
                    size = int(sz.get(qn("w:val"))) / 2
                if rPr.find(qn("w:b")) is not None:
                    bold = True
                c = rPr.find(qn("w:color"))
                if c is not None and c.get(qn("w:val")) not in (None, "auto"):
                    color = "#" + c.get(qn("w:val"))
            style = f"font-size:{size}pt;color:{color};" + ("font-weight:700;" if bold else "")
            out.append(f'<span style="{style}">{text}</span>')
    return "".join(out)


def _align(p):
    jc = p._p.find(qn("w:pPr"))
    if jc is None:
        return "left"
    j = jc.find(qn("w:jc"))
    if j is None:
        return "left"
    v = j.get(qn("w:val"))
    return {"center": "center", "right": "right", "both": "justify"}.get(v, "left")


def docx_to_html(path, title=""):
    doc = Document(path)
    part = doc.part
    body = []

    for el in doc.element.body.iterchildren():
        tag = el.tag.split("}")[-1]

        if tag == "p":
            from docx.text.paragraph import Paragraph
            p = Paragraph(el, doc)
            html = _para_html(p, part)
            if html.strip():
                body.append(
                    f'<p style="text-align:{_align(p)};margin:0 0 6px">{html}</p>')
            else:
                body.append('<p style="margin:0 0 6px">&nbsp;</p>')

        elif tag == "tbl":
            from docx.table import Table
            t = Table(el, doc)
            rows_html = []
            for ri, row in enumerate(t.rows):
                cells_html = []
                for cell in row.cells:
                    bg = _cell_style(cell)
                    inner = "".join(
                        _para_html(p, part) for p in cell.paragraphs
                    ) or "&nbsp;"
                    al = _align(cell.paragraphs[0]) if cell.paragraphs else "left"
                    style = ("border:.5pt solid #d6d1ca;padding:4px 6px;"
                             f"text-align:{al};vertical-align:middle;")
                    if bg:
                        style += f"background:{bg};"
                    cells_html.append(f'<td style="{style}">{inner}</td>')
                rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
            body.append(
                '<table style="border-collapse:collapse;width:100%;'
                'table-layout:fixed;margin:6px 0">' + "".join(rows_html) + "</table>")

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{{background:#fff;color:#2b2724;
 font-family:"Segoe UI","Microsoft YaHei UI",sans-serif;margin:0;padding:0;}}
.page{{width:21cm;min-height:29.7cm;padding:1.6cm 1.8cm;box-sizing:border-box;
 margin:0 auto;background:#fff;}}
p{{font-size:10.5pt;line-height:1.35}}
img{{max-width:100%}}
</style></head><body><div class="page">{''.join(body)}</div></body></html>"""


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2]
    with open(out, "w", encoding="utf-8") as f:
        f.write(docx_to_html(src))
    print("HTML", out, os.path.getsize(out))
