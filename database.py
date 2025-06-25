# database.py (Versione con sistema di migrazione)
import sqlite3
import json
import os
import logging
from datetime import datetime

def get_db_connection():
    """Stabilisce e restituisce una connessione al database con row_factory."""
    conn = sqlite3.connect('verifiche.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    logging.info("Connessione al database stabilita.")
    return conn

def migrate_database():
    """
    Applica le migrazioni SQL al database in modo sequenziale.
    Traccia la versione corrente dello schema in una tabella 'schema_version'.
    """
    # 1. Crea la tabella per il versioning dello schema, se non esiste
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);")
    
    # 2. Controlla la versione corrente. Se la tabella è vuota, la versione è 0.
    cursor.execute("SELECT version FROM schema_version;")
    result = cursor.fetchone()
    current_version = result['version'] if result else 0
    
    conn.commit()
    conn.close()

    # 3. Trova e ordina i file di migrazione
    migrations_path = 'migrations'
    if not os.path.isdir(migrations_path):
        logging.info(f"ERRORE: La cartella delle migrazioni '{migrations_path}' non è stata trovata.")
        return

    try:
        migration_files = sorted([f for f in os.listdir(migrations_path) if f.endswith('.sql')])
    except FileNotFoundError:
        logging.info(f"ERRORE: La cartella delle migrazioni '{migrations_path}' non è stata trovata.")
        return

    # 4. Applica le nuove migrazioni
    for m_file in migration_files:
        try:
            file_version = int(m_file.split('_')[0])
        except (ValueError, IndexError):
            logging.info(f"ATTENZIONE: Il file di migrazione '{m_file}' non è nominato correttamente e verrà ignorato.")
            continue

        if file_version > current_version:
            logging.info(f"Applicando migrazione: {m_file}...")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            with open(os.path.join(migrations_path, m_file), 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Esegui lo script di migrazione
            cursor.executescript(sql_script)

            # Aggiorna la versione dello schema nel database
            if current_version == 0 and file_version == 1:
                 # Se partiamo da zero, inseriamo la prima versione
                 cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (file_version,))
            else:
                # Altrimenti, la aggiorniamo
                cursor.execute("UPDATE schema_version SET version = ?", (file_version,))
            
            conn.commit()
            conn.close()
            current_version = file_version # Aggiorna la versione in memoria
            logging.info(f"Database aggiornato alla versione {current_version}.")

# --- Funzioni di manipolazione dati (DAO - Data Access Object) ---

def add_device(customer_id, serial, desc, mfg, model, applied_parts, customer_inv, ams_inv, verification_interval):
    """Aggiunge un nuovo dispositivo, includendo l'intervallo di verifica."""
    pa_json = json.dumps([pa.__dict__ for pa in applied_parts])
    
    # --- LOGICA DI CONVERSIONE CORRETTA ---
    interval = None
    try:
        # Prova a convertire il valore in un intero.
        # Funziona sia se è una stringa (es. "12") sia se è già un numero (es. 12).
        interval = int(verification_interval)
    except (ValueError, TypeError):
        # Se la conversione fallisce (es. il valore è "Nessuno" o None), 
        # l'intervallo rimane None, che è il comportamento corretto.
        pass
    # --- FINE LOGICA CORRETTA ---

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO devices (customer_id, serial_number, description, manufacturer, model, applied_parts_json, customer_inventory, ams_inventory, verification_interval) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (customer_id, serial, desc, mfg, model, pa_json, customer_inv, ams_inv, interval)
    )
    conn.commit()
    conn.close()

def update_device(dev_id, serial, desc, mfg, model, applied_parts, customer_inv, ams_inv, verification_interval):
    """Aggiorna un dispositivo esistente, includendo l'intervallo di verifica."""
    pa_json = json.dumps([pa.__dict__ for pa in applied_parts])

    # --- LOGICA DI CONVERSIONE CORRETTA ---
    interval = None
    try:
        interval = int(verification_interval)
    except (ValueError, TypeError):
        pass
    # --- FINE LOGICA CORRETTA ---
    
    conn = get_db_connection()
    conn.execute(
        "UPDATE devices SET serial_number=?, description=?, manufacturer=?, model=?, applied_parts_json=?, customer_inventory=?, ams_inventory=?, verification_interval=? WHERE id=?",
        (serial, desc, mfg, model, pa_json, customer_inv, ams_inv, interval, dev_id)
    )
    conn.commit()
    conn.close()

def add_customer(name, address, phone, email):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO customers (name, address, phone, email) VALUES (?, ?, ?, ?)", (name, address, phone, email))
        logging.info(f"Cliente aggiunto: {name}.")
        conn.commit()
    finally:
        conn.close()

def update_customer(cust_id, name, address, phone, email):
    conn = get_db_connection()
    conn.execute("UPDATE customers SET name=?, address=?, phone=?, email=? WHERE id=?", (name, address, phone, email, cust_id))
    logging.info(f"Cliente ID {cust_id} aggiornato: {name}.")
    conn.commit()
    conn.close()

def delete_customer(cust_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM customers WHERE id=?", (cust_id,))
        conn.commit()
        logging.info(f"Cliente ID {cust_id} eliminato.")    
        return True, "Cliente eliminato."
    except sqlite3.IntegrityError:
        return False, "Impossibile eliminare: il cliente ha dispositivi associati."
    finally:
        conn.close()

def get_all_customers():
    conn = get_db_connection()
    customers = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return customers

def add_or_get_customer(name, address=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM customers WHERE name = ?", (name,))
    customer = cursor.fetchone()
    if customer:
        conn.close()
        return customer['id']
    else:
        cursor.execute("INSERT INTO customers (name, address) VALUES (?, ?)", (name, address))
        customer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return customer_id

def device_exists(serial_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM devices WHERE serial_number = ?", (serial_number,))
    device = cursor.fetchone()
    conn.close()
    return device is not None

def delete_device(dev_id):
    """Elimina un dispositivo e, a cascata, tutte le sue verifiche."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM devices WHERE id=?", (dev_id,))
        conn.commit()
        logging.warning(f"Dispositivo con ID {dev_id} e tutte le sue verifiche sono stati eliminati.")
    except Exception as e:
        logging.error(f"Errore durante l'eliminazione del dispositivo ID {dev_id}", exc_info=True)
        # In caso di errore, annulla la transazione
        conn.rollback()
    finally:
        conn.close()

def get_devices_for_customer(customer_id):
    conn = get_db_connection()
    devices = conn.execute("SELECT * FROM devices WHERE customer_id = ? ORDER BY description", (customer_id,)).fetchall()
    conn.close()
    return devices

def get_device_by_id(device_id):
    conn = get_db_connection()
    device = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    conn.close()
    return device

# app/workers/stm_import_worker.py
import json
import logging
from PySide6.QtCore import QObject, Signal
import database

class StmImportWorker(QObject):
    """Esegue l'importazione di un file archivio .stm in background."""
    finished = Signal(int, int, int, int) # verif_imp, verif_skip, dev_new, cust_new
    error = Signal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        logging.info(f"Avvio importazione dall'archivio: {self.filepath}")
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.error.emit(f"Impossibile leggere o parsare il file .stm: {e}")
            return

        verif_imported = 0
        verif_skipped = 0
        devices_created = 0
        customers_created = 0
        
        # Itera su ogni pacchetto di verifica presente nel file
        for verification_package in data.get("verifications", []):
            try:
                # --- 1. Gestione Cliente ---
                customer_data = verification_package['customer']
                customer_id = database.add_or_get_customer(customer_data['name'], customer_data['address'])
                
                # --- 2. Gestione Dispositivo ---
                device_data = verification_package['device']
                device_serial = device_data['serial_number']
                
                existing_device = database.get_device_by_serial(device_serial)
                if existing_device:
                    device_id = existing_device['id']
                else:
                    # Crea il nuovo dispositivo se non esiste
                    database.add_device(
                        customer_id, device_serial, device_data['description'], device_data['manufacturer'],
                        device_data['model'], json.loads(device_data['applied_parts_json']), 
                        device_data['customer_inventory'], device_data['ams_inventory']
                    )
                    new_device = database.get_device_by_serial(device_serial)
                    device_id = new_device['id']
                    devices_created += 1
                    logging.info(f"Nuovo dispositivo creato: {device_serial}")
                
                # --- 3. Gestione Verifica ---
                verif_details = verification_package['verification_details']
                verif_date = verif_details['verification_date']
                verif_profile = verif_details['profile_name']

                if database.verification_exists(device_id, verif_date, verif_profile):
                    verif_skipped += 1
                    logging.warning(f"Verifica del {verif_date} per S/N {device_serial} già esistente. Saltata.")
                else:
                    # Salva la nuova verifica
                    database.save_verification(
                        device_id=device_id,
                        verification_date=verif_date,
                        profile_name=verif_profile,
                        results=json.loads(verif_details['results_json']),
                        overall_status=verif_details['overall_status'],
                        visual_inspection_data=json.loads(verif_details['visual_inspection_json']),
                        mti_info=verif_details['mti_info']
                    )
                    verif_imported += 1
            
            except Exception as e:
                logging.error(f"Errore durante l'importazione di un record di verifica.", exc_info=True)
                verif_skipped += 1 # Salta il record problematico

        self.finished.emit(verif_imported, verif_skipped, devices_created, customers_created)

def get_verifications_for_device(device_id):
    """Recupera tutte le verifiche per un dato dispositivo."""
    conn = get_db_connection()
    # La query "SELECT *" seleziona automaticamente anche la nuova colonna 'technician_name'
    verifications = conn.execute(
        "SELECT * FROM verifications WHERE device_id = ? ORDER BY verification_date DESC", 
        (device_id,)
    ).fetchall()
    conn.close()
    return verifications

def get_all_customers(search_query=None):
    """Restituisce tutti i clienti, filtrati opzionalmente per nome."""
    conn = get_db_connection()
    query = "SELECT * FROM customers"
    params = []
    if search_query:
        query += " WHERE name LIKE ?"
        params.append(f"%{search_query}%")
    query += " ORDER BY name"
    customers = conn.execute(query, params).fetchall()
    conn.close()
    return customers

def get_devices_for_customer(customer_id, search_query=None):
    """Restituisce i dispositivi di un cliente, filtrati opzionalmente."""
    conn = get_db_connection()
    query = "SELECT * FROM devices WHERE customer_id = ?"
    params = [customer_id]
    if search_query:
        query += " AND (description LIKE ? OR serial_number LIKE ? OR model LIKE ? OR ams_inventory LIKE ? OR customer_inventory LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
    query += " ORDER BY description"
    devices = conn.execute(query, params).fetchall()
    conn.close()
    return devices

def get_stats():
    """Restituisce un dizionario con le statistiche principali."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        device_count = cursor.execute("SELECT COUNT(id) FROM devices").fetchone()[0]
        customer_count = cursor.execute("SELECT COUNT(id) FROM customers").fetchone()[0]
        last_verif_date = cursor.execute("SELECT MAX(verification_date) FROM verifications").fetchone()[0]
    except Exception:
        # Gestisce il caso di DB vuoto o errori
        return {"devices": 0, "customers": 0, "last_verif": "N/A"}
    finally:
        conn.close()

    return {
        "devices": device_count,
        "customers": customer_count,
        "last_verif": last_verif_date if last_verif_date else "Nessuna"
    }

def get_all_verifications_for_customer(customer_id):
    """
    Recupera una lista completa di tutte le verifiche per tutti i dispositivi
    di un dato cliente, unendo le tabelle.
    """
    conn = get_db_connection()
    query = """
        SELECT
            c.name as customer_name,
            d.description as device_description,
            d.serial_number,
            d.model,
            d.manufacturer,
            d.ams_inventory,
            v.id as verification_id,
            v.verification_date,
            v.profile_name,
            v.overall_status
        FROM verifications v
        JOIN devices d ON v.device_id = d.id
        JOIN customers c ON d.customer_id = c.id
        WHERE c.id = ?
        ORDER BY d.description, v.verification_date DESC;
    """
    verifications = conn.execute(query, (customer_id,)).fetchall()
    conn.close()
    return verifications

def get_full_verification_data_for_date(target_date):
    """
    Recupera tutte le verifiche di una data specifica, complete di dati
    di dispositivo e cliente, e le struttura in un dizionario per l'export.
    """
    conn = get_db_connection()
    # Query che unisce tutte le tabelle e filtra per data
    query = """
        SELECT 
            c.id as customer_id, c.name as customer_name, c.address as customer_address,
            d.id as device_id, d.serial_number, d.description, d.manufacturer, d.model, d.applied_parts_json, d.customer_inventory, d.ams_inventory,
            v.id as verification_id, v.verification_date, v.profile_name, v.results_json, v.overall_status, v.visual_inspection_json, v.mti_instrument, v.mti_serial, v.mti_version, v.mti_cal_date
        FROM verifications v
        JOIN devices d ON v.device_id = d.id
        JOIN customers c ON d.customer_id = c.id
        WHERE v.verification_date = ?
    """
    rows = conn.execute(query, (target_date,)).fetchall()
    conn.close()

    export_structure = {
        "export_format_version": "1.0",
        "export_creation_date": datetime.now().isoformat(),
        "verifications_for_date": target_date,
        "verifications": []
    }

    for row in rows:
        verification_package = {
            "customer": {
                "name": row["customer_name"],
                "address": row["customer_address"]
            },
            "device": {
                "serial_number": row["serial_number"],
                "description": row["description"],
                "manufacturer": row["manufacturer"],
                "model": row["model"],
                "applied_parts_json": row["applied_parts_json"],
                "customer_inventory": row["customer_inventory"],
                "ams_inventory": row["ams_inventory"]
            },
            "verification_details": {
                "verification_date": row["verification_date"],
                "profile_name": row["profile_name"],
                "results_json": row["results_json"],
                "overall_status": row["overall_status"],
                "visual_inspection_json": row["visual_inspection_json"],
                "mti_info": {
                    "instrument": row["mti_instrument"],
                    "serial": row["mti_serial"],
                    "version": row["mti_version"],
                    "cal_date": row["mti_cal_date"]
                }
            }
        }
        export_structure["verifications"].append(verification_package)
    
    return export_structure
def get_device_count_for_customer(customer_id):
    """Conta quanti dispositivi sono associati a un cliente."""
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(id) FROM devices WHERE customer_id = ?", (customer_id,)).fetchone()[0]
        return count
    except Exception as e:
        logging.error(f"Impossibile contare i dispositivi per il cliente ID {customer_id}", exc_info=True)
        return 0
    finally:
        conn.close()

def delete_all_devices_for_customer(customer_id):
    """Elimina TUTTI i dispositivi (e a cascata le loro verifiche) per un dato cliente."""
    conn = get_db_connection()
    try:
        # Grazie a "ON DELETE CASCADE", eliminando i dispositivi vengono eliminate anche le verifiche
        cursor = conn.execute("DELETE FROM devices WHERE customer_id = ?", (customer_id,))
        conn.commit()
        logging.warning(f"Eliminati {cursor.rowcount} dispositivi per il cliente ID {customer_id}.")
        return True
    except Exception as e:
        logging.error(f"Errore durante l'eliminazione massiva dei dispositivi per il cliente ID {customer_id}", exc_info=True)
        conn.rollback()
        return False
    finally:
        conn.close()
        
def get_device_by_serial(serial_number):
    """Restituisce i dati di un dispositivo cercando per matricola, o None se non esiste."""
    conn = get_db_connection()
    device = conn.execute("SELECT * FROM devices WHERE serial_number = ?", (serial_number,)).fetchone()
    conn.close()
    return device

def verification_exists(device_id, verification_date, profile_name):
    """Verifica se una verifica specifica esiste già per un dato dispositivo."""
    conn = get_db_connection()
    verif = conn.execute(
        "SELECT id FROM verifications WHERE device_id = ? AND verification_date = ? AND profile_name = ?",
        (device_id, verification_date, profile_name)
    ).fetchone()
    conn.close()
    return verif is not None

def update_device_next_verification_date(device_id, interval_months):
    """Calcola e aggiorna la data della prossima verifica per un dispositivo."""
    if not device_id or not interval_months:
        return
    try:
        # Calcola la data futura. Semplice approssimazione, si può usare dateutil per maggiore precisione.
        from datetime import date
        from dateutil.relativedelta import relativedelta # Richiede: pip install python-dateutil
        
        next_date = date.today() + relativedelta(months=int(interval_months))
        next_date_str = next_date.strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        conn.execute("UPDATE devices SET next_verification_date = ? WHERE id = ?", (next_date_str, device_id))
        conn.commit()
        conn.close()
        logging.info(f"Data prossima verifica per dispositivo ID {device_id} impostata a {next_date_str}")
    except Exception as e:
        logging.error(f"Impossibile aggiornare la data di prossima verifica per il dispositivo ID {device_id}", exc_info=True)


def get_devices_needing_verification(days_in_future=30):
    """Recupera i dispositivi con verifica scaduta o in scadenza."""
    from datetime import date, timedelta
    
    today = date.today()
    future_date = today + timedelta(days=days_in_future)
    
    conn = get_db_connection()
    # Seleziona i dispositivi la cui prossima verifica è nel passato o entro i prossimi X giorni
    query = """
        SELECT d.*, c.name as customer_name FROM devices d
        JOIN customers c ON d.customer_id = c.id
        WHERE d.next_verification_date IS NOT NULL AND d.next_verification_date <= ?
        ORDER BY d.next_verification_date ASC
    """
    devices = conn.execute(query, (future_date.strftime('%Y-%m-%d'),)).fetchall()
    conn.close()
    return devices


def save_verification(device_id, profile_name, results, overall_status, visual_inspection_data, mti_info, technician_name, verification_date=None):
    """Salva una nuova verifica nel database, includendo il nome del tecnico."""
    if verification_date is None:
        verification_date = datetime.now().strftime('%Y-%m-%d')

    results_json = json.dumps(results)
    visual_json = json.dumps(visual_inspection_data)
    mti_data = mti_info if isinstance(mti_info, dict) else {}

    conn = get_db_connection()
    try:
        conn.execute(
            # La lista delle colonne (11 totali)
            "INSERT INTO verifications (device_id, verification_date, profile_name, results_json, overall_status, visual_inspection_json, mti_instrument, mti_serial, mti_version, mti_cal_date, technician_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            # La tupla di valori (deve avere 11 elementi corrispondenti)
            (
                device_id, 
                verification_date, 
                profile_name, 
                results_json, 
                overall_status, 
                visual_json, 
                mti_data.get('instrument'), 
                mti_data.get('serial'), 
                mti_data.get('version'), 
                mti_data.get('cal_date'),
                technician_name # <-- VALORE CHE PROBABILMENTE MANCAVA
            )
        )
        conn.commit()
        logging.info(f"Verifica del {verification_date} salvata con successo per il dispositivo ID: {device_id}")
    except Exception as e:
        logging.error(f"Errore durante il salvataggio della verifica per il dispositivo ID {device_id}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()

def get_all_instruments():
    """Recupera tutti gli strumenti di misura dal database."""
    conn = get_db_connection()
    instruments = conn.execute("SELECT * FROM mti_instruments ORDER BY instrument_name").fetchall()
    conn.close()
    return instruments

def add_instrument(name, serial, version, cal_date):
    """Aggiunge un nuovo strumento."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO mti_instruments (instrument_name, serial_number, fw_version, calibration_date) VALUES (?, ?, ?, ?)",
        (name, serial, version, cal_date)
    )
    conn.commit()
    conn.close()

def update_instrument(instrument_id, name, serial, version, cal_date):
    """Aggiorna uno strumento esistente."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE mti_instruments SET instrument_name=?, serial_number=?, fw_version=?, calibration_date=? WHERE id=?",
        (name, serial, version, cal_date, instrument_id)
    )
    conn.commit()
    conn.close()

def delete_instrument(instrument_id):
    """Elimina uno strumento."""
    conn = get_db_connection()
    conn.execute("DELETE FROM mti_instruments WHERE id = ?", (instrument_id,))
    conn.commit()
    conn.close()

def set_default_instrument(instrument_id):
    """Imposta uno strumento come predefinito."""
    conn = get_db_connection()
    try:
        # Resetta tutti gli altri strumenti a non-predefinito
        conn.execute("UPDATE mti_instruments SET is_default = 0")
        # Imposta il nuovo strumento come predefinito
        conn.execute("UPDATE mti_instruments SET is_default = 1 WHERE id = ?", (instrument_id,))
        conn.commit()
    except Exception as e:
        logging.error("Errore nell'impostare lo strumento predefinito.", exc_info=True)
        conn.rollback()
    finally:
        conn.close()

def get_customer_by_id(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    return customer

def search_device_globally(search_term):
    """
    Cerca un dispositivo in tutto il database per matricola o inventario AMS.
    Restituisce la riga del dispositivo se trovato, altrimenti None.
    """
    conn = get_db_connection()
    # Cerca una corrispondenza esatta (più veloce se i numeri sono precisi)
    device = conn.execute(
        "SELECT * FROM devices WHERE serial_number = ? OR ams_inventory = ?",
        (search_term, search_term)
    ).fetchone()
    conn.close()
    return device

migrate_database()