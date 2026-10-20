-- Activar cronómetro en consola para medir rendimiento real
\timing on

-- 1. Limpiar staging para la prueba de estrés de 100,000 filas
TRUNCATE TABLE staging_products RESTART IDENTITY;
TRUNCATE TABLE rejected_products_log RESTART IDENTITY;

-- 2. Generar 100,000 registros sintéticos usando generate_series
INSERT INTO staging_products (sku, product_name, category, unit_price, currency, uom, supplier_email, raw_metadata)
SELECT 
    -- Genera unos ~85,000 SKUs únicos y ~15,000 duplicados intencionales
    'SKU-' || (CASE WHEN i % 7 = 0 THEN i - 1 ELSE i END) AS sku,
    'Industrial Component #' || i AS product_name,
    (ARRAY['Chemicals', 'Tools', 'Accessories', 'Compounds', 'Electronics'])[1 + (i % 5)] AS category,
    -- Cada 20 filas inyectamos un precio negativo (-15.00) para probar el filtro de rechazo
    CASE WHEN i % 20 = 0 THEN -15.00 ELSE ROUND((RANDOM() * 500 + 5)::numeric, 2) END AS unit_price,
    'USD' AS currency,
    -- Cada 33 filas inyectamos un UOM inválido ('INVALID_UOM')
    CASE WHEN i % 33 = 0 THEN 'INVALID_UOM' ELSE (ARRAY['EA', 'KG', 'BOX', 'L'])[1 + (i % 4)] END AS uom,
    -- Cada 50 filas inyectamos un correo roto
    CASE WHEN i % 50 = 0 THEN 'broken_email.com' ELSE 'supplier' || (i % 500) || '@industrial-corp.com' END AS supplier_email,
    jsonb_build_object('batch_id', (i % 100), 'generated_row', i) AS raw_metadata
FROM generate_series(1, 100000) AS s(i);

-- 3. Crear un Índice en staging_products para acelerar el PARTITION BY en 100k filas
CREATE INDEX IF NOT EXISTS idx_staging_sku_loaded ON staging_products (sku, loaded_at DESC, raw_id DESC);

-- 4. Crear la Vista Ejecutiva de Calidad de Datos (Data Quality Dashboard View)
CREATE OR REPLACE VIEW vw_data_quality_summary AS
SELECT 
    (SELECT COUNT(*) FROM staging_products) AS total_raw_records,
    (SELECT COUNT(*) FROM master_products) AS total_clean_master_records,
    (SELECT COUNT(*) FROM rejected_products_log) AS total_rejected_records,
    ROUND(
        ((SELECT COUNT(*) FROM master_products)::numeric / 
        NULLIF((SELECT COUNT(*) FROM staging_products), 0)) * 100, 2
    ) AS data_quality_score_pct;
