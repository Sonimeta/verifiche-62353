# app/workers/import_worker.py
import pandas as pd
from PySide6.QtCore import QObject, Signal
import database
import logging

class ImportWorker(QObject):
    # Segnale per aggiornare la progress bar (emette una percentuale 0-100)
    progress_updated = Signal(int)
    
    # Il segnale di fine ora include uno stato ("Completato", "Annullato")
    finished = Signal(int, list, str) 
    
    error = Signal(str)

    def __init__(self, filename, mapping, customer_id):
        super().__init__()
        self.filename = filename
        self.mapping = mapping
        self.customer_id = customer_id
        self._is_cancelled = False # Flag per gestire l'annullamento

    def cancel(self):
        """Metodo pubblico (slot) per richiedere l'annullamento."""
        logging.warning("Richiesta di annullamento dell'importazione ricevuta.")
        self._is_cancelled = True

    def run(self):
        try:
            if self.filename.endswith('.csv'):
                df = pd.read_csv(self.filename, sep=';', dtype=str).fillna('')
            else:
                df = pd.read_excel(self.filename, dtype=str).fillna('')
        except Exception as e:
            self.error.emit(f"Impossibile leggere il file:\n{e}")
            return
            
        added_count = 0
        skipped_rows_details = []
        total_rows = len(df)

        for index, row in df.iterrows():
            # Controlla ad ogni ciclo se l'operazione è stata annullata
            if self._is_cancelled:
                break # Esce dal ciclo

            excel_row_num = index + 2
            serial_number = row.get(self.mapping.get('matricola'))

            if not serial_number:
                skipped_rows_details.append(f"Riga {excel_row_num}: Matricola mancante.")
                continue
            
            if database.device_exists(serial_number):
                skipped_rows_details.append(f"Riga {excel_row_num}: Matricola '{serial_number}' esiste già nel database.")
                continue

            description = row.get(self.mapping.get('descrizione'), '')
            if not description:
                skipped_rows_details.append(f"Riga {excel_row_num}: Descrizione mancante.")
                continue
            
            department = row.get(self.mapping.get('reparto'), '')
            if department:
                description = f"{description} ({department})"
            
            interval_value = row.get(self.mapping.get('verification_interval'), None)

            database.add_device(
                customer_id=self.customer_id,
                serial=serial_number,
                desc=description,
                mfg=row.get(self.mapping.get('costruttore'), ''),
                model=row.get(self.mapping.get('modello'), ''),
                customer_inv=row.get(self.mapping.get('inv_cliente'), ''),
                ams_inv=row.get(self.mapping.get('inv_ams'), ''),
                verification_interval=interval_value,
                applied_parts=[]
            )
            added_count += 1
            
            # Calcola e emetti il progresso
            progress_percent = int(((index + 1) / total_rows) * 100)
            self.progress_updated.emit(progress_percent)
        
        # Determina lo stato finale e emetti il segnale di completamento
        status = "Annullato" if self._is_cancelled else "Completato"
        self.finished.emit(added_count, skipped_rows_details, status)