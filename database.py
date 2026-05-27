"""
预售管理系统 - 数据库层
三级结构: 品牌 → 产品 → 订单
"""
import sqlite3
import hashlib
import os
from datetime import datetime
from contextlib import contextmanager
from config import DB_PATH


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── 初始化 ────────────────────────────────
    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT UNIQUE NOT NULL,
                    password    TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role        TEXT DEFAULT 'member',
                    created_at  TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS brands (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS products (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id    INTEGER NOT NULL,
                    name        TEXT NOT NULL,
                    price       REAL DEFAULT 0,
                    notes       TEXT DEFAULT '',
                    created_at  TEXT DEFAULT (datetime('now','localtime')),
                    updated_at  TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id  INTEGER NOT NULL,
                    order_no    TEXT DEFAULT '',
                    customer    TEXT DEFAULT '',
                    quantity    INTEGER DEFAULT 1,
                    notes       TEXT DEFAULT '',
                    status      TEXT DEFAULT 'pending',
                    created_at  TEXT DEFAULT (datetime('now','localtime')),
                    updated_at  TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER,
                    username   TEXT DEFAULT '',
                    action     TEXT NOT NULL,
                    details    TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );
            """)

# 首次安装不再创建默认账号，由用户自己注册管理员

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
        with self._conn() as conn:
            return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None

    def login(self, username: str, password: str):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if row and self.verify(password, row["password"]):
                return dict(row)
        return None

    def get_users(self):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id, username, display_name, role, created_at FROM users ORDER BY id"
            ).fetchall()]

    def add_user(self, username, password, display_name, role="member"):
        with self._conn() as conn:
            conn.execute("INSERT INTO users (username, password, display_name, role) VALUES (?,?,?,?)",
                         (username, self._hash(password), display_name, role))

    def update_user(self, user_id, display_name=None, role=None, password=None):
        with self._conn() as conn:
            sets, vals = [], []
            if display_name is not None:
                sets.append("display_name=?"); vals.append(display_name)
            if role is not None:
                sets.append("role=?"); vals.append(role)
            if password is not None:
                sets.append("password=?"); vals.append(self._hash(password))
            if sets:
                vals.append(user_id)
                conn.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals)

    def delete_user(self, user_id):
        with self._conn() as conn:
            admin_count = conn.execute("SELECT COUNT(*) as c FROM users WHERE role='admin'").fetchone()["c"]
            user = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if user and user["role"] == "admin" and admin_count <= 1:
                raise ValueError("不能删除最后一个管理员")
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))

    def user_exists(self, username):
        with self._conn() as conn:
            return conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None

    # ════════════════════════════════════════════
    #  品牌
    # ════════════════════════════════════════════
    def get_brands(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM brands ORDER BY created_at DESC").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["product_count"] = conn.execute(
                    "SELECT COUNT(*) as c FROM products WHERE brand_id=?", (r["id"],)
                ).fetchone()["c"]
                result.append(d)
            return result

    def get_brand(self, brand_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM brands WHERE id=?", (brand_id,)).fetchone()
            return dict(row) if row else None

    def add_brand(self, name):
        with self._conn() as conn:
            cur = conn.execute("INSERT INTO brands (name) VALUES (?)", (name,))
            return cur.lastrowid

    def update_brand(self, brand_id, name):
        with self._conn() as conn:
            conn.execute("UPDATE brands SET name=? WHERE id=?", (name, brand_id))

    def delete_brand(self, brand_id):
        with self._conn() as conn:
            conn.execute("DELETE FROM brands WHERE id=?", (brand_id,))

    # ════════════════════════════════════════════
    #  产品（属于品牌）
    # ════════════════════════════════════════════
    def get_products(self, brand_id=None):
        with self._conn() as conn:
            if brand_id:
                rows = conn.execute(
                    "SELECT p.*, b.name as brand_name FROM products p LEFT JOIN brands b ON p.brand_id=b.id WHERE p.brand_id=? ORDER BY p.created_at DESC",
                    (brand_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT p.*, b.name as brand_name FROM products p LEFT JOIN brands b ON p.brand_id=b.id ORDER BY p.created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def search_products(self, keyword):
        with self._conn() as conn:
            like = f"%{keyword}%"
            rows = conn.execute(
                """SELECT p.*, b.name as brand_name FROM products p
                   LEFT JOIN brands b ON p.brand_id=b.id
                   WHERE p.name LIKE ? OR b.name LIKE ? OR p.notes LIKE ?
                   ORDER BY p.created_at DESC""",
                (like, like, like)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_product(self, product_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT p.*, b.name as brand_name FROM products p LEFT JOIN brands b ON p.brand_id=b.id WHERE p.id=?",
                (product_id,)
            ).fetchone()
            return dict(row) if row else None

    def add_product(self, brand_id, name, price=0, notes=""):
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO products (brand_id, name, price, notes) VALUES (?,?,?,?)",
                (brand_id, name, price, notes)
            )
            return cur.lastrowid

    def update_product(self, product_id, **kwargs):
        allowed = {"brand_id", "name", "price", "notes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            sets = ",".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE products SET {sets} WHERE id=?", (*fields.values(), product_id))

    def delete_product(self, product_id):
        with self._conn() as conn:
            conn.execute("DELETE FROM products WHERE id=?", (product_id,))

    # ════════════════════════════════════════════
    #  订单（属于产品）
    # ════════════════════════════════════════════
    def get_orders(self, product_id=None, brand_id=None, status=None, keyword=None):
        with self._conn() as conn:
            query = """SELECT o.*, p.name as product_name, b.name as brand_name
                       FROM orders o
                       LEFT JOIN products p ON o.product_id=p.id
                       LEFT JOIN brands b ON p.brand_id=b.id
                       WHERE 1=1"""
            params = []
            if product_id:
                query += " AND o.product_id=?"
                params.append(product_id)
            if brand_id:
                query += " AND p.brand_id=?"
                params.append(brand_id)
            if status:
                query += " AND o.status=?"
                params.append(status)
            if keyword:
                like = f"%{keyword}%"
                query += " AND (o.order_no LIKE ? OR o.customer LIKE ? OR o.notes LIKE ? OR p.name LIKE ?)"
                params.extend([like, like, like, like])
            query += " ORDER BY o.created_at DESC"
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def get_order(self, order_id):
        with self._conn() as conn:
            row = conn.execute(
                """SELECT o.*, p.name as product_name, b.name as brand_name
                   FROM orders o LEFT JOIN products p ON o.product_id=p.id
                   LEFT JOIN brands b ON p.brand_id=b.id WHERE o.id=?""",
                (order_id,)
            ).fetchone()
            return dict(row) if row else None

    def add_order(self, product_id, quantity=1, order_no="", customer="", notes=""):
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO orders (product_id, order_no, customer, quantity, notes) VALUES (?,?,?,?,?)",
                (product_id, order_no, customer, quantity, notes)
            )
            return cur.lastrowid

    def update_order(self, order_id, **kwargs):
        allowed = {"product_id", "order_no", "customer", "quantity", "notes", "status"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            sets = ",".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE orders SET {sets} WHERE id=?", (*fields.values(), order_id))

    def delete_order(self, order_id):
        with self._conn() as conn:
            conn.execute("DELETE FROM orders WHERE id=?", (order_id,))

    # ════════════════════════════════════════════
    #  统计
    # ════════════════════════════════════════════
    def get_stats(self):
        with self._conn() as conn:
            brands = conn.execute("SELECT COUNT(*) as c FROM brands").fetchone()["c"]
            products = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
            orders = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
            pending = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'").fetchone()["c"]
            shipped = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='shipped'").fetchone()["c"]
            return {
                "brands": brands, "products": products,
                "orders": orders, "pending": pending, "shipped": shipped,
            }

    # ════════════════════════════════════════════
    #  日志
    # ════════════════════════════════════════════
    def log(self, action, details="", user_id=None, username=""):
        with self._conn() as conn:
            conn.execute("INSERT INTO activity_log (user_id, username, action, details) VALUES (?,?,?,?)",
                         (user_id, username, action, details))

    def get_logs(self, limit=50):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]
