-- 放心预 - 云端数据库建表
-- 在 Supabase SQL Editor 里执行

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role        TEXT DEFAULT 'member',
    created_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 品牌表
CREATE TABLE IF NOT EXISTS brands (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 产品表
CREATE TABLE IF NOT EXISTS products (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    brand_id    BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    price       REAL DEFAULT 0,
    notes       TEXT DEFAULT '',
    image_path  TEXT DEFAULT '',
    created_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai'),
    updated_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    order_no    TEXT DEFAULT '',
    customer    TEXT DEFAULT '',
    quantity    INTEGER DEFAULT 1,
    notes       TEXT DEFAULT '',
    status      TEXT DEFAULT 'pending',
    created_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai'),
    updated_at  TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 操作日志
CREATE TABLE IF NOT EXISTS activity_log (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT,
    username   TEXT DEFAULT '',
    action     TEXT NOT NULL,
    details    TEXT DEFAULT '',
    created_at TEXT DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 开启RLS（但允许全部访问，后面可以加策略）
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- 允许匿名/登录用户全部操作（简单版本，先不加限制）
CREATE POLICY "Allow all" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON brands FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON orders FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON activity_log FOR ALL USING (true) WITH CHECK (true);

-- 创建存储桶（产品图片）
INSERT INTO storage.buckets (id, name, public) VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;

-- 允许所有人访问存储桶
CREATE POLICY "Public Access" ON storage.objects FOR ALL USING (bucket_id = 'product-images') WITH CHECK (bucket_id = 'product-images');
