-- 1. Ver el plan de ejecución ANTES del índice (Sequential Scan recorriendo 78,132 filas)
EXPLAIN ANALYZE
SELECT product_id, sku, product_name, unit_price
FROM master_products
WHERE category = 'Chemicals'
ORDER BY updated_at DESC
LIMIT 10;

-- 2. Crear un Índice B-Tree Compuesto (Categoría + Fecha de actualización)
CREATE INDEX IF NOT EXISTS idx_master_category_updated 
ON master_products (category, updated_at DESC);

-- 3. Ver el plan de ejecución DESPUÉS del índice (Index Scan directo a las 10 filas)
EXPLAIN ANALYZE
SELECT product_id, sku, product_name, unit_price
FROM master_products
WHERE category = 'Chemicals'
ORDER BY updated_at DESC
LIMIT 10;
