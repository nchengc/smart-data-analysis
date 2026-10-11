-- =============================================================
-- 智能数据分析系统 · 示例数据库 seed
-- 包含 customers / categories / products / orders 四张表 + 关联数据
-- SQLite 方言（strftime 替代 DATE_FORMAT、lower 列名 + 下划线）
-- =============================================================

-- 清理
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- -------------------------------------------------------------
-- 1. customers（客户）
-- -------------------------------------------------------------
CREATE TABLE customers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    region        TEXT NOT NULL,                -- 华东/华南/华北/西南/西北
    city          TEXT NOT NULL,
    register_date DATE NOT NULL,
    tier          TEXT NOT NULL DEFAULT 'normal'  -- normal / gold / vip
);
CREATE INDEX idx_customers_region ON customers(region);

-- -------------------------------------------------------------
-- 2. categories（品类）
-- -------------------------------------------------------------
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    description TEXT
);

-- -------------------------------------------------------------
-- 3. products（商品）
-- -------------------------------------------------------------
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    price       REAL NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
CREATE INDEX idx_products_cat ON products(category_id);

-- -------------------------------------------------------------
-- 4. orders（订单）
-- -------------------------------------------------------------
CREATE TABLE orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    order_date   DATE NOT NULL,
    status       TEXT NOT NULL DEFAULT 'paid',  -- paid / refunded / shipped
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (product_id)  REFERENCES products(id)
);
CREATE INDEX idx_orders_date    ON orders(order_date);
CREATE INDEX idx_orders_cust    ON orders(customer_id);
CREATE INDEX idx_orders_product ON orders(product_id);
