-- Migration v2: Preis und Aktiv-Status zu Artikel hinzufügen
-- Auf dem Live-Server ausführen:
--   docker exec -i <mysql-container> mysql -u lager -p lager < alter_v2.sql
-- oder direkt im MySQL-Client:

ALTER TABLE article
    ADD COLUMN price DECIMAL(10,2) NULL AFTER unit,
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER price;
