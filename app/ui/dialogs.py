# app/ui/dialogs.py
import json
import logging
import pandas as pd
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QAbstractItemView, QFileDialog, QCheckBox, QTextEdit, QStyle, QHeaderView,
    QProgressDialog, QCalendarWidget)
from PySide6.QtCore import Qt, QThread, QDate, QSettings
from PySide6.QtGui import QColor

# Import locali dai nuovi moduli
from app.data_models import AppliedPart
# Assumiamo che i worker siano in file separati come definito
from app.workers.import_worker import ImportWorker
from app.workers.export_worker import DailyExportWorker
from app.workers.stm_import_worker import StmImportWorker # Modificheremo questo per gestire entrambi i casi
import database
import report_generator

# --- Finestre di Dialogo di Supporto ---

class ImportReportDialog(QDialog):
    """Finestra che mostra un report dettagliato (es. righe ignorate)."""
    def __init__(self, title, report_details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        label = QLabel("Le seguenti righe del file non sono state importate:")
        layout.addWidget(label)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText("\n".join(report_details))
        layout.addWidget(text_edit)
        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)

class DateSelectionDialog(QDialog):
    """Finestra di dialogo per la selezione di una singola data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleziona Data")
        layout = QVBoxLayout(self)
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        layout.addWidget(self.calendar)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def getSelectedDate(self):
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

class MappingDialog(QDialog):
    """Finestra di dialogo per mappare le colonne del file con i campi del DB."""
    def __init__(self, file_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mappatura Colonne Importazione")
        self.setMinimumWidth(450)
        self.required_fields = {
            'matricola': 'Matricola (S/N)', 
            'descrizione': 'Descrizione',
            'costruttore': 'Costruttore', 
            'modello': 'Modello',
            'reparto': 'Reparto (Opzionale)', 
            'inv_cliente': 'Inventario Cliente (Opzionale)',
            'inv_ams': 'Inventario AMS (Opzionale)',
            'verification_interval': 'Intervallo Verifica (Mesi, Opzionale)'
        }
        self.file_columns = ["<Nessuna>"] + file_columns
        self.combo_boxes = {}
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        info_label = QLabel("Associa le colonne del tuo file Excel con i campi del programma.\nI campi obbligatori sono Matricola e Descrizione.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        for key, display_name in self.required_fields.items():
            label = QLabel(f"{display_name}:")
            combo = QComboBox()
            combo.addItems(self.file_columns)
            form_layout.addRow(label, combo)
            self.combo_boxes[key] = combo
        layout.addLayout(form_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.try_auto_mapping()

    def try_auto_mapping(self):
        for key, combo in self.combo_boxes.items():
            for i, col_name in enumerate(self.file_columns):
                if key.replace("_", "") in col_name.lower().replace(" ", "").replace("/", ""):
                    combo.setCurrentIndex(i); break

    def get_mapping(self):
        mapping = {}
        for key, combo in self.combo_boxes.items():
            selected_col = combo.currentText()
            if selected_col != "<Nessuna>": mapping[key] = selected_col
        if 'matricola' not in mapping or 'descrizione' not in mapping:
            QMessageBox.warning(self, "Campi Mancanti", "Assicurati di aver mappato almeno i campi Matricola e Descrizione.")
            return None
        return mapping

# --- Finestre di Dialogo CRUD ---

class CustomerDialog(QDialog):
    def __init__(self, customer_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dettagli Cliente")
        data = customer_data or {}
        
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(customer_data['name'] if customer_data else "")
        self.address_edit = QLineEdit(customer_data['address'] if customer_data else "")
        self.phone_edit = QLineEdit(customer_data['phone'] if customer_data else "")
        self.email_edit = QLineEdit(customer_data['email'] if customer_data else "")
        
        layout.addRow("Nome:", self.name_edit)
        layout.addRow("Indirizzo:", self.address_edit)
        layout.addRow("Telefono:", self.phone_edit)
        layout.addRow("Email:", self.email_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "address": self.address_edit.text(),
            "phone": self.phone_edit.text(),
            "email": self.email_edit.text()
        }

class DeviceDialog(QDialog):
    def __init__(self, device_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dettagli Dispositivo")
        self.setMinimumWidth(500)
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # --- LOGICA CORRETTA PER LA GESTIONE DEI DATI ---
        # Usiamo un ternario per ogni campo per gestire sia la modifica che la nuova creazione
        self.serial_edit = QLineEdit(device_data['serial_number'] if device_data else "")
        self.desc_edit = QLineEdit(device_data['description'] if device_data else "")
        self.mfg_edit = QLineEdit(device_data['manufacturer'] if device_data else "")
        self.model_edit = QLineEdit(device_data['model'] if device_data else "")
        self.customer_inv_edit = QLineEdit(device_data['customer_inventory'] if device_data else "")
        self.ams_inv_edit = QLineEdit(device_data['ams_inventory'] if device_data else "")

        self.verification_interval_combo = QComboBox()
        self.verification_interval_combo.addItems(["Nessuno", "6", "12", "24", "36"])
        
        # Logica corretta anche per il campo intervallo
        if device_data and 'verification_interval' in device_data.keys() and device_data['verification_interval'] is not None:
            self.verification_interval_combo.setCurrentText(str(device_data['verification_interval']))
        
        form_layout.addRow("Numero di Serie:", self.serial_edit)
        form_layout.addRow("Descrizione:", self.desc_edit)
        form_layout.addRow("Costruttore:", self.mfg_edit)
        form_layout.addRow("Modello:", self.model_edit)
        form_layout.addRow("Inventario Cliente:", self.customer_inv_edit)
        form_layout.addRow("Inventario AMS:", self.ams_inv_edit)
        form_layout.addRow("Intervallo Verifica (Mesi):", self.verification_interval_combo)
        
        main_layout.addLayout(form_layout)
        
        pa_group = QGroupBox("Parti Applicate")
        pa_layout = QVBoxLayout()
        
        applied_parts_json = device_data['applied_parts_json'] if device_data and 'applied_parts_json' in device_data.keys() else '[]'
        try:
            self.applied_parts = [AppliedPart(**pa) for pa in json.loads(applied_parts_json)]
        except (json.JSONDecodeError, TypeError):
            self.applied_parts = []

        self.pa_table = QTableWidget(0, 2)
        self.pa_table.setHorizontalHeaderLabels(["Nome", "Tipo"])
        pa_layout.addWidget(self.pa_table)
        
        add_pa_layout = QHBoxLayout()
        self.pa_name_input = QLineEdit()
        self.pa_type_selector = QComboBox()
        self.pa_type_selector.addItems(["B", "BF", "CF"])
        add_pa_btn = QPushButton("Aggiungi P.A.")
        add_pa_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        add_pa_btn.clicked.connect(self.add_pa)
        
        add_pa_layout.addWidget(self.pa_name_input)
        add_pa_layout.addWidget(self.pa_type_selector)
        add_pa_layout.addWidget(add_pa_btn)
        
        pa_layout.addLayout(add_pa_layout)
        pa_group.setLayout(pa_layout)
        main_layout.addWidget(pa_group)
        self.load_pa_table()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def add_pa(self):
        name = self.pa_name_input.text()
        part_type = self.pa_type_selector.currentText()
        if name:
            self.applied_parts.append(AppliedPart(name, part_type))
            self.load_pa_table()
            self.pa_name_input.clear()

    def load_pa_table(self):
        self.pa_table.setRowCount(0)
        for pa in self.applied_parts:
            row = self.pa_table.rowCount()
            self.pa_table.insertRow(row)
            self.pa_table.setItem(row, 0, QTableWidgetItem(pa.name))
            self.pa_table.setItem(row, 1, QTableWidgetItem(pa.part_type))

    def get_data(self):
        return {
            "serial": self.serial_edit.text(),
            "desc": self.desc_edit.text(),
            "mfg": self.mfg_edit.text(),
            "model": self.model_edit.text(),
            "customer_inv": self.customer_inv_edit.text(),
            "ams_inv": self.ams_inv_edit.text(),
            "applied_parts": self.applied_parts,
            "verification_interval": self.verification_interval_combo.currentText()
        }


class VisualInspectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Ispezione Visiva Preliminare"); self.setMinimumWidth(500)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Controllare tutti i punti seguenti prima di procedere con le misure elettriche."))
        self.checklist_items = ["Involucro e parti meccaniche integri, senza danni.", "Cavo di alimentazione e spina senza danneggiamenti.", "Cavi paziente, connettori e accessori integri.", "Marcature e targhette di sicurezza leggibili.", "Assenza di sporcizia o segni di versamento di liquidi.", "Fusibili (se accessibili) di tipo e valore corretti." ]
        self.checkboxes = [QCheckBox(item) for item in self.checklist_items]
        for cb in self.checkboxes: cb.stateChanged.connect(self.check_all_selected); layout.addWidget(cb)
        layout.addWidget(QLabel("\nNote aggiuntive:")); self.notes_edit = QTextEdit(); layout.addWidget(self.notes_edit)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); self.buttons.button(QDialogButtonBox.Ok).setText("Conferma e Procedi"); self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons); self.check_all_selected()
    def check_all_selected(self): self.buttons.button(QDialogButtonBox.Ok).setEnabled(all(cb.isChecked() for cb in self.checkboxes))
    def get_data(self): return {"notes": self.notes_edit.toPlainText(), "checklist": [{"item": text, "checked": cb.isChecked()} for text, cb in zip(self.checklist_items, self.checkboxes)]}

class VerificationViewerDialog(QDialog):
    def __init__(self, verification_data, parent=None):
        super().__init__(parent); self.setWindowTitle(f"Dettagli Verifica del {verification_data['verification_date']}"); self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self); info_label = QLabel(f"<b>Profilo:</b> {verification_data['profile_name']}<br><b>Esito Globale:</b> {verification_data['overall_status']}")
        layout.addWidget(info_label)
        if 'visual_inspection_json' in verification_data.keys() and verification_data['visual_inspection_json']:
            visual_group = QGroupBox("Ispezione Visiva")
            visual_layout = QVBoxLayout()
            visual_data = json.loads(verification_data['visual_inspection_json'])
            for item in visual_data.get('checklist', []): visual_layout.addWidget(QLabel(f"- {item['item']} [✓]"))
            if visual_data.get('notes'): visual_layout.addWidget(QLabel(f"\n<b>Note:</b> {visual_data['notes']}"))
            visual_group.setLayout(visual_layout); layout.addWidget(visual_group)
        results_table = QTableWidget(); results_table.setColumnCount(4); results_table.setHorizontalHeaderLabels(["Test / P.A.", "Limite", "Valore", "Esito"]); layout.addWidget(results_table)
        results = json.loads(verification_data['results_json'])
        for res in results:
            row = results_table.rowCount(); results_table.insertRow(row)
            results_table.setItem(row, 0, QTableWidgetItem(res['name'])); results_table.setItem(row, 1, QTableWidgetItem(res['limit']))
            results_table.setItem(row, 2, QTableWidgetItem(res['value']))
            is_passed = res['passed']; passed_item = QTableWidgetItem("PASSATO" if is_passed else "FALLITO")
            passed_item.setBackground(QColor('#D4EDDA') if is_passed else QColor('#F8D7DA')); results_table.setItem(row, 3, passed_item)
        results_table.resizeColumnsToContents()
        close_button = QPushButton("Chiudi"); close_button.clicked.connect(self.accept); layout.addWidget(close_button)


# --- CLASSE DB MANAGER ---
class DbManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Gestione Anagrafiche")
    
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Layout per i pulsanti di azione in alto
        top_actions_layout = QHBoxLayout()
        self.import_button = QPushButton("Importa Dispositivi da CSV/Excel")
        self.import_button.setObjectName("import_button")
        self.import_button.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))
        self.import_button.clicked.connect(self.import_from_file)
        top_actions_layout.addWidget(self.import_button)


        # --- NUOVO PULSANTE IMPORTA DA ARCHIVIO ---
        self.import_stm_button = QPushButton("Importa da Archivio (.stm)...")
        self.import_stm_button.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        self.import_stm_button.clicked.connect(self.import_from_stm)
        top_actions_layout.addWidget(self.import_stm_button)
        # ---

        # MANTENIAMO SOLO IL PULSANTE DI ESPORTAZIONE PER DATA
        self.export_daily_button = QPushButton("Esporta Verifiche per Data...")
        self.export_daily_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.export_daily_button.clicked.connect(self.export_daily_verifications)
        top_actions_layout.addWidget(self.export_daily_button)
        
        top_actions_layout.addStretch()
        main_layout.addLayout(top_actions_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        customers_group = QGroupBox("Clienti")
        cust_layout = QVBoxLayout()
        self.customer_search_box = QLineEdit()
        self.customer_search_box.setPlaceholderText("Cerca cliente per nome...")
        self.customer_search_box.textChanged.connect(self.filter_customers)
        self.customer_table = QTableWidget(0, 5)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Nome", "Indirizzo", "Telefono", "Email"])
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customer_table.itemSelectionChanged.connect(self.customer_selected)
        header_clienti = self.customer_table.horizontalHeader()
        header_clienti.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        header_clienti.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)         # Nome
        header_clienti.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)         # Indirizzo
        header_clienti.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)      # Telefono
        header_clienti.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Email
        cust_buttons_layout, _ = self.create_buttons("Aggiungi Cliente", "Modifica Cliente", "Elimina Cliente", self.add_customer, self.edit_customer, self.delete_customer)
        
        # --- NUOVO PULSANTE PER ELIMINAZIONE MASSIVA ---
        self.delete_all_devices_button = QPushButton("Elimina Tutti i Dispositivi")
        self.delete_all_devices_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.delete_all_devices_button.setEnabled(False) # Inizialmente disabilitato
        self.delete_all_devices_button.clicked.connect(self.delete_all_devices_for_selected_customer)
        
        # Aggiungiamo il nuovo pulsante al layout esistente
        cust_buttons_layout.insertWidget(2, self.delete_all_devices_button) # Lo inserisce prima del pulsante "Elimina Cliente"
        # --- FINE AGGIUNTA PULSANTE ---
        
        cust_layout.addWidget(self.customer_search_box)
        cust_layout.addWidget(self.customer_table)
        cust_layout.addLayout(cust_buttons_layout)
        customers_group.setLayout(cust_layout)
        top_layout.addWidget(customers_group, 1)

        self.devices_group = QGroupBox("Dispositivi")
        dev_layout = QVBoxLayout()
        self.device_search_box = QLineEdit()
        self.device_search_box.setPlaceholderText("Cerca per descrizione, S/N, modello...")
        self.device_search_box.textChanged.connect(self.filter_devices)
        self.device_table = QTableWidget(0, 7)
        self.device_table.setHorizontalHeaderLabels(["ID", "Descrizione", "S/N", "Costruttore", "Modello", "Inv. Cliente", "Inv. AMS"])
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.itemSelectionChanged.connect(self.device_selected)
        header_dispositivi = self.device_table.horizontalHeader()
        header_dispositivi.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header_dispositivi.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_dispositivi.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header_dispositivi.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header_dispositivi.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header_dispositivi.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_dispositivi.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        dev_buttons_layout, buttons = self.create_buttons("Aggiungi Dispositivo", "Modifica Dispositivo", "Elimina Dispositivo", self.add_device, self.edit_device, self.delete_device)
        self.add_dev_btn, self.edit_dev_btn, self.del_dev_btn = buttons
        dev_layout.addWidget(self.device_search_box)
        dev_layout.addWidget(self.device_table)
        dev_layout.addLayout(dev_buttons_layout)
        self.devices_group.setLayout(dev_layout)
        top_layout.addWidget(self.devices_group, 2)
        main_layout.addLayout(top_layout)

        self.verifications_group = QGroupBox("Storico Verifiche")
        verif_layout = QVBoxLayout()
        self.verifications_table = QTableWidget(0, 3)
        self.verifications_table.setHorizontalHeaderLabels(["ID", "Data", "Esito Globale"])
        self.verifications_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verifications_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        verif_buttons_layout = QHBoxLayout()
        self.view_verif_btn = QPushButton("Visualizza Dettagli")
        self.view_verif_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.view_verif_btn.clicked.connect(self.view_verification_details)
        self.gen_report_btn = QPushButton("Genera Report PDF")
        self.gen_report_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.gen_report_btn.clicked.connect(self.generate_old_report)
        verif_buttons_layout.addStretch()
        verif_buttons_layout.addWidget(self.view_verif_btn)
        verif_buttons_layout.addWidget(self.gen_report_btn)
        verif_layout.addWidget(self.verifications_table)
        verif_layout.addLayout(verif_buttons_layout)
        self.verifications_group.setLayout(verif_layout)
        main_layout.addWidget(self.verifications_group)
        self.load_customers_table()

    def create_buttons(self, add_text, edit_text, del_text, add_fn, edit_fn, del_fn):
        layout = QHBoxLayout(); add = QPushButton(add_text); add.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder)); add.clicked.connect(add_fn)
        edit = QPushButton(edit_text); edit.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)); edit.clicked.connect(edit_fn)
        delete = QPushButton(del_text); delete.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon)); delete.clicked.connect(del_fn)
        layout.addWidget(add); layout.addWidget(edit); layout.addWidget(delete); return layout, (add, edit, delete)

    def import_from_file(self):
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Cliente non Selezionato", "Per favore, seleziona un cliente dalla tabella prima di importare i dispositivi.")
            return
        selected_customer_id = int(self.customer_table.item(selected_rows[0].row(), 0).text())
        selected_customer_name = self.customer_table.item(selected_rows[0].row(), 1).text()
        reply = QMessageBox.question(self, 'Conferma Importazione', f"Stai per importare i dispositivi per il cliente:\n\n<b>{selected_customer_name}</b>\n\nVuoi continuare?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No: return
        filename, _ = QFileDialog.getOpenFileName(self, "Seleziona File da Importare", "", "File Excel/CSV (*.xlsx *.csv)")
        if not filename: return
        try:
            df_headers = pd.read_csv(filename, sep=';', dtype=str, nrows=0) if filename.endswith('.csv') else pd.read_excel(filename, dtype=str, nrows=0)
            file_columns = df_headers.columns.tolist()
        except Exception as e:
            QMessageBox.critical(self, "Errore Lettura File", f"Impossibile leggere le intestazioni dal file:\n{e}"); return
        map_dialog = MappingDialog(file_columns, self)
        if map_dialog.exec() == QDialog.Accepted:
            mapping = map_dialog.get_mapping()
            if mapping is None: return
            self.progress_dialog = QProgressDialog("Importazione dei dati...", "Annulla", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal); self.progress_dialog.setWindowTitle("Importazione in Corso"); self.progress_dialog.setValue(0)
            self.thread = QThread(); self.worker = ImportWorker(filename, mapping, selected_customer_id)
            self.worker.moveToThread(self.thread)
            self.worker.progress_updated.connect(self.progress_dialog.setValue); self.progress_dialog.canceled.connect(self.worker.cancel)
            self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.on_import_finished); self.worker.error.connect(self.on_import_error)
            self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(self.progress_dialog.close)
            self.thread.start(); self.progress_dialog.exec()

    def on_import_finished(self, added_count, skipped_rows_details, status):
        self.load_customers_table()
        if status == "Annullato":
            QMessageBox.warning(self, "Importazione Annullata", "L'operazione di importazione è stata annullata dall'utente."); return
        skipped_count = len(skipped_rows_details)
        summary_message = f"Importazione terminata.\n\n- Dispositivi aggiunti: {added_count}\n- Righe ignorate: {skipped_count}"
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Importazione Completata"); msg_box.setText(summary_message)
        msg_box.setIcon(QMessageBox.Information); ok_button = msg_box.addButton("OK", QMessageBox.AcceptRole)
        if skipped_count > 0:
            details_button = msg_box.addButton("Visualizza Dettagli", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton() == details_button:
                report_dialog = ImportReportDialog("Dettaglio Righe Ignorate", skipped_rows_details, self); report_dialog.exec()
        else:
            msg_box.exec()

    def on_import_error(self, error_message):
        self.progress_dialog.close(); QMessageBox.critical(self, "Errore Importazione", error_message)

    def export_daily_verifications(self):
        date_dialog = DateSelectionDialog(self)
        if date_dialog.exec() == QDialog.Accepted:
            target_date = date_dialog.getSelectedDate()
            
            default_filename = f"Export_Verifiche_{target_date.replace('-', '')}.stm"
            output_path, _ = QFileDialog.getSaveFileName(self, "Salva Esportazione Verifiche per Data", default_filename, "File Safety Test Manager (*.stm)")

            if not output_path:
                logging.info("Esportazione giornaliera annullata dall'utente.")
                return

            self.export_thread = QThread()
            # Assumiamo che il worker si chiami DailyExportWorker come definito prima
            self.export_worker = DailyExportWorker(target_date, output_path)
            self.export_worker.moveToThread(self.export_thread)
            
            self.export_thread.started.connect(self.export_worker.run)
            self.export_worker.finished.connect(self.on_export_finished)
            self.export_worker.error.connect(self.on_export_error)
            
            self.export_worker.finished.connect(self.export_thread.quit)
            self.export_worker.finished.connect(self.export_worker.deleteLater)
            self.export_thread.finished.connect(self.export_thread.deleteLater)
            
            self.export_thread.start()
            
            # --- CORREZIONE QUI ---
            self.export_daily_button.setEnabled(False)
            self.setWindowTitle("Manager Anagrafiche (Esportazione in corso...)")

    def on_export_finished(self, status, message):
        self.setWindowTitle("Manager Anagrafiche")
        # --- CORREZIONE QUI ---
        self.export_daily_button.setEnabled(True)
        if status == "Success":
            QMessageBox.information(self, "Esportazione Completata", message)
        else:
            QMessageBox.warning(self, "Esportazione", message)

    def on_export_error(self, error_message):
        self.setWindowTitle("Manager Anagrafiche")
        # --- CORREZIONE QUI ---
        self.export_daily_button.setEnabled(True)
        QMessageBox.critical(self, "Errore Esportazione", error_message)

    def filter_customers(self): self.load_customers_table(self.customer_search_box.text())
    def filter_devices(self): self.customer_selected()

    def load_customers_table(self, search_text=None):
        self.customer_table.setRowCount(0)
        # Aggiungi i nuovi campi alla lista delle colonne da visualizzare
        columns_to_display = ['id', 'name', 'address', 'phone', 'email']
        for customer in database.get_all_customers(search_query=search_text):
            row = self.customer_table.rowCount()
            self.customer_table.insertRow(row)
            for i, col_name in enumerate(columns_to_display):
                value_to_show = str(customer[col_name]) if col_name in customer.keys() and customer[col_name] is not None else ''
                self.customer_table.setItem(row, i, QTableWidgetItem(value_to_show))
        self.devices_group.setTitle("Dispositivi")
        self.device_table.setRowCount(0) 
        self.set_device_buttons_enabled(False)
        self.verifications_group.setTitle("Storico Verifiche")
        self.verifications_table.setRowCount(0) 
        self.set_verification_buttons_enabled(False)

    def customer_selected(self):
        self.verifications_table.setRowCount(0); 
        self.set_verification_buttons_enabled(False)
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows: 
            self.set_device_buttons_enabled(False)
            self.export_daily_button.setEnabled(False)
            self.delete_all_devices_button.setEnabled(False)
            return
        self.export_daily_button.setEnabled(True)
        self.delete_all_devices_button.setEnabled(True)
        customer_id = int(self.customer_table.item(selected_rows[0].row(), 0).text()) 
        customer_name = self.customer_table.item(selected_rows[0].row(), 1).text()
        self.devices_group.setTitle(f"Dispositivi per '{customer_name}'")
        self.load_devices_table(customer_id); 
        self.set_device_buttons_enabled(True)

    def load_devices_table(self, customer_id):
        self.device_table.setRowCount(0)
        search_text = self.device_search_box.text()
        for device in database.get_devices_for_customer(customer_id, search_query=search_text):
            row = self.device_table.rowCount(); self.device_table.insertRow(row)
            for i, col in enumerate(['id', 'description', 'serial_number', 'manufacturer', 'model', 'customer_inventory', 'ams_inventory']): self.device_table.setItem(row, i, QTableWidgetItem(str(device[col])))

    def device_selected(self):
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows: self.verifications_table.setRowCount(0); self.set_verification_buttons_enabled(False); return
        device_id = int(self.device_table.item(selected_rows[0].row(), 0).text()); device_desc = self.device_table.item(selected_rows[0].row(), 1).text()
        self.verifications_group.setTitle(f"Storico Verifiche per '{device_desc}'"); self.load_verifications_table(device_id)

    def load_verifications_table(self, device_id):
        self.verifications_table.setRowCount(0); self.set_verification_buttons_enabled(False)
        for verif in database.get_verifications_for_device(device_id):
            self.set_verification_buttons_enabled(True); row = self.verifications_table.rowCount(); self.verifications_table.insertRow(row)
            self.verifications_table.setItem(row, 0, QTableWidgetItem(str(verif['id']))); self.verifications_table.setItem(row, 1, QTableWidgetItem(verif['verification_date']))
            status_item = QTableWidgetItem(verif['overall_status']); status_item.setBackground(QColor('#D4EDDA') if verif['overall_status'] == 'PASSATO' else QColor('#F8D7DA'))
            self.verifications_table.setItem(row, 2, status_item)

    def view_verification_details(self):
        selected_verif_rows = self.verifications_table.selectionModel().selectedRows(); selected_dev_rows = self.device_table.selectionModel().selectedRows()
        if not selected_verif_rows or not selected_dev_rows: return
        verif_id = int(self.verifications_table.item(selected_verif_rows[0].row(), 0).text()); device_id = int(self.device_table.item(selected_dev_rows[0].row(), 0).text())
        verifications = database.get_verifications_for_device(device_id)
        verification_data = next((v for v in verifications if v['id'] == verif_id), None)
        if verification_data: dialog = VerificationViewerDialog(verification_data, self); dialog.exec()

    def generate_old_report(self):
        selected_verif_rows = self.verifications_table.selectionModel().selectedRows() 
        selected_dev_rows = self.device_table.selectionModel().selectedRows()
        if not selected_verif_rows or not selected_dev_rows: 
            QMessageBox.warning(self, "Attenzione", "Selezionare un dispositivo e una verifica dalla lista."); return
        verif_id = int(self.verifications_table.item(selected_verif_rows[0].row(), 0).text())
        dev_id = int(self.device_table.item(selected_dev_rows[0].row(), 0).text())
        device_info = database.get_device_by_id(dev_id)
        customer_info = next((c for c in database.get_all_customers() 
                              if c['id'] == device_info['customer_id']), None)
        verification = next((v for v in database.get_verifications_for_device(dev_id) 
                             if v['id'] == verif_id), None)
        if not (device_info and customer_info and verification): 
            QMessageBox.critical(self, "Errore", "Impossibile recuperare tutti i dati per il report.")
            return
        try:
            technician_name = verification['technician_name'] or "N/D"
        except IndexError: # Il campo potrebbe non esistere nei vecchi record letti da get_verifications_for_device
             technician_name = "N/D"

        mti_info = { "instrument": verification['mti_instrument'], 
                    "serial": verification['mti_serial'], 
                    "version": verification['mti_version'], 
                    "cal_date": verification['mti_cal_date']}
        report_settings = {"logo_path": self.main_window.logo_path}
        results_data = json.loads(verification['results_json']) if verification['results_json'] else []
        visual_data = json.loads(verification['visual_inspection_json']) if 'visual_inspection_json' in verification.keys() and verification['visual_inspection_json'] else {}
        verification_data = {'date': verification['verification_date'], 'profile_name': verification['profile_name'], 'overall_status': verification['overall_status'], 'results': results_data, 'visual_inspection_data': visual_data}
        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", f"./Report_{device_info['serial_number']}_{verification['verification_date']}.pdf", "PDF Files (*.pdf)")
        if filename: report_generator.create_report(filename, device_info, customer_info, mti_info, report_settings, verification_data, technician_name); QMessageBox.information(self, "Successo", f"Report generato:\n{filename}")

    def set_verification_buttons_enabled(self, enabled): self.view_verif_btn.setEnabled(enabled); self.gen_report_btn.setEnabled(enabled)
    def set_device_buttons_enabled(self, enabled): self.add_dev_btn.setEnabled(enabled); self.edit_dev_btn.setEnabled(enabled); self.del_dev_btn.setEnabled(enabled)
    def add_customer(self):
        dialog = CustomerDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if data['name']: database.add_customer(**data); self.load_customers_table()
            else: QMessageBox.warning(self, "Errore", "Il nome del cliente non può essere vuoto.")
    def edit_customer(self):
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows: return
        row_idx = selected_rows[0].row()
        cust_id = int(self.customer_table.item(row_idx, 0).text())
        
        # Recupera i dati dal database per essere sicuro di avere la versione più aggiornata
        customer_data_from_db = database.get_customer_by_id(cust_id)
        if not customer_data_from_db:
             QMessageBox.critical(self, "Errore", "Impossibile trovare i dati del cliente selezionato.")
             return
        
        # Passa l'oggetto sqlite3.Row direttamente alla dialog, che ora sa come gestirlo
        dialog = CustomerDialog(customer_data_from_db, self)
        
        if dialog.exec():
            data = dialog.get_data()
            if data['name']:
                database.update_customer(cust_id, **data)
                self.load_customers_table(self.customer_search_box.text())

    def delete_customer(self):
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows: return
        cust_id = int(self.customer_table.item(selected_rows[0].row(), 0).text())
        reply = QMessageBox.question(self, 'Conferma', 'Eliminare il cliente? (Possibile solo se non ha dispositivi)')
        if reply == QMessageBox.Yes:
            success, message = database.delete_customer(cust_id)
            if success: self.load_customers_table()
            else: QMessageBox.critical(self, "Errore", message)
    def add_device(self):
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows: return
        cust_id = int(self.customer_table.item(selected_rows[0].row(), 0).text())
        dialog = DeviceDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if data['serial']: database.add_device(cust_id, **data); self.load_devices_table(cust_id)
            else: QMessageBox.warning(self, "Errore", "Il numero di serie non può essere vuoto.")
    def edit_device(self):
        selected_dev_rows = self.device_table.selectionModel().selectedRows(); selected_cust_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_dev_rows or not selected_cust_rows: return
        dev_id = int(self.device_table.item(selected_dev_rows[0].row(), 0).text()); cust_id = int(self.customer_table.item(selected_cust_rows[0].row(), 0).text())
        device_data = database.get_device_by_id(dev_id); dialog = DeviceDialog(device_data, self)
        if dialog.exec(): data = dialog.get_data(); database.update_device(dev_id, **data); self.load_devices_table(cust_id)
    def delete_device(self):
        selected_dev_rows = self.device_table.selectionModel().selectedRows(); selected_cust_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_dev_rows or not selected_cust_rows: return
        dev_id = int(self.device_table.item(selected_dev_rows[0].row(), 0).text()); cust_id = int(self.customer_table.item(selected_cust_rows[0].row(), 0).text())
        reply = QMessageBox.question(self, 'Conferma', 'Eliminare questo dispositivo e tutte le sue verifiche?')
        if reply == QMessageBox.Yes: database.delete_device(dev_id); self.load_devices_table(cust_id)
    
    def delete_all_devices_for_selected_customer(self):
        """Chiede conferma ed elimina tutti i dispositivi per il cliente selezionato."""
        selected_rows = self.customer_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        customer_id = int(self.customer_table.item(selected_rows[0].row(), 0).text())
        customer_name = self.customer_table.item(selected_rows[0].row(), 1).text()
        
        # Recupera il numero di dispositivi per mostrarlo nel messaggio
        device_count = database.get_device_count_for_customer(customer_id)

        if device_count == 0:
            QMessageBox.information(self, "Nessun Dispositivo", f"Il cliente '{customer_name}' non ha dispositivi da eliminare.")
            return

        # Messaggio di conferma critico
        reply = QMessageBox.question(self, 'Conferma Eliminazione Massiva',
                                     f"<b>ATTENZIONE: OPERAZIONE IRREVERSIBILE!</b>\n\n"
                                     f"Sei assolutamente sicuro di voler eliminare tutti i <b>{device_count}</b> dispositivi "
                                     f"e le relative verifiche per il cliente '{customer_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logging.warning(f"Avvio eliminazione massiva di {device_count} dispositivi per il cliente ID {customer_id}")
            success = database.delete_all_devices_for_customer(customer_id)
            if success:
                QMessageBox.information(self, "Operazione Completata", "Tutti i dispositivi del cliente sono stati eliminati con successo.")
                # Aggiorna la tabella dei dispositivi, che ora sarà vuota
                self.load_devices_table(customer_id)
            else:
                QMessageBox.critical(self, "Errore", "Si è verificato un errore durante l'eliminazione dei dispositivi. Controllare i log.")

     # --- NUOVI METODI PER L'IMPORTAZIONE DA ARCHIVIO ---
    def import_from_stm(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleziona Archivio da Importare", "", "File Safety Test Manager (*.stm)")
        if not filepath:
            return

        self.import_thread = QThread()
        self.import_worker = StmImportWorker(filepath)
        self.import_worker.moveToThread(self.import_thread)

        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.finished.connect(self.on_stm_import_finished)
        self.import_worker.error.connect(self.on_import_error) # Possiamo riusare lo slot di errore

        self.import_worker.finished.connect(self.import_thread.quit)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)

        self.import_thread.start()
        # Potremmo aggiungere una progress dialog anche qui se l'operazione è lunga
        self.setWindowTitle("Manager Anagrafiche (Importazione da archivio in corso...)")

    def on_stm_import_finished(self, verif_imported, verif_skipped, dev_new, cust_new):
        self.setWindowTitle("Manager Anagrafiche")
        self.load_customers_table() # Ricarica tutto per mostrare i nuovi dati

        summary_message = f"Importazione da archivio completata.\n\n" \
                          f"- Verifiche importate: {verif_imported}\n" \
                          f"- Verifiche saltate (già presenti): {verif_skipped}\n" \
                          f"- Nuovi dispositivi creati: {dev_new}\n"
                          # f"- Nuovi clienti creati: {cust_new}" # Potremmo aggiungerlo se necessario

        QMessageBox.information(self, "Importazione Completata", summary_message)
class InstrumentDetailDialog(QDialog):
    """Dialog per inserire/modificare i dettagli di un singolo strumento."""
    def __init__(self, instrument_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dettagli Strumento di Misura")
        data = instrument_data or {}
        
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(data.get('instrument_name', ''))
        self.serial_edit = QLineEdit(data.get('serial_number', ''))
        self.version_edit = QLineEdit(data.get('fw_version', ''))
        self.cal_date_edit = QLineEdit(data.get('calibration_date', ''))
        
        layout.addRow("Nome Strumento:", self.name_edit)
        layout.addRow("Numero di Serie:", self.serial_edit)
        layout.addRow("Versione Firmware:", self.version_edit)
        layout.addRow("Data Calibrazione:", self.cal_date_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "serial": self.serial_edit.text(),
            "version": self.version_edit.text(),
            "cal_date": self.cal_date_edit.text()
        }

class InstrumentManagerDialog(QDialog):
    """Dialog per visualizzare e gestire la lista di strumenti."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Anagrafica Strumenti")
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome Strumento", "Seriale", "Versione FW", "Data Cal."])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Aggiungi"); add_btn.clicked.connect(self.add_instrument)
        edit_btn = QPushButton("Modifica"); edit_btn.clicked.connect(self.edit_instrument)
        delete_btn = QPushButton("Elimina"); delete_btn.clicked.connect(self.delete_instrument)
        default_btn = QPushButton("Imposta come Predefinito"); default_btn.clicked.connect(self.set_default)
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(default_btn)
        layout.addLayout(buttons_layout)
        
        self.load_instruments()

    def load_instruments(self):
        self.table.setRowCount(0)
        for instrument in database.get_all_instruments():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(instrument['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(instrument['instrument_name']))
            self.table.setItem(row, 2, QTableWidgetItem(instrument['serial_number']))
            self.table.setItem(row, 3, QTableWidgetItem(instrument['fw_version']))
            self.table.setItem(row, 4, QTableWidgetItem(instrument['calibration_date']))
            if instrument['is_default']:
                for col in range(5): self.table.item(row, col).setBackground(QColor("#E0F7FA"))

    def add_instrument(self):
        dialog = InstrumentDetailDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data['name']:
                database.add_instrument(**data)
                self.load_instruments()

    def edit_instrument(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return
        row_idx = selected_rows[0].row()
        inst_id = int(self.table.item(row_idx, 0).text())
        
        inst_data = {
            'instrument_name': self.table.item(row_idx, 1).text(),
            'serial_number': self.table.item(row_idx, 2).text(),
            'fw_version': self.table.item(row_idx, 3).text(),
            'calibration_date': self.table.item(row_idx, 4).text()
        }
        
        dialog = InstrumentDetailDialog(inst_data, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            database.update_instrument(inst_id, **data)
            self.load_instruments()

    def delete_instrument(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return
        inst_id = int(self.table.item(selected_rows[0].row(), 0).text())
        reply = QMessageBox.question(self, "Conferma", "Eliminare lo strumento selezionato?")
        if reply == QMessageBox.Yes:
            database.delete_instrument(inst_id)
            self.load_instruments()
            
    def set_default(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return
        inst_id = int(self.table.item(selected_rows[0].row(), 0).text())
        database.set_default_instrument(inst_id)
        self.load_instruments()

class InstrumentSelectionDialog(QDialog):
    """Dialog per selezionare lo strumento e inserire il nome del tecnico."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleziona Strumento e Tecnico")
        self.settings = QSettings("MyCompany", "SafetyTester") # Per ricordare l'ultimo tecnico
        
        self.instruments = database.get_all_instruments()
        self.selected_instrument = None
        
        layout = QFormLayout(self)
        
        # --- Campo Selezione Strumento (invariato) ---
        self.combo = QComboBox()
        default_idx = -1
        for i, instrument in enumerate(self.instruments):
            self.combo.addItem(f"{instrument['instrument_name']} (S/N: {instrument['serial_number']})", instrument['id'])
            if instrument['is_default']:
                default_idx = i
        if default_idx != -1: self.combo.setCurrentIndex(default_idx)
        layout.addRow("Strumento:", self.combo)

        # --- NUOVO: Campo Nome Tecnico ---
        self.technician_name_edit = QLineEdit()
        # Pre-compila con l'ultimo nome usato per comodità
        last_technician = self.settings.value("last_technician_name", "")
        self.technician_name_edit.setText(last_technician)
        layout.addRow("Nome Tecnico:", self.technician_name_edit)
        # --- FINE NUOVO CAMPO ---
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getSelectedInstrumentData(self):
        # ... (metodo invariato) ...
        if not self.instruments: return None
        selected_id = self.combo.currentData()
        for instrument in self.instruments:
            if instrument['id'] == selected_id:
                return {"instrument": instrument['instrument_name'], "serial": instrument['serial_number'], "version": instrument['fw_version'], "cal_date": instrument['calibration_date']}
        return None

    def getTechnicianName(self):
        """Restituisce il nome del tecnico e lo salva per la prossima volta."""
        name = self.technician_name_edit.text()
        self.settings.setValue("last_technician_name", name) # Salva il nome
        return name