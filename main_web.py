"""
放心预 v2 — pywebview 启动器

启动顺序不能动：
1. 先设 DPI awareness（否则 125%/150% 缩放下整屏文字发虚）
2. 再建窗口
3. start() 之后才能碰系统标题栏
"""
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import json
import os
import sys

import webview

from config import DB_PATH, DATA_DIR, _find_resource
from database import Database
from web_api import WebApi


def apply_dark_titlebar(theme="dark"):
    """让 Windows 原生标题栏跟着主题走。失败就当作没这回事，不能影响启动。"""
    try:
        user32 = ctypes.windll.user32
        dwm = ctypes.windll.dwmapi
        hwnd = user32.FindWindowW(None, "放心预")
        if not hwnd:
            return
        dark = ctypes.c_int(1 if theme != "light" else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)      # immersive dark mode
        caption, border = ((0x00110F0E, 0x00201F1E) if theme != "light"
                           else (0x00FAF9F7, 0x00E6E3DE))
        c = ctypes.c_int(caption)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c), 4)         # caption color
        b = ctypes.c_int(border)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(b), 4)         # border color
    except Exception:
        pass


def backup_local_db():
    """本地模式的命根子只有一个 .db 文件，每天启动时先备份一份，留最近 7 天。

    用 sqlite3 的 backup API 而不是 shutil.copy2：WAL 模式下直接复制文件
    可能拿到写到一半的状态，备份出来是坏的。
    """
    import glob
    import sqlite3
    from datetime import datetime

    if not os.path.exists(DB_PATH):
        return
    bdir = os.path.join(DATA_DIR, "backup")
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, f"presale_{datetime.now():%Y%m%d}.db")
    if os.path.exists(dest):        # 今天已经备过
        return
    try:
        with sqlite3.connect(DB_PATH) as src, sqlite3.connect(dest) as dst:
            src.backup(dst)
        for f in sorted(glob.glob(os.path.join(bdir, "presale_*.db")))[:-7]:
            try:
                os.remove(f)
            except OSError:
                pass
    except Exception as e:
        print("备份失败（不影响使用）：", e)


def load_saved_theme():
    sp = os.path.join(DATA_DIR, "settings.json")
    try:
        with open(sp, encoding="utf-8") as f:
            return json.load(f).get("theme", "dark")
    except (OSError, ValueError):
        return "dark"


def launch():
    backup_local_db()
    db = Database()

    index = _find_resource("web/index.html")
    if not os.path.exists(index):
        print("找不到 web/index.html：", index)
        return

    theme = load_saved_theme()
    api = WebApi(db)
    window = webview.create_window(
        "放心预",
        index,
        width=1400,
        height=900,
        min_size=(1080, 700),
        background_color="#FAF9F7" if theme == "light" else "#0F0F0F",
        js_api=api,
    )
    api.window = window
    window.events.shown += lambda: apply_dark_titlebar(theme)
    webview.start(debug=("--debug" in sys.argv), private_mode=False)


if __name__ == "__main__":
    launch()
