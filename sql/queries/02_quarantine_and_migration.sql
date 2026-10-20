-- Tabla de cuarentena para auditar registros que no pasaron las reglas de negocio
CREATE TABLE IF NOT EXISTS rejected_products_log (
    rejection_id SERIAL PRIMARY KEY,
    raw_id INT NOT NULL,
    sku VARCHAR(100),
    product_name VARCHAR(255),
    rejection_reason TEXT NOT NULL,
    raw_payload JSONB,
    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- =========================================================================
-- PASO 1: Auditar y clasificar todos los registros de staging usando CTEs
-- =========================================================================
WITH deduplicated_staging AS (
    SELECT 
        raw_id,
        TRIM(UPPER(sku)) AS clean_sku,
        TRIM(product_name) AS clean_name,
        TRIM(category) AS clean_category,
        unit_price,
        TRIM(UPPER(currency)) AS clean_currency,
        TRIM(UPPER(uom)) AS clean_uom,
        TRIM(LOWER(supplier_email)) AS clean_email,
        raw_metadata,
        loaded_at,
        -- Window Function 1: Identificar el registro más reciente por SKU
        ROW_NUMBER() OVER (
            PARTITION BY TRIM(UPPER(sku)) 
            ORDER BY loaded_at DESC, raw_id DESC
        ) AS rn
    FROM staging_products
),
evaluated_records AS (
    SELECT 
        *,
        CASE 
            WHEN rn > 1 THEN 'DUPLICATE_SKU_OUTDATED'
            WHEN unit_price IS NULL OR unit_price <= 0 THEN 'INVALID_PRICE_ZERO_OR_NEGATIVE'
            WHEN clean_currency NOT IN ('USD', 'EUR') THEN 'INVALID_CURRENCY'
            WHEN clean_uom NOT IN ('EA', 'KG', 'BOX', 'L') THEN 'INVALID_UOM'
            WHEN clean_email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 'INVALID_EMAIL_FORMAT'
            ELSE 'VALID'
        END AS status
    FROM deduplicated_staging
),
-- =========================================================================
-- PASO 2: Enviar los registros inválidos a la tabla de Cuarentena (Log)
-- =========================================================================
inserted_rejections AS (
    INSERT INTO rejected_products_log (raw_id, sku, product_name, rejection_reason, raw_payload)
    SELECT 
        raw_id,
        clean_sku,
        clean_name,
        status,
        jsonb_build_object(
            'unit_price', unit_price,
            'currency', clean_currency,
            'uom', clean_uom,
            'supplier_email', clean_email,
            'metadata', raw_metadata
        )
    FROM evaluated_records
    WHERE status <> 'VALID'
    RETURNING rejection_id
)
-- =========================================================================
-- PASO 3: Migrar solo los registros VÁLIDOS a Master Data (con UPSERT)
-- =========================================================================
INSERT INTO master_products (sku, product_name, category, unit_price, currency, uom, supplier_email, attributes)
SELECT 
    clean_sku,
    clean_name,
    clean_category,
    unit_price,
    clean_currency,
    clean_uom,
    clean_email,
    COALESCE(raw_metadata, '{}'::jsonb)
FROM evaluated_records
WHERE status = 'VALID'
ON CONFLICT (sku) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    category = EXCLUDED.category,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    uom = EXCLUDED.uom,
    supplier_email = EXCLUDED.supplier_email,
    attributes = master_products.attributes || EXCLUDED.attributes,
    updated_at = CURRENT_TIMESTAMP;
