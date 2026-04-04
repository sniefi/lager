-- Migration v4: Grund-Feld für Kunden-Abgänge
ALTER TABLE booking
    ADD COLUMN abgang_grund VARCHAR(32) NULL AFTER customer_name;
