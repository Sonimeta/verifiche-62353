-- Versione 1: Creazione delle tabelle iniziali
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT,
    contact_person TEXT
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    serial_number TEXT UNIQUE,
    description TEXT,
    manufacturer TEXT,
    model TEXT,
    applied_parts_json TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    verification_date TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    results_json TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
);