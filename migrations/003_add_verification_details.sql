-- Versione 3: Aggiunge le colonne per ispezione visiva e dati MTI
ALTER TABLE verifications ADD COLUMN visual_inspection_json TEXT;
ALTER TABLE verifications ADD COLUMN mti_instrument TEXT;
ALTER TABLE verifications ADD COLUMN mti_serial TEXT;
ALTER TABLE verifications ADD COLUMN mti_version TEXT;
ALTER TABLE verifications ADD COLUMN mti_cal_date TEXT;