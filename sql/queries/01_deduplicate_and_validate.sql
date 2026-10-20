WITH ranked_staging AS (
    SELECT 
        *,
        -- Numera los registros con el mismo SKU ordenando del más reciente al más antiguo
        ROW_NUMBER() OVER (
            PARTITION BY sku 
            ORDER BY loaded_at DESC, raw_id DESC
        ) AS rn
    FROM staging_products
),
validation_check AS (
    SELECT 
        raw_id,
        sku,
        product_name,
        unit_price,
        currency,
        uom,
        supplier_email,
        rn,
        -- Diagnóstico automático de reglas de negocio
        CASE 
            WHEN rn > 1 THEN 'REJECTED: Duplicate SKU (Outdated record)'
            WHEN unit_price <= 0 THEN 'REJECTED: Unit price must be greater than 0'
            WHEN uom NOT IN ('EA', 'KG', 'BOX', 'L') THEN 'REJECTED: Invalid Unit of Measure (UOM)'
            WHEN supplier_email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN 'REJECTED: Invalid Email Format'
            ELSE 'VALID'
        END AS validation_status
    FROM ranked_staging
)
SELECT * FROM validation_check
ORDER BY sku, rn;
