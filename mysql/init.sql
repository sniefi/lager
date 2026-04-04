CREATE TABLE IF NOT EXISTS article (
    id INT PRIMARY KEY AUTO_INCREMENT,
    article_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(32) DEFAULT 'Liter',
    price DECIMAL(10,2) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warehouse (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    type ENUM('main', 'employee') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking (
    id INT PRIMARY KEY AUTO_INCREMENT,
    booking_type ENUM('Einkauf', 'Abgang', 'Umlagerung') NOT NULL,
    article_id INT NOT NULL,
    quantity DECIMAL(12,4) NOT NULL,
    purchase_price DECIMAL(10,4) NULL,
    source_warehouse_id INT NULL,
    target_warehouse_id INT NULL,
    abgang_destination ENUM('Eigenbedarf', 'Kunde') NULL,
    customer_name VARCHAR(255) NULL,
    is_billed TINYINT(1) DEFAULT 0,
    billed_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES article(id),
    FOREIGN KEY (source_warehouse_id) REFERENCES warehouse(id),
    FOREIGN KEY (target_warehouse_id) REFERENCES warehouse(id)
);

CREATE OR REPLACE VIEW v_stock AS
SELECT
    w.id          AS warehouse_id,
    w.name        AS warehouse_name,
    w.type        AS warehouse_type,
    a.id          AS article_id,
    a.article_id  AS article_code,
    a.name        AS article_name,
    a.unit        AS unit,
    COALESCE(SUM(
        CASE
            WHEN b.target_warehouse_id = w.id THEN b.quantity
            WHEN b.source_warehouse_id = w.id THEN -b.quantity
            ELSE 0
        END
    ), 0) AS stock
FROM warehouse w
CROSS JOIN article a
LEFT JOIN booking b ON b.article_id = a.id
    AND (b.target_warehouse_id = w.id OR b.source_warehouse_id = w.id)
GROUP BY w.id, w.name, w.type, a.id, a.article_id, a.name, a.unit;

INSERT INTO warehouse (name, type) VALUES ('Hauptlager', 'main')
ON DUPLICATE KEY UPDATE name = name;
