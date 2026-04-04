-- Migration v3: Inventur-Tabellen + booking_type ENUM erweitern
-- Auf dem Live-Server ausführen (MySQL-Client):

-- 1. Booking-Type ENUM um 'Inventur' erweitern
ALTER TABLE booking
    MODIFY COLUMN booking_type ENUM('Einkauf', 'Abgang', 'Umlagerung', 'Inventur') NOT NULL;

-- 2. Inventur-Kopftabelle (eine Zeile pro Inventur-Vorgang)
CREATE TABLE IF NOT EXISTS inventur (
    id INT PRIMARY KEY AUTO_INCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Inventur-Positionen (eine Zeile pro geändertem Artikel)
CREATE TABLE IF NOT EXISTS inventur_position (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inventur_id INT NOT NULL,
    article_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    quantity_before DECIMAL(12,4) NOT NULL,
    quantity_after DECIMAL(12,4) NOT NULL,
    difference DECIMAL(12,4) NOT NULL,
    FOREIGN KEY (inventur_id) REFERENCES inventur(id),
    FOREIGN KEY (article_id) REFERENCES article(id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouse(id)
);
