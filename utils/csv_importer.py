"""
csv_importer.py — 纯逻辑 CSV 导入（不依赖任何 GUI 库）

和老的 utils/csv_import.py 的区别：老文件 import 了 customtkinter，
pywebview 版不能碰它。这里是同一套规则的纯函数版本。

规则：
· 多编码尝试（utf-8-sig → utf-8 → gbk → gb2312 → gb18030）
· 列名按平台常见说法模糊匹配
· 订单类型只看备注关键词：预存 > 预售 > 其他=现货
· 订单号已存在则跳过（不覆盖手工改过的状态）
· 商品不存在时自动建到「未分类」品牌下
"""
import csv
import os
from datetime import datetime

FIELD_PATTERNS = {
    "order_no":      ["订单号", "订单编号", "订单id", "交易号", "order_no", "order_id"],
    "customer":      ["收货人", "买家昵称", "收件人", "客户名称", "客户", "customer", "buyer"],
    "goods_name":    ["商品名称", "宝贝标题", "商品标题", "商品", "产品名称", "title", "product"],
    "spec":          ["规格", "规格名称", "款式", "尺寸", "sku", "spec"],
    "quantity":      ["数量", "件数", "购买数量", "qty", "quantity", "num"],
    "created_at":    ["下单时间", "付款时间", "成交时间", "创建时间", "日期", "date", "time"],
    "notes":         ["备注", "买家留言", "留言", "remark", "note", "memo"],
    "receiver_phone": ["收货电话", "收货人电话", "手机号", "联系电话", "手机", "phone", "mobile"],
    "receiver_addr": ["收货地址", "详细地址", "地址", "address", "addr"],
    "amount":        ["实付金额", "订单金额", "商品金额", "应付金额", "实付", "金额", "amount"],
}

PLATFORM_DAYS = {"douyin": 2, "taobao": 3, "pdd": 3, "unknown": 30}


def _read_rows(path):
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:]
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return [], []


def _match(headers, field):
    pats = [p.lower() for p in FIELD_PATTERNS[field]]
    for i, h in enumerate(headers):
        hl = (h or "").strip().lower()
        if not hl:
            continue
        if hl in pats:
            return i
    for i, h in enumerate(headers):
        hl = (h or "").strip().lower()
        for p in pats:
            if p in hl or hl in p:
                return i
    return None


def _get(row, idx, default=""):
    if idx is None or idx >= len(row):
        return default
    return (row[idx] or "").strip()


def _amount(s):
    s = str(s or "").replace("¥", "").replace("￥", "").replace(",", "").replace("元", "").strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def detect_order_type(notes):
    if not notes:
        return "normal"
    if "预存" in notes:
        return "stored"
    if "预售" in notes:
        return "presale"
    return "normal"


def _norm_date(s):
    """平台导出的时间是 '2026-11-27 14:03:22' / '2026/11/27' 等，尽量归一。"""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _default_product(db):
    """订单必须挂在商品上；没有商品上下文时挂到「未分类」。
    返回 (product_id, brand_id) —— brand_id 用于新建商品时挂靠。"""
    brands = db.get_brands()
    brand = next((b for b in brands if b.get("name") == "未分类"), None)
    bid = brand["id"] if brand else db.add_brand("未分类")
    prods = db.get_products(brand_id=bid)
    p = next((x for x in prods if x.get("name") == "未分类"), None)
    pid = p["id"] if p else db.add_product(bid, "未分类")
    return pid, bid


FIELD_ALIAS = {"product": "goods_name"}


def _ai_fill_missing(headers, idx):
    """规则没认出来的列，交给 DeepSeek 认。返回被 AI 补上的字段名列表。"""
    missing = [f for f, i in idx.items() if i is None]
    if not missing:
        return []
    try:
        from config import ai_enabled, DEEPSEEK_API_KEY
        if not ai_enabled():
            return []
        from utils.ai_parser import parse_headers_with_ai
        mapping = parse_headers_with_ai(headers, DEEPSEEK_API_KEY)
        filled = []
        for k, col in mapping.items():
            key = FIELD_ALIAS.get(k, k)
            if key in idx and idx[key] is None:
                try:
                    idx[key] = headers.index(col)
                    filled.append(key)
                except ValueError:
                    continue
        return filled
    except Exception:
        return []


def import_csv_file(db, path, use_ai=True):
    """返回 {'added','dup','invalid','ai_fields','ai_used'}"""
    headers, rows = _read_rows(path)
    if not headers:
        raise ValueError("文件为空或编码无法识别")

    idx = {f: _match(headers, f) for f in FIELD_PATTERNS}
    ai_fields = _ai_fill_missing(headers, idx) if use_ai else []
    if idx["order_no"] is None and idx["goods_name"] is None:
        raise ValueError("没识别出订单号列或商品列，请确认这是平台导出的订单 CSV")

    fallback_pid, fallback_bid = _default_product(db)
    added = dup = invalid = 0
    known = {}
    for p in db.get_products():
        known.setdefault(p.get("name"), p["id"])

    for row in rows:
        if not row or not any((c or "").strip() for c in row):
            continue
        first = (row[0] or "").strip()
        if any(k in first for k in ("合计", "总计", "备注：", "小计")):
            continue

        order_no = _get(row, idx["order_no"])
        goods = _get(row, idx["goods_name"]) or "未分类商品"
        if not order_no and not goods:
            invalid += 1
            continue

        if order_no and db.get_order_by_no(order_no):
            dup += 1
            continue

        notes = _get(row, idx["notes"])
        qty_raw = _get(row, idx["quantity"], "1")
        try:
            qty = int(float(qty_raw)) if qty_raw else 1
        except (TypeError, ValueError):
            qty = 1

        # 商品不存在就建一个（避免所有单都堆在「未分类」）
        pid = known.get(goods)
        if pid is None:
            try:
                pid = db.add_product(fallback_bid, goods)
                known[goods] = pid
            except Exception:
                pid = fallback_pid

        db.add_order(
            product_id=pid,
            quantity=qty,
            order_no=order_no,
            customer=_get(row, idx["customer"]),
            notes=notes,
            created_at=_norm_date(_get(row, idx["created_at"])),
            ship_days=PLATFORM_DAYS["unknown"],
            order_type=detect_order_type(notes),
            goods_name=goods,
            spec=_get(row, idx["spec"]),
            receiver_name=_get(row, idx["customer"]),
            receiver_phone=_get(row, idx["receiver_phone"]),
            receiver_addr=_get(row, idx["receiver_addr"]),
            amount=_amount(_get(row, idx["amount"])),
        )
        added += 1

    return {"added": added, "dup": dup, "invalid": invalid,
            "ai_fields": ai_fields, "ai_used": bool(ai_fields)}
