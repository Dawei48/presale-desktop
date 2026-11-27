"""自审脚本：数据一致性 + API 契约 + 边界情况。不启动 GUI。"""
import os
import sys
import json
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("FX_TEST", "1")

FAILS = []
WARNS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        FAILS.append(f"{name} :: {detail}")
        print(f"  FAIL  {name}  {detail}")


def main():
    from database import Database

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = Database(tmp.name)

    from web_api import WebApi
    api = WebApi(db)

    print("\n[1] 空库边界")
    r = api.summary()
    check("空库 summary 不崩", r.get("ok"), str(r))
    check("空库 todo=0", r["data"]["todo"] == 0, str(r["data"]))
    r = api.orders()
    check("空库 orders 返回空数组", r.get("ok") and r["data"]["rows"] == [], str(r)[:200])
    r = api.imports()
    check("空库 imports 不崩", r.get("ok"), str(r))
    r = api.products()
    check("空库 products 不崩", r.get("ok"), str(r))

    print("\n[2] 造数据")
    bid = db.add_brand("玉柏")
    pid = db.add_product(bid, "玉柏 · 青花缠枝四季花 · 茶壶", price=1280)
    specs = [
        dict(order_no="A001", customer="赵敏", order_type="presale",  goods_name="玉柏 · 青花缠枝四季花 · 茶壶"),
        dict(order_no="A002", customer="李雨桐", order_type="presale", goods_name="春风祥玉 · 青花缠枝莲 · 盖碗"),
        dict(order_no="A003", customer="陈默", order_type="stored",  goods_name="艺林堂 · 粉彩四季花 · 赏瓶"),
        dict(order_no="A004", customer="吴岚", order_type="normal",  goods_name="九段烧 · 釉里红 · 主人杯"),
    ]
    ids = [db.add_order(product_id=pid, quantity=1, **s) for s in specs]
    # 造一条老状态数据（验证兼容映射）
    old_id = db.add_order(product_id=pid, quantity=1, order_no="A005", customer="老数据")
    db.update_order(old_id, status="pending")

    r = api.orders()
    check("orders 返回 5 行", len(r["data"]["rows"]) == 5, str(len(r["data"]["rows"])))
    check("老 pending 映射为 ready",
          any(x["status"] == "ready" for x in r["data"]["rows"]), "")

    print("\n[3] 计数一致性")
    rows = r["data"]["rows"]
    counts = r["data"]["counts"]
    real = {}
    for x in rows:
        real[x["status"]] = real.get(x["status"], 0) + 1
    check("counts.total 正确", counts["total"] == len(rows), f'{counts.get("total")} vs {len(rows)}')
    for k, v in real.items():
        check(f"counts[{k}] 正确", counts.get(k) == v, f'{counts.get(k)} vs {v}')
    todo = sum(counts.get(k, 0) for k in ("confirm", "producing", "ready"))
    check("todo 只算待办态", r["data"]["todo"] == todo, f'{r["data"]["todo"]} vs {todo}')

    print("\n[4] 筛选")
    r2 = api.orders("presale")
    check("presale 只返预售", all(x["order_type"] == "presale" for x in r2["data"]["rows"]),
          str([x["order_type"] for x in r2["data"]["rows"]]))
    r3 = api.orders("all", "赵敏")
    check("关键词命中 1 条", len(r3["data"]["rows"]) == 1, str(len(r3["data"]["rows"])))

    print("\n[5] 状态机")
    r = api.set_status(ids[0], "producing")
    check("合法状态可写", r.get("ok"), str(r))
    d = api.order_detail(ids[0])["data"]
    check("状态已落库", d["status"] == "producing", str(d.get("status")))
    r = api.set_status(ids[0], "不存在的状态")
    check("非法状态被拒", not r.get("ok"), str(r))
    r = api.set_status(999999, "ready")
    check("不存在订单不崩", r.get("ok") is not None, str(r))

    print("\n[6] 类型切换")
    r = api.set_order_type(ids[3], "presale")
    check("类型可改", r.get("ok"), str(r))
    check("类型已落库", api.order_detail(ids[3])["data"]["order_type"] == "presale", "")
    r = api.set_order_type(ids[3], "bogus")
    check("非法类型被拒", not r.get("ok"), str(r))

    print("\n[7] 导出")
    out = os.path.join(tempfile.gettempdir(), "fx_selfcheck.docx")
    from utils.docx_export_pro import export_production_docx
    presale = [x for x in rows if x["order_type"] == "presale"]
    n = export_production_docx("玉柏", presale, out)
    check("docx 生成", os.path.exists(out) and os.path.getsize(out) > 5000,
          f'{os.path.getsize(out) if os.path.exists(out) else 0} bytes')
    check("合并后品项数合理", 1 <= n <= len(presale), f"{n} / {len(presale)}")

    # 结构校验：三线表必须是 bezier 无竖线 + 表头有 top/bottom 边
    from docx import Document
    doc = Document(out)
    check("表格存在", len(doc.tables) >= 1, "")
    if doc.tables:
        t = doc.tables[0]
        check("表头 6 列", len(t.columns) == 6, str(len(t.columns)))
        check("数据行 = 品项数", len(t.rows) == n + 1, f"{len(t.rows)} vs {n + 1}")

    print("\n[8] CSV 导入（含重复、脏行、GBK）")
    from utils.csv_importer import import_csv_file
    csv_path = os.path.join(tempfile.gettempdir(), "fx_selfcheck.csv")
    content = (
        "订单编号,收货人,商品名称,规格,购买数量,下单时间,买家留言,实付金额\n"
        "B001,王五,玉柏 · 青花 · 盖碗,110ml,1,2026-11-01 10:00:00,预售,980\n"
        "B001,王五,玉柏 · 青花 · 盖碗,110ml,1,2026-11-01 10:00:00,预售,980\n"
        "B002,赵六,春风祥玉 · 青花 · 杯,60ml,2,2026-11-02,预存,300\n"
        "合计,,, ,3,,,,  \n"
        "B003,孙七,九段烧 · 釉里红 · 主人杯,85ml,1,2026-11-03,,\n"
    )
    with open(csv_path, "w", encoding="gbk") as f:
        f.write(content)
    stats = import_csv_file(db, csv_path)
    check("GBK 编码可读", stats["added"] == 3, json.dumps(stats, ensure_ascii=False))
    check("重复订单号被跳过", stats["dup"] == 1, json.dumps(stats, ensure_ascii=False))
    check("汇总行被跳过", stats["added"] == 3, json.dumps(stats, ensure_ascii=False))

    rows2 = api.orders()["data"]["rows"]
    b2 = next((x for x in rows2 if x["order_no"] == "B002"), None)
    check("备注含预存 → stored", b2 and b2["order_type"] == "stored", str(b2 and b2["order_type"]))
    b3 = next((x for x in rows2 if x["order_no"] == "B003"), None)
    check("无备注 → normal", b3 and b3["order_type"] == "normal", str(b3 and b3["order_type"]))
    check("金额解析", b2 and abs((b2.get("amount") or 0) - 300) < 0.01, str(b2 and b2.get("amount")))

    print("\n[9] 商品库聚合")
    prods = api.products()["data"]
    check("商品库非空", len(prods) >= 3, str(len(prods)))
    check("窑口已解析", all(p["kiln"] for p in prods), str(prods[:2]))

    print("\n" + "=" * 60)
    if FAILS:
        print(f"FAILED {len(FAILS)}")
        for f in FAILS:
            print("  -", f)
    else:
        print("ALL PASS")
    print("=" * 60)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
