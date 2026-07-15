-- =============================================
-- Georgia Retail Intelligence — Database Schema
-- =============================================

-- Products table: master product catalog
CREATE TABLE IF NOT EXISTS products (
    id                  BIGINT PRIMARY KEY,
    name                TEXT NOT NULL,
    barcode             TEXT,
    name_normalized     TEXT,
    brand               TEXT,
    image_url           TEXT,
    unit                TEXT,
    quantity            NUMERIC,
    normalized_unit     TEXT,
    store_slug          TEXT,
    category_slug       TEXT,
    parent_category_slug TEXT,
    city_slug           TEXT,
    chain_rank          INT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Prices table: historical price tracking
CREATE TABLE IF NOT EXISTS prices (
    id                  BIGSERIAL PRIMARY KEY,
    product_id          BIGINT REFERENCES products(id) ON DELETE CASCADE,
    original_price      NUMERIC,
    sale_price          NUMERIC,
    discount_percent    NUMERIC,
    is_on_sale          BOOLEAN DEFAULT FALSE,
    recorded_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id);
CREATE INDEX IF NOT EXISTS idx_prices_recorded_at ON prices(recorded_at);
CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_slug);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_slug);
CREATE INDEX IF NOT EXISTS idx_products_city ON products(city_slug);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);

-- Materialized view: latest prices per product
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_prices AS
SELECT DISTINCT ON (p.product_id)
    p.product_id,
    pr.name,
    pr.brand,
    pr.category_slug,
    pr.parent_category_slug,
    pr.city_slug,
    pr.store_slug,
    p.original_price,
    p.sale_price,
    p.discount_percent,
    p.is_on_sale,
    p.recorded_at
FROM prices p
JOIN products pr ON pr.id = p.product_id
ORDER BY p.product_id, p.recorded_at DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_latest_prices_product_id ON latest_prices(product_id);

-- =============================================
-- Future Tables (recommended next steps)
-- =============================================

-- Consumer transaction data for simulation realism
-- CREATE TABLE IF NOT EXISTS consumer_transactions (
--     id              BIGSERIAL PRIMARY KEY,
--     product_id      BIGINT REFERENCES products(id),
--     store_slug      TEXT,
--     city_slug       TEXT,
--     quantity        NUMERIC,
--     total_price     NUMERIC,
--     transaction_at  TIMESTAMPTZ DEFAULT NOW()
-- );

-- Inflation tracking index
-- CREATE TABLE IF NOT EXISTS inflation_index (
--     id              BIGSERIAL PRIMARY KEY,
--     category_slug   TEXT,
--     city_slug       TEXT,
--     avg_price       NUMERIC,
--     index_value     NUMERIC,
--     recorded_month  DATE,
--     recorded_at     TIMESTAMPTZ DEFAULT NOW()
-- );

-- Store competition metrics
-- CREATE TABLE IF NOT EXISTS store_competition (
--     id              BIGSERIAL PRIMARY KEY,
--     store_slug      TEXT,
--     city_slug       TEXT,
--     competitor_slug TEXT,
--     overlap_count   INT,
--     avg_price_diff  NUMERIC,
--     recorded_at     TIMESTAMPTZ DEFAULT NOW()
-- );

-- Agent behavior log for AI economy simulations
-- CREATE TABLE IF NOT EXISTS agent_behavior (
--     id              BIGSERIAL PRIMARY KEY,
--     agent_id        TEXT,
--     action_type     TEXT,
--     product_id      BIGINT REFERENCES products(id),
--     store_slug      TEXT,
--     price_paid      NUMERIC,
--     quantity        NUMERIC,
--     satisfaction    NUMERIC,
--     simulation_tick INT,
--     created_at      TIMESTAMPTZ DEFAULT NOW()
-- );

-- Regional price variance
-- CREATE TABLE IF NOT EXISTS regional_prices (
--     id              BIGSERIAL PRIMARY KEY,
--     product_id      BIGINT REFERENCES products(id),
--     city_slug       TEXT,
--     avg_price       NUMERIC,
--     min_price       NUMERIC,
--     max_price       NUMERIC,
--     price_variance  NUMERIC,
--     recorded_month  DATE,
--     recorded_at     TIMESTAMPTZ DEFAULT NOW()
-- );
