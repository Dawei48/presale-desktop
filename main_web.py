"""
放心预 v2 — pywebview 启动器

启动顺序不能动：
1. 先设 DPI awareness（否则 125%/150% 缩放下整屏文字发虚）
2. 再建窗口
3. start() 之后才能操作系统标题栏
"""
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
import sys
import traceback

import webview

from config import BASE_DIR, _find_resource, USE_CLOUD
from web_api import WebApi


def get_database():
    """云端可用就用云端，失败回落本地 SQLite，并把原因写进日志。"""
    if USE_CLOUD:
        try:
            from database_cloud import Database as CloudDB
            db = CloudDB()
            db.has_users()
            print("云端数据库已连接")
            return db, None
        except Exception as e:
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            print("云端连接失败，回落本地：", err)
            try:
                with open(os.path.join(BASE_DIR, "cloud_error.log"), "w", encoding="utf-8") as f:
                    f.write(err)
            except Exception:
                pass
            from database import Database as LocalDB
            return LocalDB(), err
    from database import Database as LocalDB
    return LocalDB(), None


def apply_dark_titlebar(window, theme="dark"):
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        dwm = ctypes.windll.dwmapi
        hwnd = user32.FindWindowW(None, "放心预")
        if not hwnd:
            return
        v = ctypes.c_int(1 if theme != "light" else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v), 4)
        caption, border = (0x00110F0E, 0x00201F1E) if theme != "light" else (0x00FAF9F7, 0x00E6E3DE)
        c = ctypes.c_int(caption)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c), 4)
        b = ctypes.c_int(border)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(b), 4)
    except Exception:
        pass


def backup_local_db():
    """本地模式的命根子只有一个 .db 文件，每天启动时先备份一份，留最近 7 天。
    用 sqlite3 的 backup API，而不是 copy2 —— WAL 模式下直接复制文件可能拿到半截数据。"""
    import glob
    import sqlite3
    from datetime import datetime
    from config import DB_PATH, DATA_DIR

    if not os.path.exists(DB_PATH):
        return
    bdir = os.path.join(DATA_DIR, "backup")
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, f"presale_{datetime.now():%Y%m%d}.db")
    if os.path.exists(dest):
        return
    try:
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        old = sorted(glob.glob(os.path.join(bdir, "presale_*.db")))
        for f in old[:-7]:
            try:
                os.remove(f)
            except OSError:
                pass
    except Exception as e:
        print("备份失败（不影响使用）：", e)


def launch():
    db, cloud_err = get_database()
    if cloud_err is None:
        backup_local_db()

    index = _find_resource("web/index.html")
    if not os.path.exists(index):
        print("找不到 web/index.html：", index)
        # 开发期：源码目录
        dev = os.path.join(BASE_DIR, "web", "index.html")
        if os.path.exists(dev):
            index = dev

    saved_theme = "dark"
    try:
        import json
        sp = os.path.join(BASE_DIR, "data", "settings.json")
        if os.path.exists(sp):
            with open(sp, encoding="utf-8") as f:
                saved_theme = json.load(f).get("theme", "dark")
    except Exception:
        pass

    api = WebApi(db)

    window = webview.create_window(
        "放心预",
        index,
        width=1400,
        height=900,
        min_size=(1080, 700),
        background_color="#FAF9F7" if saved_theme == "light" else "#0F0F0F",
        js_api=api,
    )
    api.window = window

    def on_shown():
        apply_dark_titlebar(window, saved_theme)

    window.events.shown += on_shown

    webview.start(debug=("--debug" in sys.argv), private_mode=False)


if __name__ == "__main__":
    launch()
