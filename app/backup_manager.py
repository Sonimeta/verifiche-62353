# app/backup_manager.py
import os
import shutil
import logging
from datetime import datetime

DB_FILE = "verifiche.db"
BACKUP_DIR = "backups"
BACKUP_RETENTION_COUNT = 10  # Numero di backup da conservare

def create_backup():
    """Crea un backup del file del database con un timestamp."""
    if not os.path.exists(DB_FILE):
        logging.warning(f"File database '{DB_FILE}' non trovato. Backup saltato.")
        return

    try:
        # Crea la cartella dei backup se non esiste
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Definisci il nome del file di backup
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"verifiche_backup_{timestamp}.db.bak"
        backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

        # Copia il file del database nella cartella dei backup
        shutil.copy2(DB_FILE, backup_filepath)
        logging.info(f"Backup del database creato con successo: {backup_filepath}")

        # Pulisci i vecchi backup
        rotate_backups()

    except Exception as e:
        logging.error("Errore durante la creazione del backup del database.", exc_info=True)

def rotate_backups():
    """Elimina i backup più vecchi, conservando solo il numero definito in BACKUP_RETENTION_COUNT."""
    try:
        backups = sorted(
            [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".bak")],
            key=os.path.getmtime
        )
        
        if len(backups) > BACKUP_RETENTION_COUNT:
            num_to_delete = len(backups) - BACKUP_RETENTION_COUNT
            logging.info(f"Trovati {len(backups)} backup. Rimuovendo i {num_to_delete} più vecchi.")
            for f in backups[:num_to_delete]:
                os.remove(f)
                logging.info(f"Vecchio backup rimosso: {f}")
    except Exception as e:
        logging.error("Errore durante la rotazione dei vecchi backup.", exc_info=True)

def restore_from_backup(backup_path):
    """Ripristina il database da un file di backup, sovrascrivendo quello corrente."""
    try:
        shutil.copy2(backup_path, DB_FILE)
        logging.warning(f"Database ripristinato con successo dal file: {backup_path}")
        return True
    except Exception as e:
        logging.critical(f"Errore critico durante il ripristino dal backup: {backup_path}", exc_info=True)
        return False