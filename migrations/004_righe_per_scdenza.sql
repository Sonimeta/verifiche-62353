-- Versione 4: Aggiunge la data della prossima verifica ai dispositivi
ALTER TABLE devices ADD COLUMN next_verification_date TEXT;

