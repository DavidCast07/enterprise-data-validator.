SELECT 
    sku,
    product_name,
    category,
    unit_price,
    -- Promedio de la categoría sin colapsar las filas (Window Function)
    ROUND(AVG(unit_price) OVER (PARTITION BY category), 2) AS category_avg_price,
    -- Diferencia respecto al promedio de su categoría
    ROUND(unit_price - AVG(unit_price) OVER (PARTITION BY category), 2) AS diff_from_avg,
    -- Ranking de precio dentro de su categoría (1 = más caro)
    DENSE_RANK() OVER (PARTITION BY category ORDER BY unit_price DESC) AS price_rank_in_category
FROM master_products
ORDER BY category, price_rank_in_category;
