-- 1. Tabla Staging (Datos crudos sin restricciones fuertes, tal como llegan de un CSV/Excel)
CREATE TABLE staging_products (
    raw_id SERIAL PRIMARY KEY,
    sku VARCHAR(100),
    product_name VARCHAR(255),
    category VARCHAR(100),
    unit_price NUMERIC(12, 2),
    currency VARCHAR(10),
    uom VARCHAR(20), -- Unit of Measure (EA, KG, BOX)
    supplier_email VARCHAR(255),
    raw_metadata JSONB,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla Master Data (Reglas de negocio estrictas a nivel de Base de Datos)
CREATE TABLE master_products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    currency CHAR(3) NOT NULL CHECK (currency IN ('USD', 'EUR')),
    uom VARCHAR(10) NOT NULL CHECK (uom IN ('EA', 'KG', 'BOX', 'L')),
    supplier_email VARCHAR(255) CHECK (supplier_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    attributes JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Insertar lote de prueba con casos reales (duplicados, precios negativos, UOM inválidos)
INSERT INTO staging_products (sku, product_name, category, unit_price, currency, uom, supplier_email, raw_metadata) VALUES
('MAT-1001', 'Ceramic Coating Pro 50ml', 'Chemicals', 85.00, 'USD', 'EA', 'sales@gyeon.com', '{"origin": "KR", "batch": 101}'),
('MAT-1001', 'Ceramic Coating Pro 50ml (Updated)', 'Chemicals', 89.50, 'USD', 'EA', 'sales@gyeon.com', '{"origin": "KR", "batch": 102}'), -- Duplicado más reciente
('MAT-1002', 'Microfiber Towel 40x40', 'Accessories', -12.00, 'USD', 'EA', 'contact@towels.com', '{"gsm": 380}'), -- Error: Precio negativo
('MAT-1003', 'Heavy Cut Compound 1L', 'Compounds', 42.00, 'USD', 'LITROS', 'info@menzerna.de', '{"cut": 9}'), -- Error: UOM inválido (debe ser L)
('MAT-1004', 'Dual Action Polisher 15mm', 'Tools', 250.00, 'USD', 'EA', 'correo_invalido_sin_arroba.com', '{"watts": 1000}'), -- Error: Email inválido
('MAT-1005', 'Foam Cannon Lance', 'Tools', 65.00, 'USD', 'EA', 'orders@mtmhydro.com', '{"pressure_bar": 160}'),
('MAT-1005', 'Foam Cannon Lance', 'Tools', 65.00, 'USD', 'EA', 'orders@mtmhydro.com', '{"pressure_bar": 160}'); -- Duplicado exacto
