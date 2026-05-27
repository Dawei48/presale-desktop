"""
预售管理系统 - Supabase 云端数据库层
替换 SQLite，实现多机协作
"""
import hashlib
import os
import uuid
from datetime import datetime
from supabase import create_client, Client

# ── 配置 ──────────────────────────────────────
from config import SUPABASE_URL, SUPABASE_KEY
STORAGE_BUCKET = "product-images"


class Database:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        res = self.client.table("users").select("id").limit(1).execute()
        return len(res.data) > 0

    def login(self, username: str, password: str):
        res = self.client.table("users").select("*").eq("username", username).execute()
        if res.data:
            user = res.data[0]
            if self.verify(password, user["password"]):
                return user
        return None

    def get_users(self):
        res = self.client.table("users").select("id,username,display_name,role,created_at").order("id").execute()
        return res.data

    def add_user(self, username, password, display_name, role="member"):
        self.client.table("users").insert({
            "username": username,
            "password": self._hash(password),
            "display_name": display_name,
            "role": role,
        }).execute()

    def update_user(self, user_id, display_name=None, role=None, password=None):
        fields = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if role is not None:
            fields["role"] = role
        if password is not None:
            fields["password"] = self._hash(password)
        if fields:
            self.client.table("users").update(fields).eq("id", user_id).execute()

    def delete_user(self, user_id):
        # 检查是否是最后一个管理员
        res = self.client.table("users").select("role").eq("role", "admin").execute()
        admin_count = len(res.data)
        user_res = self.client.table("users").select("role").eq("id", user_id).execute()
        if user_res.data and user_res.data[0]["role"] == "admin" and admin_count <= 1:
            raise ValueError("不能删除最后一个管理员")
        self.client.table("users").delete().eq("id", user_id).execute()

    def user_exists(self, username):
        res = self.client.table("users").select("id").eq("username", username).limit(1).execute()
        return len(res.data) > 0

    # ════════════════════════════════════════════
    #  品牌
    # ════════════════════════════════════════════
    def get_brands(self):
        res = self.client.table("brands").select("*").order("created_at", desc=True).execute()
        result = []
        for b in res.data:
            # 查每个品牌的产品数
            pc = self.client.table("products").select("id", count="exact").eq("brand_id", b["id"]).execute()
            b["product_count"] = pc.count or 0
            result.append(b)
        return result

    def get_brand(self, brand_id):
        res = self.client.table("brands").select("*").eq("id", brand_id).execute()
        return res.data[0] if res.data else None

    def add_brand(self, name):
        res = self.client.table("brands").insert({"name": name}).execute()
        return res.data[0]["id"]

    def update_brand(self, brand_id, name):
        self.client.table("brands").update({"name": name}).eq("id", brand_id).execute()

    def delete_brand(self, brand_id):
        self.client.table("brands").delete().eq("id", brand_id).execute()

    # ════════════════════════════════════════════
    #  产品
    # ════════════════════════════════════════════
    def get_products(self, brand_id=None):
        query = self.client.table("products").select("*, brands(name)")
        if brand_id:
            query = query.eq("brand_id", brand_id)
        res = query.order("created_at", desc=True).execute()
        # 展平 brand_name
        for p in res.data:
            if "brands" in p and p["brands"]:
                p["brand_name"] = p["brands"]["name"]
            del p["brands"]
        return res.data

    def search_products(self, keyword):
        # 先按产品名和备注搜
        res = self.client.table("products").select("*, brands(name)").or_(
            f"name.ilike.%{keyword}%,notes.ilike.%{keyword}%"
        ).order("created_at", desc=True).execute()
        # 再按品牌名搜（Supabase不支持跨表or，单独查）
        brand_res = self.client.table("brands").select("id").ilike("name", f"%{keyword}%").execute()
        if brand_res.data:
            brand_ids = [b["id"] for b in brand_res.data]
            for bid in brand_ids:
                extra = self.client.table("products").select("*, brands(name)").eq("brand_id", bid).execute()
                # 去重合并
                existing_ids = {p["id"] for p in res.data}
                for p in extra.data:
                    if p["id"] not in existing_ids:
                        res.data.append(p)
        for p in res.data:
            if "brands" in p and p["brands"]:
                p["brand_name"] = p["brands"]["name"]
            del p["brands"]
        return res.data

    def get_product(self, product_id):
        res = self.client.table("products").select("*, brands(name)").eq("id", product_id).execute()
        if res.data:
            p = res.data[0]
            if "brands" in p and p["brands"]:
                p["brand_name"] = p["brands"]["name"]
            del p["brands"]
            return p
        return None

    def add_product(self, brand_id, name, price=0, notes="", image_path=""):
        res = self.client.table("products").insert({
            "brand_id": brand_id,
            "name": name,
            "price": price,
            "notes": notes,
            "image_path": image_path,
        }).execute()
        return res.data[0]["id"]

    def update_product(self, product_id, **kwargs):
        allowed = {"brand_id", "name", "price", "notes", "image_path"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.client.table("products").update(fields).eq("id", product_id).execute()

    def delete_product(self, product_id):
        self.client.table("products").delete().eq("id", product_id).execute()

    # ════════════════════════════════════════════
    #  订单
    # ════════════════════════════════════════════
    def get_orders(self, product_id=None, brand_id=None, status=None, keyword=None):
        query = self.client.table("orders").select("*, products(name,price,image_path,brand_id)")
        if product_id:
            query = query.eq("product_id", product_id)
        if brand_id:
            query = query.eq("products.brand_id", brand_id)
        if status:
            query = query.eq("status", status)
        if keyword:
            # 需要分别搜订单字段和产品名，用in_语法不太方便，先搜订单字段
            query = query.or_(
                f"order_no.ilike.%{keyword}%,customer.ilike.%{keyword}%,notes.ilike.%{keyword}%"
            )
        res = query.order("created_at", desc=True).execute()
        # 展平关联数据
        orders = []
        for o in res.data:
            prod = o.pop("products", None) or {}
            o["product_name"] = prod.get("name", "")
            o["product_price"] = prod.get("price", 0)
            o["product_image_path"] = prod.get("image_path", "")
            # 如果需要brand_name，单独查
            if prod.get("brand_id"):
                b = self.get_brand(prod["brand_id"])
                o["brand_name"] = b["name"] if b else ""
            else:
                o["brand_name"] = ""
            orders.append(o)
        return orders

    def get_order(self, order_id):
        res = self.client.table("orders").select("*, products(name,brand_id)").eq("id", order_id).execute()
        if res.data:
            o = res.data[0]
            prod = o.pop("products", None) or {}
            o["product_name"] = prod.get("name", "")
            if prod.get("brand_id"):
                b = self.get_brand(prod["brand_id"])
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
        res = self.client.table("orders").insert(data).execute()
        return res.data[0]["id"]

    def update_order(self, order_id, **kwargs):
        allowed = {"product_id", "order_no", "customer", "quantity", "notes", "status", "created_at"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.client.table("orders").update(fields).eq("id", order_id).execute()

    def delete_order(self, order_id):
        self.client.table("orders").delete().eq("id", order_id).execute()

    # ════════════════════════════════════════════
    #  统计
    # ════════════════════════════════════════════
    def get_stats(self):
        brands = self.client.table("brands").select("id", count="exact").execute().count or 0
        products = self.client.table("products").select("id", count="exact").execute().count or 0
        orders = self.client.table("orders").select("id", count="exact").execute().count or 0
        pending = self.client.table("orders").select("id", count="exact").eq("status", "pending").execute().count or 0
        shipped = self.client.table("orders").select("id", count="exact").eq("status", "shipped").execute().count or 0
        return {
            "brands": brands, "products": products,
            "orders": orders, "pending": pending, "shipped": shipped,
        }

    # ════════════════════════════════════════════
    #  日志
    # ════════════════════════════════════════════
    def log(self, action, details="", user_id=None, username=""):
        self.client.table("activity_log").insert({
            "action": action,
            "details": details,
            "user_id": user_id,
            "username": username,
        }).execute()

    def get_logs(self, limit=50):
        res = self.client.table("activity_log").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data

    # ════════════════════════════════════════════
    #  图片上传
    # ════════════════════════════════════════════
    def upload_image(self, local_path: str) -> str:
        """上传图片到Supabase Storage，返回公开URL"""
        ext = os.path.splitext(local_path)[1].lower()
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        with open(local_path, "rb") as f:
            self.client.storage.from_(STORAGE_BUCKET).upload(filename, f, {
                "content-type": "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}",
                "upsert": "false",
            })
        # 返回公开URL
        return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"

    def delete_image(self, url: str):
        """从URL提取文件名并删除"""
        if not url or "product-images" not in url:
            return
        filename = url.split("/")[-1]
        try:
            self.client.storage.from_(STORAGE_BUCKET).remove([filename])
        except Exception:
            pass
