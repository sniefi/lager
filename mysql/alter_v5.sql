-- Migration v5: WooCommerce Produkt-ID pro Artikel
-- Auf dem Live-Server ausführen:
--   docker exec -i <mysql-container> mysql -u lager -p lager < alter_v5.sql

ALTER TABLE article
    ADD COLUMN woo_product_id INT NULL AFTER price;

-- Bekannte Matches (Lager article.id → WooCommerce Produkt-ID)
UPDATE article SET woo_product_id = 52  WHERE id = 4;   -- Aquamaris Gin 0,7l        → WC: Aquamaris Distilled Dry Gin
UPDATE article SET woo_product_id = 53  WHERE id = 5;   -- Aquamaris Vodka 0,7l      → WC: Aquamaris Vodka
UPDATE article SET woo_product_id = 51  WHERE id = 11;  -- Choco Noir                → WC: Choco Noir
UPDATE article SET woo_product_id = 50  WHERE id = 3;   -- Choco Schanel No 3 Citrus → WC: Choco Schanel No 3 Citrus
UPDATE article SET woo_product_id = 49  WHERE id = 2;   -- Choco Schanel No 2 Chili  → WC: Choco Schanel No 2 Chili
UPDATE article SET woo_product_id = 48  WHERE id = 1;   -- Choco Schanel No 1 Vanilla→ WC: Choco Schanel No 1 Vanille
UPDATE article SET woo_product_id = 114 WHERE id = 12;  -- Soleggiato                → WC: Marabino Soleggiato
UPDATE article SET woo_product_id = 113 WHERE id = 18;  -- Terra argilosse           → WC: Marabino Terre Argillose
UPDATE article SET woo_product_id = 112 WHERE id = 19;  -- Terra Calcare             → WC: Marabino Terre Calcaree
UPDATE article SET woo_product_id = 111 WHERE id = 14;  -- Eureka                    → WC: Marabino Èureka
UPDATE article SET woo_product_id = 108 WHERE id = 15;  -- Archimede                 → WC: Marabino Archimede
UPDATE article SET woo_product_id = 107 WHERE id = 13;  -- Muscatedda                → WC: Marabino Muscatedda
UPDATE article SET woo_product_id = 110 WHERE id = 20;  -- Rosa Nera                 → WC: Marabino Rosa Nera
UPDATE article SET woo_product_id = 109 WHERE id = 21;  -- Parring                   → WC: Marabino Parrino
-- Kein WC-Match: Aquamaris Gin GOLD (id=7), Sea Water 5l (id=6), Amaro Lumia (id=9),
--                Santa Spina Fumigata (id=8), Santa Spina Cruda (id=10,17), Santa Spina Riposada (id=16)
