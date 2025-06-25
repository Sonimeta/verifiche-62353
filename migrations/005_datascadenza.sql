-- Versione 5: Aggiunge l'intervallo di verifica (in mesi) ai dispositivi
ALTER TABLE devices ADD COLUMN verification_interval INTEGER;