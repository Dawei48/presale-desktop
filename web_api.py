"""
web_api.py — pywebview JS 桥接层

约定：所有方法返回 {"ok": True, "data": ...} 或 {"ok": False, "error": str}
前端 api.js 只认这两种形状。异常绝不外泄到 JS（否则 UI 卡死无提示）。
"""
import os
import sys
import json
import traceback
import subprocess
from datetime import datetime

import webview

from config import BASE_DIR, DATA_DIR

# 旧状态 → 新状态机（老库里的数据要能继续用）
STATUS_MAP = {
    "pending": "ready",      # 老"未发货" = 新"待发货"
    "completed": "done",
    "cancelled": "cancelled",
}


def _norm_status(s):
    return STATUS_MAP.get(s, s or "ready")


def _err(e):
    return {"ok": False, "error": f"{type(e).__name__}: {e}"}


class WebApi:
    def __init__(self, db, window=None):
        self.db = db
        self.window = window
        self.settings_path = os.path.join(DATA_DIR, "settings.json")
        self.settings = self._load_settings()

    # ── 设置 ────────────────────────────────────────────
    def _load_settings(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_settings(self):
        try:
            return {"ok": True, "data": self.settings}
        except Exception as e:
            return _err(e)

    def save_settings(self, s):
        try:
            if isinstance(s, dict):
                self.settings.update(s)
                self._save_settings()
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def set_theme(self, name):
        """前端主题变了，同步 Windows 标题栏颜色，避免浅色界面配深色标题栏。"""
        try:
            self.settings["theme"] = name
            self._save_settings()
            self._apply_titlebar(name)
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def _apply_titlebar(self, name):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            dwm = ctypes.windll.dwmapi
            # 用窗口标题找句柄最稳（pywebview 的 gui 对象在不同后端字段不一样）
            hwnd = user32.FindWindowW(None, "放心预")
            if not hwnd:
                return
            if name == "light":
                v = ctypes.c_int(0)
                caption, border = 0x00F7F7F6, 0x00E6E3DE
            else:
                v = ctypes.c_int(1)
                caption, border = 0x00110F0E, 0x00201F1E
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v), 4)
            c = ctypes.c_int(caption)
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c), 4)
            b = ctypes.c_int(border)
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(b), 4)
        except Exception:
            pass

    # ── 数据 ────────────────────────────────────────────
    def _all_orders(self, keyword=""):
        rows = self.db.get_orders(keyword=keyword or None) if keyword else self.db.get_orders()
        out = []
        for r in rows:
            r = dict(r)
            r["status"] = _norm_status(r.get("status"))
            out.append(r)
        return out

    def summary(self):
        try:
            rows = self._all_orders()
            counts = {"total": len(rows)}
            for r in rows:
                counts[r["status"]] = counts.get(r["status"], 0) + 1
            todo = sum(counts.get(k, 0) for k in ("confirm", "producing", "ready"))
            return {"ok": True, "data": {"counts": counts, "todo": todo}}
        except Exception as e:
            return _err(e)

    def orders(self, filter="all", keyword=""):
        try:
            rows = self._all_orders(keyword or "")
            if filter and filter != "all":
                if filter in ("presale", "normal", "stored"):
                    rows = [r for r in rows if (r.get("order_type") or "normal") == filter]
                else:
                    rows = [r for r in rows if r["status"] == filter]

            counts = {"total": len(self._all_orders())}
            for r in self._all_orders():
                counts[r["status"]] = counts.get(r["status"], 0) + 1
            todo = sum(counts.get(k, 0) for k in ("confirm", "producing", "ready"))
            return {"ok": True, "data": {"rows": rows, "counts": counts, "todo": todo}}
        except Exception as e:
            return _err(e)

    def order_detail(self, oid):
        try:
            r = self.db.get_order(int(oid))
            if r:
                r["status"] = _norm_status(r.get("status"))
            return {"ok": True, "data": r}
        except Exception as e:
            return _err(e)

    def _manual_product(self):
        """手录订单总要挂个商品；没有就用「手动录入」兜底。"""
        brands = self.db.get_brands()
        b = next((x for x in brands if x.get("name") == "手动录入"), None)
        bid = b["id"] if b else self.db.add_brand("手动录入")
        prods = self.db.get_products(brand_id=bid)
        p = next((x for x in prods if x.get("name") == "手动录入"), None)
        return p["id"] if p else self.db.add_product(bid, "手动录入")

    def save_order(self, data):
        """新增或更新订单。data 带 id 就是更新。"""
        try:
            if not isinstance(data, dict):
                return {"ok": False, "error": "参数错误"}
            oid = data.get("id")
            fields = {}
            for k in ("order_no", "customer", "quantity", "notes", "status",
                      "order_type", "goods_name", "spec", "receiver_name",
                      "receiver_phone", "receiver_addr", "amount", "shop_type",
                      "ship_days"):
                if k in data and data[k] is not None and data[k] != "":
                    fields[k] = data[k]

            if "quantity" in fields:
                try:
                    fields["quantity"] = max(1, int(float(fields["quantity"])))
                except (TypeError, ValueError):
                    fields["quantity"] = 1
            if "amount" in fields:
                try:
                    fields["amount"] = float(fields["amount"])
                except (TypeError, ValueError):
                    fields["amount"] = 0

            if oid:
                self.db.update_order(int(oid), **fields)
                self.db.log("编辑订单", f"订单 {oid}")
                return {"ok": True, "data": {"id": int(oid)}}

            goods = fields.get("goods_name") or "未命名商品"
            pid = None
            for p in self.db.get_products():
                if p.get("name") == goods:
                    pid = p["id"]
                    break
            if pid is None:
                pid = self._manual_product()
            fields.setdefault("customer", "")
            fields.setdefault("order_no", "")
            new_id = self.db.add_order(product_id=pid, **fields)
            self.db.log("新增订单", f"{fields.get('order_no') or new_id}")
            return {"ok": True, "data": {"id": new_id}}
        except Exception as e:
            return _err(e)

    def delete_order(self, oid):
        try:
            self.db.delete_order(int(oid))
            self.db.log("删除订单", f"订单 {oid}")
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def save_product(self, data):
        try:
            if not isinstance(data, dict):
                return {"ok": False, "error": "参数错误"}
            pid = data.get("id")
            name = (data.get("name") or "").strip()
            if not name:
                return {"ok": False, "error": "商品名不能为空"}

            brands = self.db.get_brands()
            b = next((x for x in brands if x.get("name") == "手动录入"), None)
            bid = b["id"] if b else self.db.add_brand("手动录入")

            if pid:
                self.db.update_product(int(pid), name=name,
                                       notes=data.get("notes") or "",
                                       image_path=data.get("image_path") or "")
                return {"ok": True, "data": {"id": int(pid)}}
            new_id = self.db.add_product(bid, name, price=0,
                                         notes=data.get("notes") or "",
                                         image_path=data.get("image_path") or "")
            return {"ok": True, "data": {"id": new_id}}
        except Exception as e:
            return _err(e)

    def delete_product(self, pid):
        try:
            self.db.delete_product(int(pid))
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def pick_image(self):
        """选一张产品图，复制到 data/images，返回可写进库的相对路径。"""
        try:
            import shutil
            import uuid
            res = self.window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("图片 (*.png;*.jpg;*.jpeg;*.webp)", "所有文件 (*.*)"))
            if not res:
                return {"ok": False, "error": "已取消"}
            src = res[0] if isinstance(res, (list, tuple)) else res
            ext = os.path.splitext(src)[1].lower()
            from config import IMAGES_DIR
            os.makedirs(IMAGES_DIR, exist_ok=True)
            dest = os.path.join(IMAGES_DIR, f"{uuid.uuid4().hex[:12]}{ext}")
            shutil.copy2(src, dest)
            return {"ok": True, "data": {"path": dest}}
        except Exception as e:
            return _err(e)

    def set_status(self, oid, status):
        try:
            allowed = {"confirm", "producing", "ready", "stored", "shipped", "done", "cancelled"}
            if status not in allowed:
                return {"ok": False, "error": f"非法状态: {status}"}
            self.db.update_order(int(oid), status=status)
            self.db.log("改状态", f"订单 {oid} → {status}")
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def set_order_type(self, oid, otype):
        try:
            if otype not in ("normal", "presale", "stored"):
                return {"ok": False, "error": f"非法类型: {otype}"}
            self.db.update_order(int(oid), order_type=otype)
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def products(self, keyword=""):
        try:
            rows = self.db.get_products()
            seen = {}
            for p in rows:
                name = p.get("name") or ""
                kiln = name.split("·")[0].strip() if "·" in name else "—"
                key = (kiln, name)
                if key not in seen:
                    seen[key] = {
                        "id": p["id"], "kiln": kiln, "name": name,
                        "notes": p.get("notes") or "",
                        "image_path": p.get("image_path") or "",
                        "thumb": self._thumb(p.get("image_path") or ""),
                        "order_count": 0,
                    }
                seen[key]["order_count"] += 1
            return {"ok": True, "data": list(seen.values())}
        except Exception as e:
            return _err(e)

    @staticmethod
    def _thumb(path, size=96):
        """WebView2 不允许 file:// 页面读本地文件（实测三个路径全 FAILED），
        所以缩略图一律转成 base64 data URL 传给前端。"""
        if not path or not os.path.exists(path):
            return ""
        try:
            import base64
            import io
            from PIL import Image
            img = Image.open(path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail((size * 2, size * 2), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82, optimize=True)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""

    def fetch_images(self, goods_name):
        """按商品名搜网图，返回候选（不落库，等用户挑）。"""
        try:
            from utils.image_fetcher import build_keyword, search_images
            kw = build_keyword(goods_name)
            items = search_images(kw, 12)
            if not items:
                return {"ok": False, "error": f"没搜到「{kw}」的图，换个更具体的词试试"}
            return {"ok": True, "data": {"keyword": kw, "items": items[:9]}}
        except Exception as e:
            return {"ok": False, "error": f"搜图失败（网络或限流）：{e}"}

    def apply_image(self, product_id, url, goods_name=""):
        """下载选中的图 → 压到 900px → 写到商品。只改这一条，不动别的。"""
        try:
            from utils.image_fetcher import download_to
            from config import IMAGES_DIR
            if not url:
                return {"ok": False, "error": "没有图片地址"}
            path = download_to(url, IMAGES_DIR)
            if product_id:
                self.db.update_product(int(product_id), image_path=path)
                self.db.log("找图", f"商品 {product_id} 写入新图")
            else:
                # 没有 id（商品库聚合行）时按名字找
                for p in self.db.get_products():
                    if p.get("name") == goods_name:
                        self.db.update_product(p["id"], image_path=path)
                        break
            return {"ok": True, "data": {"path": path}}
        except Exception as e:
            return _err(e)

    def kilns(self):
        """按窑口聚合：这个窑口有哪些商品、各多少单、待生产多少件。
        窑口取商品名的第一段（「玉柏 · 青花 · 盖碗」→ 玉柏）。"""
        try:
            orders = self._all_orders()
            buckets = {}

            def bucket(kiln):
                if kiln not in buckets:
                    buckets[kiln] = {"name": kiln, "products": {}, "orders": 0, "pending": 0}
                return buckets[kiln]

            for o in orders:
                raw = (o.get("goods_name") or o.get("product_name") or "未命名商品").strip()
                parts = [x.strip() for x in raw.split("·") if x.strip()]
                kiln = parts[0] if len(parts) > 1 else "未标注窑口"
                product = " · ".join(parts[1:]) if len(parts) > 1 else raw

                b = bucket(kiln)
                b["orders"] += 1
                item = b["products"].setdefault(product, {
                    "name": product, "orders": 0, "pending": 0, "specs": set(),
                })
                item["orders"] += 1
                if o["status"] in ("confirm", "producing"):
                    item["pending"] += int(o.get("quantity") or 1)
                    b["pending"] += int(o.get("quantity") or 1)
                if o.get("spec"):
                    item["specs"].add(o["spec"])

            out = []
            for b in buckets.values():
                prods = []
                for it in b["products"].values():
                    prods.append({
                        "name": it["name"],
                        "orders": it["orders"],
                        "pending": it["pending"],
                        "specs": sorted(it["specs"]),
                    })
                prods.sort(key=lambda x: (-x["pending"], -x["orders"]))
                out.append({
                    "name": b["name"],
                    "orders": b["orders"],
                    "pending": b["pending"],
                    "products": prods,
                })
            out.sort(key=lambda x: (-x["pending"], -x["orders"]))
            return {"ok": True, "data": out}
        except Exception as e:
            return _err(e)

    def imports(self):
        try:
            rows = self.db.get_logs(limit=100)
            out = [r for r in rows if "导入" in (r.get("action") or "")]
            return {"ok": True, "data": out}
        except Exception as e:
            return _err(e)

    # ── 文件 ────────────────────────────────────────────
    def open_path(self, path):
        try:
            if path and os.path.exists(path):
                os.startfile(path)  # noqa: S606
                return {"ok": True}
            return {"ok": False, "error": "文件不存在"}
        except Exception as e:
            return _err(e)

    def export_production(self, opts=None):
        try:
            opts = opts or {}
            kiln = opts.get("kiln") or ""
            ids = opts.get("ids") or []

            rows = self._all_orders()
            if ids:
                idset = {int(i) for i in ids}
                rows = [r for r in rows if r["id"] in idset]
            if kiln:
                rows = [r for r in rows
                        if (r.get("goods_name") or "").split("·")[0].strip() == kiln
                        and r["status"] == "producing"]
            if not rows:
                return {"ok": False, "error": "这个窑口还没有「客户已同意延发」的单，先确认延发再导出"}

            default = f"{kiln or '全部'}_生产单_{datetime.now():%Y%m%d}.docx"
            path = self._ask_save(default)
            if not path:
                return {"ok": False, "error": "已取消"}

            from utils.docx_export_slip import export_production_docx
            count = export_production_docx(kiln or "生产单", rows, path)
            return {"ok": True, "data": {"path": path, "count": count}}
        except Exception as e:
            return _err(e)

    def _ask_save(self, filename):
        try:
            res = self.window.create_file_dialog(
                webview.SAVE_DIALOG, directory=str(BASE_DIR),
                save_filename=filename, file_types=("Word 文档 (*.docx)",))
            if isinstance(res, (list, tuple)):
                return res[0] if res else None
            return res
        except Exception:
            return os.path.join(BASE_DIR, filename)

    def import_csv(self):
        try:
            res = self.window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("CSV 文件 (*.csv)", "所有文件 (*.*)"))
            if not res:
                return {"ok": False, "error": "已取消"}
            path = res[0] if isinstance(res, (list, tuple)) else res
            from utils.csv_importer import import_csv_file
            stats = import_csv_file(self.db, path)
            self.db.log("导入订单", f"{os.path.basename(path)}：新增 {stats['added']}，跳过 {stats['dup']}")
            return {"ok": True, "data": stats}
        except Exception as e:
            return _err(e)

    def save_file(self, name, b64):
        try:
            import base64
            path = os.path.join(DATA_DIR, os.path.basename(name))
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            return {"ok": True, "data": {"path": path}}
        except Exception as e:
            return _err(e)
