"""
预售管理系统 - Supabase REST API 直连版 (Optimized)
不依赖 supabase-py 库，纯 HTTP 请求，PyInstaller 打包零问题
性能优化：消除 N+1 查询，批量获取关联数据后在 Python 中 join
"""
import hashlib
import os
import uuid
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

STORAGE_BUCKET = "product-images"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"


def _api(table, method="GET", data=None, filters=None, count=False, order=None, limit=None):
    """直接调 Supabase PostgREST API"""
    url = f"{REST_URL}/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation" if method in ("POST", "PATCH", "DELETE") else "",
    }
    if count:
        headers["Prefer"] = "count=exact"

    query = []
    if filters:
        for k, v in filters.items():
            if isinstance(v, dict):
                for op, val in v.items():
                    if op == "ilike":
                        query.append(f"{k}=ilike.{urllib.parse.quote(f'%{val}%')}")
                    elif op == "eq":
                        query.append(f"{k}=eq.{val}")
                    elif op == "in":
                        query.append(f"{k}=in.({','.join(str(x) for x in val)})")
                    elif op == "neq":
                        query.append(f"{k}=neq.{val}")
                    elif op == "not.is":
                        query.append(f"{k}=not.is.{val}")
            else:
                query.append(f"{k}=eq.{v}")
    if order:
        # order="created_at.desc" or "name.asc"
        query.append(f"order={order}")
    if limit:
        query.append(f"limit={limit}")

    if query:
        url += "?" + "&".join(query)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = resp.read().decode()
        result = json.loads(result) if result else []
        if count:
            total = resp.headers.get("content-range", "")
            if "/" in total:
                result = {"data": result, "count": int(total.split("/")[1])}
            else:
                result = {"data": result, "count": 0}
        return result


def _batch_products_for_brands(brand_ids):
    """Fetch all products matching the given brand_ids in one call. Returns dict: brand_id -> count"""
    if not brand_ids:
        return {}
    brand_ids = list(set(brand_ids))
    # PostgREST 'in' filter
    rows = _api("products", filters={"brand_id": {"in": [str(b) for b in brand_ids]}})
    counts = {}
    for p in rows:
        bid = p.get("brand_id")
        if bid:
            counts[bid] = counts.get(bid, 0) + 1
    return counts


def _batch_products_by_ids(product_ids):
    """Fetch all products with matching ids in one call. Returns dict: product_id -> product"""
    if not product_ids:
        return {}
    product_ids = list(set(str(pid) for pid in product_ids if pid))
    if not product_ids:
        return {}
    rows = _api("products", filters={"id": {"in": product_ids}})
    return {str(p["id"]): p for p in rows}


def _batch_brands_by_ids(brand_ids):
    """Fetch all brands with matching ids in one call. Returns dict: brand_id -> brand"""
    if not brand_ids:
        return {}
    brand_ids = list(set(str(bid) for bid in brand_ids if bid))
    if not brand_ids:
        return {}
    rows = _api("brands", filters={"id": {"in": brand_ids}})
    return {str(b["id"]): b for b in rows}


class Database:
    def __init__(self):
        # 测试连接
        _api("users", count=True)

    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed

    # ════════════════════════════════════════════
    #  用户
    # ════════════════════════════════════════════
    def has_users(self):
        r = _api("users", count=True)
        return r["count"] > 0

    def login(self, username, password):
        rows = _api("users", filters={"username": username})
        if rows:
            user = rows[0]
            if self.verify(password, user["password"]):
                return user
        return None

    def get_users(self):
        return _api("users", filters={})

    def add_user(self, username, password, display_name, role="member"):
        _api("users", method="POST", data={
            "username": username,
            "password": self._hash(password),
            "display_name": display_name,
            "role": role,
        })

    def update_user(self, user_id, display_name=None, role=None, password=None):
        fields = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if role is not None:
            fields["role"] = role
        if password is not None:
            fields["password"] = self._hash(password)
        if fields:
            _api("users", method="PATCH", data=fields, filters={"id": user_id})

    def delete_user(self, user_id):
        r = _api("users", filters={"role": "admin"}, count=True)
        if r["count"] <= 1:
            user = _api("users", filters={"id": user_id})
            if user and user[0]["role"] == "admin":
                raise ValueError("不能删除最后一个管理员")
        _api("users", method="DELETE", filters={"id": user_id})

    def user_exists(self, username):
        r = _api("users", filters={"username": username}, count=True)
        return r["count"] > 0

    # ════════════════════════════════════════════
    #  品牌
    # ════════════════════════════════════════════
    def get_brands(self):
        rows = _api("brands")
        if not rows:
            return []
        brand_ids = [b["id"] for b in rows]
        # 并行获取品牌和产品计数
        product_counts = _batch_products_for_brands(brand_ids)
        for b in rows:
            b["product_count"] = product_counts.get(b["id"], 0)
        return rows

    def get_brand(self, brand_id):
        rows = _api("brands", filters={"id": brand_id})
        return rows[0] if rows else None

    def add_brand(self, name):
        r = _api("brands", method="POST", data={"name": name})
        return r[0]["id"] if r else None

    def update_brand(self, brand_id, name):
        _api("brands", method="PATCH", data={"name": name}, filters={"id": brand_id})

    def delete_brand(self, brand_id):
        _api("brands", method="DELETE", filters={"id": brand_id})

    # ════════════════════════════════════════════
    #  产品
    # ════════════════════════════════════════════
    def get_products(self, brand_id=None):
        filters = {}
        if brand_id:
            filters["brand_id"] = brand_id
        rows = _api("products", filters=filters)
        # Batch-fetch all brands needed
        brand_ids = list(set(p.get("brand_id") for p in rows if p.get("brand_id")))
        brands_map = _batch_brands_by_ids(brand_ids)
        for p in rows:
            bid = p.get("brand_id")
            if bid:
                b = brands_map.get(str(bid))
                p["brand_name"] = b["name"] if b else ""
            else:
                p["brand_name"] = ""
        return rows

    def search_products(self, keyword):
        # Use PostgREST ilike filter on server side for name and notes
        rows = _api("products", filters={"name": {"ilike": keyword}})
        # Also search in notes
        rows2 = _api("products", filters={"notes": {"ilike": keyword}})
        # Merge by id, dedup
        seen = set()
        merged = []
        for p in rows + rows2:
            pid = p.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                merged.append(p)
        # Batch-fetch brands
        brand_ids = list(set(p.get("brand_id") for p in merged if p.get("brand_id")))
        brands_map = _batch_brands_by_ids(brand_ids)
        for p in merged:
            bid = p.get("brand_id")
            if bid:
                b = brands_map.get(str(bid))
                p["brand_name"] = b["name"] if b else ""
            else:
                p["brand_name"] = ""
        return merged

    def get_product(self, product_id):
        rows = _api("products", filters={"id": product_id})
        if rows:
            p = rows[0]
            if p.get("brand_id"):
                b = _batch_brands_by_ids([p["brand_id"]]).get(str(p["brand_id"]))
                p["brand_name"] = b["name"] if b else ""
            else:
                p["brand_name"] = ""
            return p
        return None

    def add_product(self, brand_id, name, price=0, notes="", image_path=""):
        r = _api("products", method="POST", data={
            "brand_id": brand_id,
            "name": name,
            "price": price,
            "notes": notes,
            "image_path": image_path,
        })
        return r[0]["id"] if r else None

    def update_product(self, product_id, **kwargs):
        allowed = {"brand_id", "name", "price", "notes", "image_path"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _api("products", method="PATCH", data=fields, filters={"id": product_id})

    def delete_product(self, product_id):
        _api("products", method="DELETE", filters={"id": product_id})

    # ════════════════════════════════════════════
    #  订单
    # ════════════════════════════════════════════
    def get_orders(self, product_id=None, brand_id=None, status=None, keyword=None):
        filters = {}
        if product_id:
            filters["product_id"] = product_id
        if status:
            filters["status"] = status

        # Fetch filtered orders in ONE call (or all if no filters)
        if filters or keyword:
            rows = _api("orders", filters=filters)
        else:
            rows = _api("orders")

        if not rows:
            return []

        # Batch-fetch all products for these orders in ONE call
        product_ids = list(set(o.get("product_id") for o in rows if o.get("product_id")))
        products_map = _batch_products_by_ids(product_ids)

        # Batch-fetch all brands needed for those products
        brand_ids = list(set(p.get("brand_id") for p in products_map.values() if p.get("brand_id")))
        brands_map = _batch_brands_by_ids(brand_ids)

        # Join in Python
        results = []
        for o in rows:
            pid = str(o.get("product_id", ""))
            prod = products_map.get(pid, {})
            o["product_name"] = prod.get("name", "")
            o["product_price"] = prod.get("price", 0)
            o["product_image_path"] = prod.get("image_path", "")
            bid = str(prod.get("brand_id", ""))
            brand = brands_map.get(bid, {})
            o["brand_name"] = brand.get("name", "")
            results.append(o)

        # Brand filter (server-side would require joins, do in Python after batch fetch)
        if brand_id:
            results = [o for o in results if str(
                products_map.get(str(o.get("product_id", "")), {}).get("brand_id", "")
            ) == str(brand_id)]

        # Keyword filter
        if keyword:
            kw = keyword.lower()
            results = [o for o in results if kw in (
                o.get("order_no", "") + o.get("customer", "") +
                o.get("notes", "") + o.get("product_name", "")
            ).lower()]

        return results

    def get_order(self, order_id):
        rows = _api("orders", filters={"id": order_id})
        if rows:
            o = rows[0]
            pid = o.get("product_id")
            if pid:
                products_map = _batch_products_by_ids([pid])
                prod = products_map.get(str(pid), {})
                o["product_name"] = prod.get("name", "")
                bid = prod.get("brand_id")
                if bid:
                    brands_map = _batch_brands_by_ids([bid])
                    brand = brands_map.get(str(bid), {})
                    o["brand_name"] = brand.get("name", "")
                else:
                    o["brand_name"] = ""
            else:
                o["product_name"] = ""
                o["brand_name"] = ""
            return o
        return None

    def add_order(self, product_id, quantity=1, order_no="", customer="", notes="", created_at=None):
        data = {
            "product_id": product_id,
            "quantity": quantity,
            "order_no": order_no,
            "customer": customer,
            "notes": notes,
        }
        if created_at:
            data["created_at"] = created_at
        r = _api("orders", method="POST", data=data)
        return r[0]["id"] if r else None

    def update_order(self, order_id, **kwargs):
        allowed = {"product_id", "order_no", "customer", "quantity", "notes", "status", "created_at"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _api("orders", method="PATCH", data=fields, filters={"id": order_id})

    def delete_order(self, order_id):
        _api("orders", method="DELETE", filters={"id": order_id})

    # ════════════════════════════════════════════
    #  统计
    # ════════════════════════════════════════════
    def get_stats(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            f1 = pool.submit(lambda: _api("brands", count=True)["count"])
            f2 = pool.submit(lambda: _api("products", count=True)["count"])
            f3 = pool.submit(lambda: _api("orders", count=True)["count"])
            f4 = pool.submit(lambda: _api("orders", filters={"status": "pending"}, count=True)["count"])
            f5 = pool.submit(lambda: _api("orders", filters={"status": "shipped"}, count=True)["count"])
            brands, products, orders, pending, shipped = f1.result(), f2.result(), f3.result(), f4.result(), f5.result()
        return {
            "brands": brands, "products": products,
            "orders": orders, "pending": pending, "shipped": shipped,
        }

    # ════════════════════════════════════════════
    #  日志
    # ════════════════════════════════════════════
    def log(self, action, details="", user_id=None, username=""):
        _api("activity_log", method="POST", data={
            "action": action,
            "details": details,
            "user_id": user_id,
            "username": username,
        })

    def get_logs(self, limit=50):
        return _api("activity_log", order="created_at.desc", limit=limit)

    # ════════════════════════════════════════════
    #  图片上传
    # ════════════════════════════════════════════
    def upload_image(self, local_path: str) -> str:
        """上传图片到 Supabase Storage"""
        ext = os.path.splitext(local_path)[1].lower()
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"

        url = f"{STORAGE_URL}/object/{STORAGE_BUCKET}/{filename}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": mime,
        }
        with open(local_path, "rb") as f:
            req = urllib.request.Request(url, data=f, headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=30)

        return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"

    def delete_image(self, url: str):
        if not url or "product-images" not in url:
            return
        filename = url.split("/")[-1]
        url = f"{STORAGE_URL}/object/{STORAGE_BUCKET}/{filename}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

print('DONE')
