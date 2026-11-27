"""e2e.py — 真机端到端：在 pywebview 窗口里真点真改，再回数据库核对。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import webview
from config import _find_resource
from database import Database
from web_api import WebApi

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)

db = Database()
api = WebApi(db)
window = webview.create_window("放心预", _find_resource("web/index.html"),
                               width=1400, height=900, js_api=api)
api.window = window

RESULTS = []


def chk(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} · {name}" + (f"  ← {detail}" if not ok else ""))


def js(expr):
    return window.evaluate_js(expr)


def shot(name):
    # 用 Windows 截图拿到真实窗口像素
    try:
        from PIL import ImageGrab
        import ctypes.wintypes as wt
        u = ctypes.windll.user32
        h = u.FindWindowW(None, "放心预")
        u.SetWindowPos(h, -1, 40, 20, 1400, 900, 0x0040)
        u.SetForegroundWindow(h)
        time.sleep(0.8)
        r = wt.RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom)).save(
            os.path.join(OUT, name))
        return True
    except Exception as e:
        print("截图失败:", e)
        return False


def run():
    time.sleep(2.5)   # 等 waitBridge 轮询完成

    # 1. 同步状态
    chk("桥接已同步", js("(document.getElementById('sync-state')||{}).textContent") == "已同步",
        js("(document.getElementById('sync-state')||{}).textContent"))

    # 2. 真实数据行数（库里 4 单）
    n = js("document.querySelectorAll('#list .row').length")
    chk("渲染 4 行真实订单", n == 4, f"实际 {n} 行")

    # 3. 副标题包含真实计数
    sub = js("document.getElementById('page-sub').textContent")
    chk("副标题 4 单", "4 单" in sub, sub)

    # 4. 筛选：预售只有 1 单
    js("document.querySelector('[data-filter=\"presale\"]').click()")
    time.sleep(0.7)
    n = js("document.querySelectorAll('#list .row').length")
    chk("筛选预售 = 1 单", n == 1, f"{n} 行")

    # 5. 筛选：待确认延发 1 单
    js("document.querySelector('[data-filter=\"confirm\"]').click()")
    time.sleep(0.7)
    n = js("document.querySelectorAll('#list .row').length")
    chk("筛选待确认延发 = 1 单", n == 1, f"{n} 行")

    # 6. 真点一次「标记已同意」→ 状态应变 producing，并落库
    before = db.get_orders()
    conf = [o for o in before if o.get("status") == "confirm"]
    chk("库里有 1 单待确认", len(conf) == 1, str(len(conf)))
    if conf:
        oid = conf[0]["id"]
        js("""(() => {
          const b = [...document.querySelectorAll('#list .row button')]
            .find(x => x.textContent.includes('标记已同意'));
          if (b) b.click();
        })()""")
        time.sleep(1.2)
        after = [o for o in db.get_orders() if o["id"] == oid][0]
        chk("点击后落库为 producing", after.get("status") == "producing",
            f"实际 {after.get('status')}")

    # 7. 窑口页
    js("document.querySelector('[data-page=\"kilns\"]').click()")
    time.sleep(1.0)
    title = js("document.getElementById('page-title').textContent")
    chk("切到窑口页", title == "窑口", title)
    kiln_cards = js("document.querySelectorAll('#list .card, #list .kiln').length")
    print("   窑口卡片数:", kiln_cards)
    shot("e2e_kilns.png")

    # 8. 回订单页 + 主截图
    js("document.querySelector('[data-page=\"orders\"]').click()")
    time.sleep(0.9)
    js("document.querySelector('[data-filter=\"all\"]').click()")
    time.sleep(0.7)
    shot("e2e_orders.png")

    # 9. 设置页能否读到数据目录
    js("document.querySelector('[data-page=\"settings\"]').click()")
    time.sleep(1.0)
    body = js("document.getElementById('list').innerText")
    chk("设置页显示本地存储", "本地存储" in body, body[:60])
    shot("e2e_settings.png")

    # 10. 深浅主题
    js("document.querySelector('[data-page=\"orders\"]').click()")
    time.sleep(0.6)
    js("document.querySelector('[data-set-theme=\"light\"]').click()")
    time.sleep(0.7)
    chk("切浅色", js("document.documentElement.getAttribute('data-theme')") == "light")
    shot("e2e_light.png")
    js("document.querySelector('[data-set-theme=\"dark\"]').click()")
    time.sleep(0.6)
    chk("切深色", js("document.documentElement.getAttribute('data-theme')") == "dark")

    print("\n" + "=" * 60)
    fails = [r for r in RESULTS if not r[1]]
    print(f"{len(RESULTS)} 项 · PASS {len(RESULTS)-len(fails)} · FAIL {len(fails)}")
    for n_, _ok, d in fails:
        print("  ✗", n_, d)
    print("=" * 60)


window.events.loaded += run
webview.start()
