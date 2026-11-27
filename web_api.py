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
                        "kiln": kiln, "name": name,
                        "notes": p.get("notes") or "",
                        "order_count": 0,
                    }
                seen[key]["order_count"] += 1
            return {"ok": True, "data": list(seen.values())}
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
                        if (r.get("goods_name") or "").split("·")[0].strip() == kiln]
            if not rows:
                return {"ok": False, "error": "没有可导出的订单"}

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
