-- Versione 8: Aggiunge i campi telefono ed email ai clienti
ALTER TABLE customers ADD COLUMN phone TEXT;
ALTER TABLE customers ADD COLUMN email TEXT;