"""audit.py — 多维度自审。不启动 GUI，跑完给出 PASS/FAIL 清单。"""
import os
import sys
import json
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS = []


def rec(dim, name, ok, detail=""):
    RESULTS.append((dim, name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {dim} · {name}" + (f"  ← {detail}" if not ok and detail else ""))


def make_db(with_data=False):
    from database import Database
    t = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    t.close()
    db = Database(t.name)
    if with_data:
        bid = db.add_brand("玉柏")
        for i, (name, spec, qty, notes, amount, otype, status) in enumerate([
            ("玉柏 · 青花缠枝莲 · 盖碗", "110ml", 1, "", 980, "normal", "ready"),
            ("玉柏 · 青花 · 压手杯", "90ml", 2, "预售 加急", 1360, "presale", "confirm"),
            ("玉柏 · 釉里红 · 主人杯", "85ml", 3, "", 2340, "normal", "ready"),
            ("艺林堂 · 粉彩四季花 · 赏瓶", "32cm", 1, "预存 消费券", 3600, "stored", "stored"),
        ]):
            pid = db.add_product(bid, name)
            oid = db.add_order(product_id=pid, quantity=qty, order_no=f"A{i}",
                               customer=f"客户{i}", goods_name=name, spec=spec,
                               notes=notes, amount=amount, order_type=otype,
                               receiver_name=f"客户{i}", receiver_phone="13800000000",
                               receiver_addr="北京市")
            db.update_order(oid, status=status)
    return db


# ══════════════════════════════════════════════════════════
# 维度 1：静态检查
# ══════════════════════════════════════════════════════════
def dim_static():
    import py_compile
    for f in ("main_web.py", "web_api.py", "config.py",
              "utils/csv_importer.py", "utils/docx_export_slip.py",
              "utils/image_fetcher.py", "utils/ai_parser.py", "database.py"):
        try:
            py_compile.compile(f, doraise=True)
            rec("静态", f"{f} 语法", True)
        except Exception as e:
            rec("静态", f"{f} 语法", False, str(e)[:120])

    # 前端引用的文件都要存在
    base = os.path.dirname(os.path.abspath(__file__))
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    import re
    for m in re.findall(r'(?:src|href)="([^"]+)"', html):
        if m.startswith("http") or m.startswith("#"):
            continue
        p = os.path.join(base, "web", m)
        rec("静态", f"资源存在 {m}", os.path.exists(p), p)

    # ── 桥接回归：这个 bug 骗过一次「界面正常」，必须焊死 ──
    import re as _re
    api_js = open(os.path.join(base, "web", "js", "api.js"), encoding="utf-8").read()
    # 剥掉注释再判断，否则注释里那句「不能写成 Promise.race」会自己触发误报
    api_code = _re.sub(r"/\*.*?\*/", "", api_js, flags=_re.S)
    api_code = _re.sub(r"^\s*//.*$", "", api_code, flags=_re.M)
    rec("桥接", "没有用 Promise.race 包 pywebview 返回值",
        "Promise.race" not in api_code,
        "pywebview 的 api 返回自定义 thenable，塞进 race 会永不 settle，"
        "界面就永远停在 mock 假数据上还显示「已同步」")
    rec("桥接", "有超时兜底", "setTimeout" in api_js and "超时" in api_js, "缺超时保护")
    rec("桥接", "有 pywebview 调试出口",
        "window.__app" in open(os.path.join(base, "web", "js", "app.js"),
                               encoding="utf-8").read(),
        "没有 __app 出口就无法从外部验证页面真实状态")

    # app.js 里没有残留的已删页面引用
    js = open(os.path.join(base, "web", "js", "app.js"), encoding="utf-8").read()
    rec("静态", "无 nav-todo 残留", "nav-todo" not in js, "还引用了已删的待办节点")
    rec("静态", "无 page==='todo' 残留", "'todo'" not in js, "还有待办分支")


# ══════════════════════════════════════════════════════════
# 维度 2：API 冒烟（空库 + 有数据）
# ══════════════════════════════════════════════════════════
def dim_api():
    from web_api import WebApi

    db = make_db(False)
    api = WebApi(db)

    empty_calls = [
        ("summary", lambda: api.summary()),
        ("orders", lambda: api.orders()),
        ("kilns", lambda: api.kilns()),
        ("products", lambda: api.products()),
        ("imports", lambda: api.imports()),
        ("get_settings", lambda: api.get_settings()),
    ]
    for name, fn in empty_calls:
        try:
            r = fn()
            rec("API-空库", name, r.get("ok"), json.dumps(r, ensure_ascii=False)[:100])
        except Exception as e:
            rec("API-空库", name, False, f"{type(e).__name__}: {e}")

    db2 = make_db(True)
    api2 = WebApi(db2)
    rows = api2.orders()["data"]["rows"]
    oid = rows[0]["id"]

    calls = [
        ("orders(all)", lambda: api2.orders("all")),
        ("orders(presale)", lambda: api2.orders("presale")),
        ("orders(confirm)", lambda: api2.orders("confirm")),
        ("orders(keyword)", lambda: api2.orders("all", "客户1")),
        ("order_detail", lambda: api2.order_detail(oid)),
        ("set_status", lambda: api2.set_status(oid, "shipped")),
        ("set_status 非法", lambda: api2.set_status(oid, "xxx")),
        ("set_order_type", lambda: api2.set_order_type(oid, "presale")),
        ("save_order 新增", lambda: api2.save_order({"receiver_name": "新人", "goods_name": "测试 · 器"})),
        ("delete_order", lambda: api2.delete_order(oid)),
        ("delete_order 不存在", lambda: api2.delete_order(999999)),
        ("products", lambda: api2.products()),
        ("kilns", lambda: api2.kilns()),
        ("imports", lambda: api2.imports()),
        ("summary", lambda: api2.summary()),
    ]
    for name, fn in calls:
        try:
            r = fn()
            # 非法入参允许 ok=False，但必须返回结构化结果而不是抛异常
            ok = isinstance(r, dict) and "ok" in r
            rec("API-有数据", name, ok, json.dumps(r, ensure_ascii=False)[:100])
        except Exception as e:
            rec("API-有数据", name, False, f"{type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════
# 维度 3：数据一致性
# ══════════════════════════════════════════════════════════
def dim_consistency():
    from web_api import WebApi
    db = make_db(True)
    api = WebApi(db)

    r = api.orders()
    rows, counts = r["data"]["rows"], r["data"]["counts"]
    real = {}
    for x in rows:
        real[x["status"]] = real.get(x["status"], 0) + 1
    rec("一致性", "counts 与明细一致", counts.get("total") == len(rows),
        f'{counts.get("total")} vs {len(rows)}')
    for k, v in real.items():
        rec("一致性", f"counts[{k}]", counts.get(k) == v, f'{counts.get(k)} vs {v}')

    # 窑口聚合的订单数要等于总订单数
    kilns = api.kilns()["data"]
    total_in_kilns = sum(k["orders"] for k in kilns)
    rec("一致性", "窑口订单总数", total_in_kilns == len(rows), f"{total_in_kilns} vs {len(rows)}")

    # 窑口里的待生产件数要等于 confirm+producing 的数量和
    expect_pending = sum(int(x.get("quantity") or 1) for x in rows
                         if x["status"] in ("confirm", "producing"))
    got_pending = sum(k["pending"] for k in kilns)
    rec("一致性", "窑口待生产件数", expect_pending == got_pending, f"{got_pending} vs {expect_pending}")

    # 每个窑口的商品数 > 0
    rec("一致性", "窑口都有商品", all(k["products"] for k in kilns), "有空窑口")


# ══════════════════════════════════════════════════════════
# 维度 4：导入 / 导出
# ══════════════════════════════════════════════════════════
def dim_io():
    from utils.csv_importer import import_csv_file
    from utils.docx_export_slip import export_production_docx

    csv_path = os.path.join(tempfile.gettempdir(), "audit_orders.csv")
    with open(csv_path, "w", encoding="gbk") as f:
        f.write(
            "订单编号,收货人,商品标题,规格,购买数量,下单时间,买家留言,收货电话,收货地址,实付金额\n"
            "X1,张三,春风祥玉 · 青花缠枝莲 · 盖碗,110ml,1,2026-11-27 10:00:00,,138,北京,980\n"
            "X2,李四,玉柏 · 青花 · 压手杯,90ml,2,2026-11-27 11:00:00,预售 加急,139,上海,1360\n"
            "X2,李四,玉柏 · 青花 · 压手杯,90ml,2,2026-11-27 11:00:00,预售 加急,139,上海,1360\n"
            "X3,王五,艺林堂 · 粉彩四季花 · 赏瓶,32cm,1,2026-11-27 12:00:00,预存 消费券,137,广州,3600\n"
            "合计,,,,7,,,,,\n"
        )

    db = make_db(False)
    st = import_csv_file(db, csv_path)
    rec("导入", "GBK 可读 + 汇总行过滤", st["added"] == 3, json.dumps(st, ensure_ascii=False))
    rec("导入", "重复单号跳过", st["dup"] == 1, json.dumps(st, ensure_ascii=False))

    from web_api import WebApi
    api = WebApi(db)
    rows = api.orders()["data"]["rows"]
    by_no = {r["order_no"]: r for r in rows}
    rec("导入", "预售→confirm", by_no.get("X2", {}).get("status") == "confirm",
        str(by_no.get("X2", {}).get("status")))
    rec("导入", "预存→stored", by_no.get("X3", {}).get("status") == "stored",
        str(by_no.get("X3", {}).get("status")))
    rec("导入", "现货→ready", by_no.get("X1", {}).get("status") == "ready",
        str(by_no.get("X1", {}).get("status")))
    rec("导入", "金额入账", abs((by_no.get("X1", {}).get("amount") or 0) - 980) < 0.01, "")

    # 导出
    out = os.path.join(tempfile.gettempdir(), "audit_slip.docx")
    presale = [r for r in rows if r["status"] in ("confirm", "producing")]
    export_production_docx("玉柏", presale, out)
    rec("导出", "文件生成", os.path.exists(out) and os.path.getsize(out) > 5000,
        str(os.path.getsize(out) if os.path.exists(out) else 0))

    from docx import Document
    from docx.oxml.ns import qn
    doc = Document(out)
    t = doc.tables[0]
    heads = [c.text.strip() for c in t.rows[0].cells]
    rec("导出", "列序 图片/名称/数量/价格/备注",
        heads == ["产品图片", "产品名称", "数量", "价格", "备注"], str(heads))
    rec("导出", "无规格列", "规格" not in heads, str(heads))
    rec("导出", "带 logo 图", len(doc.inline_shapes) >= 1, "没有嵌入图")
    shd = t.rows[0].cells[0]._tc.tcPr.find(qn("w:shd"))
    rec("导出", "表头有底色", shd is not None and shd.get(qn("w:fill")) == "2B2724", "")


# ══════════════════════════════════════════════════════════
# 维度 5：文件与打包配置
# ══════════════════════════════════════════════════════════
def dim_packaging():
    base = os.path.dirname(os.path.abspath(__file__))
    for p in ("web/index.html", "web/css/app.css", "web/js/app.js",
              "web/js/api.js", "web/js/mock.js", "web/js/logo.js",
              "assets/logo.png", "assets/logo_mark.png", "assets/icon.ico"):
        full = os.path.join(base, p)
        rec("打包", f"存在 {p}", os.path.exists(full), full)

    from PIL import Image
    ico = Image.open(os.path.join(base, "assets", "icon.ico"))
    sizes = sorted(ico.ico.sizes())
    rec("打包", "ico 多尺寸", len(sizes) >= 5, str(sizes))

    logo_js = open(os.path.join(base, "web", "js", "logo.js"), encoding="utf-8").read()
    rec("打包", "logo base64 已内嵌", "data:image/png;base64," in logo_js, "")

    # 纯本地：不应该再有云端模块或凭据
    from config import DATA_DIR
    rec("打包", "数据目录可写", os.path.isdir(DATA_DIR), DATA_DIR)
    rec("打包", "无云端模块残留",
        not os.path.exists(os.path.join(base, "database_cloud.py")), "database_cloud.py 还在")
    cfg = open(os.path.join(base, "config.py"), encoding="utf-8").read()
    rec("打包", "config 无凭据", "sb_publishable" not in cfg and "SUPABASE_KEY" not in cfg,
        "config.py 里还有 Supabase 凭据")


def main():
    print("=" * 66)
    for fn in (dim_static, dim_api, dim_consistency, dim_io, dim_packaging):
        print(f"\n── {fn.__name__[4:].upper()} ──")
        try:
            fn()
        except Exception:
            traceback.print_exc()
            rec(fn.__name__, "整组崩溃", False, traceback.format_exc()[:200])

    fails = [r for r in RESULTS if not r[2]]
    print("\n" + "=" * 66)
    print(f"共 {len(RESULTS)} 项 · PASS {len(RESULTS) - len(fails)} · FAIL {len(fails)}")
    for d, n, ok, detail in fails:
        print(f"  ✗ {d} · {n}  {detail}")
    print("=" * 66)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
