"""
预售管理系统 - Supabase REST API 直连版
不依赖 supabase-py 库，纯 HTTP 请求，PyInstaller 打包零问题
"""
import hashlib
import os
import uuid
import json
import urllib.request
import urllib.parse
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

STORAGE_BUCKET = "product-images"
REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"


def _api(table, method="GET", data=None, filters=None, count=False):
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
                # 特殊操作: ilike, in_, eq 等
                for op, val in v.items():
                    if op == "ilike":
                        query.append(f"{k}=ilike.%{val}%")
                    elif op == "eq":
                        query.append(f"{k}=eq.{val}")
                    elif op == "in":
                        query.append(f"{k}=in.({','.join(val)})")
            else:
                query.append(f"{k}=eq.{v}")
    if query:
        url += "?" + "&".join(query)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = resp.read().decode()
        result = json.loads(result) if result else []
        if count:
            total = resp.headers.get("content-range", "")
            # format: 0-9/15
            if "/" in total:
                result = {"data": result, "count": int(total.split("/")[1])}
            else:
                result = {"data": result, "count": 0}
        return result


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
        result = []
        for b in rows:
            pc = _api("products", filters={"brand_id": b["id"]}, count=True)
            b["product_count"] = pc["count"]
            result.append(b)
        return result

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
        # 补 brand_name
        for p in rows:
            if p.get("brand_id"):
                b = self.get_brand(p["brand_id"])
                p["brand_name"] = b["name"] if b else ""
            else:
                p["brand_name"] = ""
        return rows

    def search_products(self, keyword):
        rows = _api("products")
        results = []
        kw = keyword.lower()
        for p in rows:
            if kw in (p.get("name", "") + p.get("notes", "")).lower():
                b = self.get_brand(p["brand_id"]) if p.get("brand_id") else None
                p["brand_name"] = b["name"] if b else ""
                results.append(p)
        return results

    def get_product(self, product_id):
        rows = _api("products", filters={"id": product_id})
        if rows:
            p = rows[0]
            b = self.get_brand(p["brand_id"]) if p.get("brand_id") else None
            p["brand_name"] = b["name"] if b else ""
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
        rows = _api("orders", filters=filters)

        # 补关联数据
        results = []
        for o in rows:
            prod = self.get_product(o["product_id"]) if o.get("product_id") else {}
            o["product_name"] = prod.get("name", "") if prod else ""
            o["product_price"] = prod.get("price", 0) if prod else 0
            o["product_image_path"] = prod.get("image_path", "") if prod else ""
            o["brand_name"] = prod.get("brand_name", "") if prod else ""
            results.append(o)

        # 品牌筛选
        if brand_id:
            results = [o for o in results if o.get("brand_name") and self.get_brand(
                self.get_product(o["product_id"])["brand_id"]
            ) and self.get_product(o["product_id"])["brand_id"] == brand_id]

        # 关键词筛选
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
            prod = self.get_product(o["product_id"]) if o.get("product_id") else {}
            o["product_name"] = prod.get("name", "") if prod else ""
            b = self.get_brand(prod["brand_id"]) if prod and prod.get("brand_id") else None
            o["brand_name"] = b["name"] if b else ""
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
        brands = _api("brands", count=True)["count"]
        products = _api("products", count=True)["count"]
        orders = _api("orders", count=True)["count"]
        pending = _api("orders", filters={"status": "pending"}, count=True)["count"]
        shipped = _api("orders", filters={"status": "shipped"}, count=True)["count"]
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
        return _api("activity_log")

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
