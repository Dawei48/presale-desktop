"""
image_fetcher.py — 按商品名从网上找产品图

用途：商品库里的商品没有图，手动拍照上传太慢时，先搜一批候选图，
      人工点选确认后才入库。**永远不自动覆盖已有图片**，
      因为搜图有错配（同名不同器型、别家的图），必须人来拍板。

数据源：百度图片 JSON 接口（免费、无需 key、中文命中率高）
"""
import io
import json
import os
import re
import urllib.parse
import urllib.request
import uuid

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")

SEARCH_URL = ("https://image.baidu.com/search/acjson?tn=resultjson_com&ipn=rj"
              "&ct=201326592&fp=result&queryWord={q}&cl=2&lm=-1&ie=utf-8&oe=utf-8"
              "&st=-1&word={q}&face=0&istype=2&nc=1&pn=0&rn={n}")


def build_keyword(goods_name):
    """商品名 → 搜索词。
    去掉窑口（商号）和规格，只留「工艺 + 画片 + 器型」，搜得更准。
    例：玉柏 · 青花缠枝莲 · 盖碗  →  青花缠枝莲 盖碗"""
    if not goods_name:
        return ""
    parts = [p.strip() for p in str(goods_name).split("·") if p.strip()]
    if len(parts) >= 2:
        parts = parts[1:]
    kw = " ".join(parts)
    kw = re.sub(r"\d+\s*(ml|ML|cm|CM|寸|头)", "", kw)
    return kw.strip() or goods_name.strip()


def _get(url, referer="https://image.baidu.com/", timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search_images(keyword, limit=12):
    """返回 [{thumb, url, title}]，失败抛异常由调用方处理。"""
    if not keyword:
        return []
    q = urllib.parse.quote(keyword)
    raw = _get(SEARCH_URL.format(q=q, n=limit)).decode("utf-8", "ignore")
    # 百度偶尔返回带 \' 的伪 JSON
    raw = raw.replace("\\'", "'")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raw = re.sub(r"[\x00-\x1f]", "", raw)
        data = json.loads(raw)

    out = []
    for item in data.get("data", []):
        if not isinstance(item, dict):
            continue
        thumb = item.get("thumbURL") or item.get("middleURL") or ""
        big = item.get("middleURL") or item.get("hoverURL") or thumb
        if not thumb:
            continue
        title = re.sub(r"<[^>]+>", "", item.get("fromPageTitleEnc") or "")
        out.append({"thumb": thumb, "url": big, "title": title.strip()[:40]})
    return out


def download_to(url, images_dir, referer="https://image.baidu.com/"):
    """下载一张图到 images_dir，自动压到 900px 内，返回本地路径。"""
    blob = _get(url, referer=referer, timeout=20)
    if not blob or len(blob) < 2000:
        raise ValueError("图片太小或下载失败")

    from PIL import Image
    img = Image.open(io.BytesIO(blob))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((900, 900), Image.LANCZOS)

    os.makedirs(images_dir, exist_ok=True)
    dest = os.path.join(images_dir, f"{uuid.uuid4().hex[:12]}.jpg")
    img.save(dest, "JPEG", quality=88, optimize=True)
    return dest


if __name__ == "__main__":
    kw = build_keyword("玉柏 · 青花缠枝莲 · 盖碗")
    print("搜索词:", kw)
    res = search_images(kw, 8)
    print("结果:", len(res))
    for r in res[:6]:
        print(" -", r["title"][:24], r["thumb"][:70])
