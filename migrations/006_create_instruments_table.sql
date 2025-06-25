-- Versione 6: Crea la tabella per l'anagrafica degli strumenti di misura (MTI)
CREATE TABLE mti_instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_name TEXT NOT NULL,
    serial_number TEXT NOT NULL,
    fw_version TEXT,
    calibration_date TEXT,
    is_default INTEGER DEFAULT 0 NOT NULL
);