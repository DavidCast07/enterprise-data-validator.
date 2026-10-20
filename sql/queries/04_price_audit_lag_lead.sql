-- 1. Crear tabla de historial de precios e inventario para auditoría
CREATE TABLE IF NOT EXISTS product_price_history (
    history_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    recorded_date DATE NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    stock_movement INT NOT NULL -- Positivo = Entrada de almacén, Negativo = Venta/Salida
);

TRUNCATE TABLE product_price_history;

-- 2. Insertar movimientos cronológicos de prueba
INSERT INTO product_price_history (sku, recorded_date, unit_price, stock_movement) VALUES
('MAT-1001', '2026-07-01', 80.00, 50),
('MAT-1001', '2026-08-01', 82.00, -15),
('MAT-1001', '2026-09-01', 85.00, -10),
('MAT-1001', '2026-10-01', 110.00, 30), -- Anomalía: subida brusca de precio (+29.4%)
('MAT-1005', '2026-07-01', 65.00, 20),
('MAT-1005', '2026-08-01', 65.00, -5),
('MAT-1005', '2026-09-01', 60.00, -8),  -- Descuento aplicado
('MAT-1005', '2026-10-01', 65.00, 15);

-- 3. Consulta Analítica con LAG(), LEAD() y Running Total (SUM OVER)
WITH price_analysis AS (
    SELECT 
        sku,
        recorded_date,
        unit_price,
        -- LAG: Trae el precio de la fecha anterior para el mismo SKU
        LAG(unit_price) OVER (PARTITION BY sku ORDER BY recorded_date) AS prev_price,
        -- LEAD: Trae el precio de la fecha siguiente para el mismo SKU
        LEAD(unit_price) OVER (PARTITION BY sku ORDER BY recorded_date) AS next_price,
        stock_movement,
        -- SUM() OVER: Calcula el stock acumulado (Running Total) día a día
        SUM(stock_movement) OVER (
            PARTITION BY sku 
            ORDER BY recorded_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_stock_balance
    FROM product_price_history
)
SELECT 
    sku,
    recorded_date,
    prev_price,
    unit_price AS current_price,
    next_price,
    -- Variación porcentual respecto al periodo anterior
    ROUND(
        ((unit_price - prev_price) / NULLIF(prev_price, 0)) * 100, 2
    ) AS price_change_pct,
    running_stock_balance,
    -- Alerta automática de auditoría si el precio salta más de 20%
    CASE 
        WHEN prev_price IS NULL THEN 'INITIAL_RECORD'
        WHEN ((unit_price - prev_price) / prev_price) > 0.20 THEN 'ALERT: High Price Spike (>20%)'
        WHEN unit_price < prev_price THEN 'PRICE_DROP'
        ELSE 'NORMAL'
    END AS audit_flag
FROM price_analysis
ORDER BY sku, recorded_date;
