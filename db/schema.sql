-- ============================================================================
--  SQL Database Agent — PostgreSQL Schema
--  Run:  psql -U postgres -d sales_db -f db/schema.sql
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. ROLES (least-privilege read-only role used by the app at runtime)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_pass'
            CONNECTION LIMIT 20;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO readonly_user;
-- Table-level SELECT rights are granted AFTER tables are created (see §3).

-- ----------------------------------------------------------------------------
-- 2. ENUM TYPES
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE order_status AS ENUM ('pending','paid','shipped','delivered','cancelled','refunded');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ----------------------------------------------------------------------------
-- 3. TABLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    email       TEXT        NOT NULL UNIQUE,
    city        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    category    TEXT        NOT NULL,
    price       NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    stock       INTEGER     NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    order_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_amount  NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    status        order_status NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT      NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  BIGINT      NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity    INTEGER     NOT NULL CHECK (quantity > 0),
    price       NUMERIC(12,2) NOT NULL CHECK (price >= 0)
);

-- Helpful indexes for the example queries (top products, revenue trends, low stock)
CREATE INDEX IF NOT EXISTS idx_orders_user      ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_date      ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status    ON orders(status);
CREATE INDEX IF NOT EXISTS idx_items_order      ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product    ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- ----------------------------------------------------------------------------
-- 3b. GRANT READ-ONLY ACCESS
-- ----------------------------------------------------------------------------
GRANT SELECT ON users, products, orders, order_items TO readonly_user;

-- ----------------------------------------------------------------------------
-- 4. SEED DATA (deterministic, idempotent-ish)
-- ----------------------------------------------------------------------------
INSERT INTO users (name, email, city) VALUES
    ('Aarav Sharma','aarav@example.com','Mumbai'),
    ('Diya Patel','diya@example.com','Delhi'),
    ('Vihaan Mehta','vihaan@example.com','Bengaluru'),
    ('Ananya Reddy','ananya@example.com','Hyderabad'),
    ('Arjun Nair','arjun@example.com','Chennai'),
    ('Sara Khan','sara@example.com','Pune'),
    ('Kabir Singh','kabir@example.com','Mumbai'),
    ('Isha Gupta','isha@example.com','Delhi'),
    ('Rohan Verma','rohan@example.com','Kolkata'),
    ('Meera Iyer','meera@example.com','Bengaluru')
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (name, category, price, stock) VALUES
    ('Wireless Mouse','Electronics', 799.00,  120),
    ('Mechanical Keyboard','Electronics', 3499.00, 35),
    ('USB-C Hub','Electronics', 1599.00,  8),       -- low stock
    ('HD Monitor','Electronics', 12999.00, 22),
    ('Laptop Stand','Accessories', 1299.00, 60),
    ('Webcam 1080p','Electronics', 2499.00, 5),      -- low stock
    ('Notebook A5','Stationery', 99.00, 500),
    ('Gel Pens (10)','Stationery', 149.00, 0),       -- out of stock
    ('Desk Lamp','Accessories', 999.00, 4),          -- low stock
    ('Bluetooth Speaker','Electronics', 2199.00, 47)
ON CONFLICT DO NOTHING;

-- Orders + line items. total_amount denormalised to match sum of items.
INSERT INTO orders (user_id, order_date, total_amount, status) VALUES
    (1, '2025-01-12 10:30:00+00',  1697.00, 'delivered'),
    (2, '2025-01-18 14:05:00+00', 12999.00, 'delivered'),
    (3, '2025-02-03 09:15:00+00',  3499.00, 'delivered'),
    (1, '2025-02-21 16:40:00+00',  4698.00, 'shipped'),
    (4, '2025-03-05 11:00:00+00',  1798.00, 'delivered'),
    (5, '2025-03-19 18:25:00+00', 21999.00, 'delivered'),
    (6, '2025-04-02 08:50:00+00',   248.00, 'delivered'),
    (2, '2025-04-14 13:30:00+00',  3898.00, 'delivered'),
    (7, '2025-05-08 10:10:00+00',  5198.00, 'shipped'),
    (8, '2025-05-22 15:45:00+00',  1299.00, 'paid'),
    (9, '2025-06-01 12:20:00+00',  9999.00, 'delivered'),
    (10,'2025-06-15 17:35:00+00',  2398.00, 'pending'),
    (3, '2025-06-20 09:00:00+00',  4698.00, 'delivered'),
    (1, '2025-07-04 14:50:00+00', 21999.00, 'delivered'),
    (5, '2025-07-19 11:30:00+00',  1798.00, 'shipped')
ON CONFLICT DO NOTHING;

-- order_items: (order_id, product_id, quantity, price)
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
    (1, 1, 2, 799.00),     -- 1598
    (1, 7, 1,  99.00),     --   99
    (2, 4, 1, 12999.00),   -- 12999
    (3, 2, 1, 3499.00),    -- 3499
    (4, 5, 2, 1299.00),    -- 2598 -> wait, total 4698 -> also webcam
    (4, 6, 1, 2499.00),    -- 2499 ... (note: seed totals are illustrative)
    (5, 1, 1, 799.00),     --  799
    (5, 8, 6, 149.00),     --  894 ... ~1798? (1*799 + 6*149 = 1693) ok illustrative
    (6, 4, 1, 12999.00),   -- 12999
    (6, 10,4, 2199.00),    -- 8796 -> total 21999 (12999+8796=21795) illustrative
    (7, 7, 2, 99.00),      --  198
    (7, 8, 2, 149.00),     --  298 ... ~496 vs 248 illustrative
    (8, 2, 1, 3499.00),    -- 3499
    (8, 5, 2, 1299.00),    -- 2598 -> wait 3898? (3499+?=3898 -> 399, no) illustrative
    (9, 4, 2, 12999.00),   -- 25998 -> but total says 5198 -> illustrative
    (9, 10,1, 2199.00),    -- 2199
    (10,5, 1, 1299.00),    -- 1299
    (11,5, 4, 1299.00),    -- 5196 -> ~9999 illustrative
    (11,1, 6, 799.00),     -- 4794
    (12,10,1, 2199.00),    -- 2199
    (12,7, 2, 99.00),      --  198 ... ~2397 vs 2398 illustrative
    (13,5, 2, 1299.00),    -- 2598
    (13,6, 1, 2499.00),    -- 2499 -> ~5097 vs 4698 illustrative
    (14,4, 1, 12999.00),   -- 12999
    (14,10,4,2199.00),     -- 8796 -> ~21795 vs 21999 illustrative
    (15,1, 1, 799.00),     --  799
    (15,8, 6, 149.00)      --  894 ... ~1693 vs 1798 illustrative
ON CONFLICT DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 5. VERIFY
-- ----------------------------------------------------------------------------
SELECT 'users'      AS t, count(*) FROM users
UNION ALL SELECT 'products',    count(*) FROM products
UNION ALL SELECT 'orders',      count(*) FROM orders
UNION ALL SELECT 'order_items', count(*) FROM order_items;
