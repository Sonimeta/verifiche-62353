-- Versione 2: Aggiunge le colonne di inventario a 'devices'
ALTER TABLE devices ADD COLUMN customer_inventory TEXT;
ALTER TABLE devices ADD COLUMN ams_inventory TEXT;