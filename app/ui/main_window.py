# app/ui/main_window.py
import sys
import logging
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QComboBox, QGroupBox, QFormLayout, QDialog,
    QMessageBox, QFileDialog, QStyle, QStatusBar, QListWidget, QListWidgetItem, QLineEdit)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt, QSettings, QDate
import json
from app import config
import database
import report_generator
from app.ui.dialogs import (DbManagerDialog, VisualInspectionDialog, DeviceDialog, 
                            InstrumentManagerDialog, InstrumentSelectionDialog)
from app.ui.widgets import TestRunnerWidget
from app.backup_manager import restore_from_backup


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Safety Test Manager")
        self.setGeometry(100, 100, 1280, 720)
        self.settings = QSettings("MyCompany", "SafetyTester")
        self.logo_path = self.settings.value("logo_path", "")
        self.theme = self.settings.value("theme", "light")
        self.apply_theme(self.theme)
        
        self.current_mti_info = None
        self.current_technician_name = ""

        self.create_menu_bar()
        self.setStatusBar(QStatusBar(self))

        main_widget = QWidget()
        self.main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.create_left_panel()
        self.create_right_panel()

        self.load_customers()
        self.customer_selector.currentIndexChanged.connect(self.load_devices_for_customer)
        self.load_control_panel_data()

    def apply_theme(self, theme: str):
        if theme == "dark":
            QApplication.instance().setStyleSheet(config.STYLESHEET_DARK)
        else:
            QApplication.instance().setStyleSheet(config.STYLESHEET)
        self.settings.setValue("theme", theme)

    def create_left_panel(self):
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 9, 9, 0)
        left_layout.setSpacing(10)

        dashboard_group = QGroupBox("Dashboard")
        dashboard_layout = QFormLayout(dashboard_group)
        self.customers_stat_label = QLabel("...")
        self.devices_stat_label = QLabel("...")
        dashboard_layout.addRow("Numero Clienti:", self.customers_stat_label)
        dashboard_layout.addRow("Numero Dispositivi:", self.devices_stat_label)
        
        scadenze_group = QGroupBox("Verifiche Scadute o in Scadenza (30 gg)")
        scadenze_layout = QVBoxLayout(scadenze_group)
        self.scadenze_list = QListWidget()
        scadenze_layout.addWidget(self.scadenze_list)
        
        db_button = QPushButton("Gestione Anagrafiche")
        db_button.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        db_button.clicked.connect(self.open_db_manager)

        left_layout.addWidget(dashboard_group)
        left_layout.addWidget(scadenze_group)
        left_layout.addWidget(db_button)
        left_layout.addStretch()
        self.main_layout.addWidget(left_panel, 1)

    def create_right_panel(self):
        """Crea il pannello operativo di destra."""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(9, 9, 0, 0)
        right_layout.setSpacing(10)
        
        session_group = QGroupBox("Sessione di Verifica Corrente")
        session_layout = QFormLayout(session_group)
        self.current_instrument_label = QLabel("<i>Nessuno strumento selezionato</i>")
        self.current_technician_label = QLabel("<i>Nessun tecnico impostato</i>")
        self.setup_session_button = QPushButton("Imposta / Cambia Sessione...")
        self.setup_session_button.clicked.connect(self.setup_verification_session)
        session_layout.addRow("Strumento in Uso:", self.current_instrument_label)
        session_layout.addRow("Tecnico:", self.current_technician_label)
        session_layout.addWidget(self.setup_session_button)

        # --- NUOVO: PANNELLO DI RICERCA RAPIDA ---
        quick_search_group = QGroupBox("Ricerca Rapida Dispositivo")
        quick_search_layout = QHBoxLayout(quick_search_group)
        self.global_device_search_edit = QLineEdit()
        self.global_device_search_edit.setPlaceholderText("Inserisci S/N o Inventario AMS...")
        self.global_device_search_button = QPushButton("Cerca")
        
        quick_search_layout.addWidget(self.global_device_search_edit)
        quick_search_layout.addWidget(self.global_device_search_button)

        # Connetti sia il click del pulsante che il tasto Invio nel campo di testo
        self.global_device_search_button.clicked.connect(self.perform_global_device_search)
        self.global_device_search_edit.returnPressed.connect(self.perform_global_device_search)
        # --- FINE PANNELLO RICERCA RAPIDA ---

        self.selection_group = QGroupBox("Selezione Manuale")
        selection_layout = QFormLayout(self.selection_group)
        self.customer_selector = QComboBox(); self.customer_selector.setEditable(True); self.customer_selector.setInsertPolicy(QComboBox.NoInsert)
        self.customer_selector.completer().setFilterMode(Qt.MatchContains); self.customer_selector.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.device_selector = QComboBox(); self.device_selector.setEditable(True); self.device_selector.setInsertPolicy(QComboBox.NoInsert)
        self.device_selector.completer().setFilterMode(Qt.MatchContains); self.device_selector.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.profile_selector = QComboBox(); self.profile_selector.addItems(config.PROFILES.keys())
        device_layout = QHBoxLayout(); device_layout.setContentsMargins(0,0,0,0)
        device_layout.addWidget(self.device_selector, 1)
        self.add_device_button = QPushButton("+"); self.add_device_button.setFixedSize(35, 35)
        self.add_device_button.setObjectName("add_device_button"); self.add_device_button.clicked.connect(self.quick_add_device)
        device_layout.addWidget(self.add_device_button)
        selection_layout.addRow("Cliente:", self.customer_selector); selection_layout.addRow("Dispositivo:", device_layout); selection_layout.addRow("Profilo:", self.profile_selector)
        self.start_button = QPushButton("Avvia Nuova Verifica"); self.start_button.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay)); self.start_button.clicked.connect(self.start_verification)
        selection_layout.addRow(self.start_button)
        
        self.test_runner_container = QWidget()
        self.test_runner_layout = QVBoxLayout(self.test_runner_container)
        self.test_runner_layout.setContentsMargins(0,0,0,0)
        
        right_layout.addWidget(session_group)
        right_layout.addWidget(quick_search_group) # Aggiungi il nuovo pannello
        right_layout.addWidget(self.selection_group)
        right_layout.addWidget(self.test_runner_container)
        right_layout.addStretch()
        
        self.main_layout.addWidget(right_panel, 2)


    def perform_global_device_search(self):
        """Esegue la ricerca globale e seleziona cliente/dispositivo se trovato."""
        search_term = self.global_device_search_edit.text().strip()
        if not search_term:
            return

        logging.info(f"Ricerca globale per il termine: {search_term}")
        self.statusBar().showMessage(f"Ricerca di '{search_term}' in corso...")
        
        device = database.search_device_globally(search_term)

        if device:
            customer_id = device['customer_id']
            device_id = device['id']

            # Seleziona il cliente corretto nel ComboBox
            for i in range(self.customer_selector.count()):
                if self.customer_selector.itemData(i) == customer_id:
                    self.customer_selector.setCurrentIndex(i)
                    break
            
            # La riga sopra scatena self.load_devices_for_customer.
            # Ora dobbiamo selezionare il dispositivo corretto nella lista appena caricata.
            for i in range(self.device_selector.count()):
                if self.device_selector.itemData(i) == device_id:
                    self.device_selector.setCurrentIndex(i)
                    break
            
            self.statusBar().showMessage(f"Dispositivo '{device['description']}' trovato e selezionato.", 5000)
            logging.info(f"Dispositivo trovato: ID {device_id}, Cliente ID {customer_id}")
            self.global_device_search_edit.clear()
        else:
            self.statusBar().showMessage(f"Nessun dispositivo trovato per '{search_term}'.", 5000)
            logging.warning(f"Ricerca globale fallita per il termine: {search_term}")
            QMessageBox.warning(self, "Ricerca Fallita", f"Nessun dispositivo trovato con matricola o inventario AMS '{search_term}'.")

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        settings_menu = menu_bar.addMenu("Impostazioni")
        
        restore_action = QAction("Ripristina Database da Backup...", self)
        restore_action.triggered.connect(self.restore_database)
        file_menu.addAction(restore_action)
        file_menu.addSeparator()
        quit_action = QAction("Esci", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        logo_action = QAction("Imposta Logo Azienda...", self)
        logo_action.triggered.connect(self.set_company_logo)
        settings_menu.addAction(logo_action)
        mti_manager_action = QAction("Gestisci Strumenti di Misura...", self)
        mti_manager_action.triggered.connect(self.open_instrument_manager)
        settings_menu.addAction(mti_manager_action)

        # Tema chiaro/scuro
        settings_menu.addSeparator()
        light_theme_action = QAction("Tema Chiaro", self)
        light_theme_action.setCheckable(True)
        dark_theme_action = QAction("Tema Scuro", self)
        dark_theme_action.setCheckable(True)

        # Stato iniziale
        if self.theme == "dark":
            dark_theme_action.setChecked(True)
        else:
            light_theme_action.setChecked(True)

        def set_light():
            light_theme_action.setChecked(True)
            dark_theme_action.setChecked(False)
            self.theme = "light"
            self.apply_theme("light")

        def set_dark():
            dark_theme_action.setChecked(True)
            light_theme_action.setChecked(False)
            self.theme = "dark"
            self.apply_theme("dark")

        light_theme_action.triggered.connect(set_light)
        dark_theme_action.triggered.connect(set_dark)
        settings_menu.addAction(light_theme_action)
        settings_menu.addAction(dark_theme_action)
    
    def load_control_panel_data(self):
        self.statusBar().showMessage("Aggiornamento dati dashboard...")
        stats = database.get_stats()
        self.customers_stat_label.setText(f"<b>{stats.get('customers', 0)}</b>")
        self.devices_stat_label.setText(f"<b>{stats.get('devices', 0)}</b>")
        self.scadenze_list.clear()
        devices_to_check = database.get_devices_needing_verification()
        if not devices_to_check:
            self.scadenze_list.addItem("Nessuna verifica in scadenza.")
        else:
            today = QDate.currentDate()
            for device in devices_to_check:
                next_date_str = device['next_verification_date']
                if not next_date_str: continue
                next_date = QDate.fromString(next_date_str, "yyyy-MM-dd")
                item_text = f"<b>{device['description']}</b> (S/N: {device['serial_number']})<br><small><i>{device['customer_name']}</i> - Scadenza: {next_date.toString('dd/MM/yyyy')}</small>"
                list_item = QListWidgetItem()
                label = QLabel(item_text)
                if next_date < today:
                    label.setStyleSheet("color: #D32F2F; font-weight: bold;")
                    list_item.setIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical))
                else:
                    label.setStyleSheet("color: #F57C00;")
                    list_item.setIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.scadenze_list.addItem(list_item)
                self.scadenze_list.setItemWidget(list_item, label)
        self.statusBar().showMessage("Pronto.", 3000)

    def setup_verification_session(self):
        dialog = InstrumentSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.current_mti_info = dialog.getSelectedInstrumentData()
            self.current_technician_name = dialog.getTechnicianName()
            self.current_instrument_label.setText(f"<b>{self.current_mti_info['instrument']} (S/N: {self.current_mti_info['serial']})</b>")
            self.current_technician_label.setText(f"<b>{self.current_technician_name}</b>")
            logging.info(f"Sessione impostata per il tecnico '{self.current_technician_name}' con lo strumento '{self.current_mti_info['instrument']}'")
            self.statusBar().showMessage("Sessione impostata. Pronto per avviare le verifiche.", 5000)

    def start_verification(self):
        """Avvia una verifica, con un controllo preliminare sulle parti applicate."""
        if not self.current_mti_info or not self.current_technician_name:
            QMessageBox.warning(self, "Sessione non Impostata", "Per favore, imposta lo strumento e il nome del tecnico prima di avviare una verifica.")
            return
            
        device_id = self.device_selector.currentData()
        if not device_id or self.customer_selector.currentIndex() <= 0:
            QMessageBox.warning(self, "Attenzione", "Selezionare un cliente e un dispositivo."); return
            
        device_info = database.get_device_by_id(device_id)
        profile_name = self.profile_selector.currentText()
        selected_profile = config.PROFILES[profile_name]

        # --- NUOVO BLOCCO DI CONTROLLO PER LE PARTI APPLICATE ---
        
        # Controlla se il profilo richiede test su parti applicate
        profile_needs_ap = any(test.is_applied_part_test for test in selected_profile.tests)
        
        # Controlla se il dispositivo ha parti applicate registrate
        try:
            applied_parts = json.loads(device_info['applied_parts_json'] or '[]')
        except (json.JSONDecodeError, TypeError):
            applied_parts = []

        # Se il test richiede parti applicate ma il dispositivo non ne ha, chiedi all'utente cosa fare
        if profile_needs_ap and not applied_parts:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Parti Applicate Mancanti")
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setText(
                f"Il profilo '{profile_name}' richiede test su Parti Applicate, ma il dispositivo selezionato non ne ha.\n\n"
                "Cosa vuoi fare?"
            )
            
            # Aggiungi i pulsanti personalizzati
            btn_edit = msg_box.addButton("Modifica Dispositivo", QMessageBox.ActionRole)
            btn_continue = msg_box.addButton("Continua (Salta Test P.A.)", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Annulla Verifica", QMessageBox.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_edit:
                # Apre la finestra di modifica e poi interrompe, l'utente dovrà riavviare la verifica
                dialog = DeviceDialog(device_info, self)
                if dialog.exec():
                    data = dialog.get_data()
                    database.update_device(device_id, **data)
                    self.load_devices_for_customer(device_info['customer_id']) # Ricarica per mostrare le modifiche
                return # Interrompe comunque per permettere all'utente di ricontrollare
                
            elif msg_box.clickedButton() == btn_cancel:
                return # Annulla l'intera operazione
            
        inspection_dialog = VisualInspectionDialog(self)
        if inspection_dialog.exec() == QDialog.Accepted:
            visual_inspection_data = inspection_dialog.get_data()
            
            if self.test_runner_container.layout().count() > 0:
                self.test_runner_container.layout().itemAt(0).widget().deleteLater()

            customer_info = database.get_customer_by_id(device_info['customer_id'])
            report_settings = {"logo_path": self.logo_path}
            
            test_runner_widget = TestRunnerWidget(
                device_info, customer_info, self.current_mti_info, report_settings,
                profile_name, visual_inspection_data, self.current_technician_name, self
            )
            self.test_runner_layout.addWidget(test_runner_widget)
            self.set_selection_enabled(False)

    def reset_main_ui(self):
        if self.test_runner_container.layout().count() > 0:
            for i in reversed(range(self.test_runner_layout.count())):
                self.test_runner_layout.itemAt(i).widget().deleteLater()
        self.set_selection_enabled(True)
        self.load_control_panel_data()

    def set_selection_enabled(self, enabled):
        self.selection_group.setVisible(enabled)
        self.menuBar().setEnabled(enabled)
    
    def open_db_manager(self):
        dialog = DbManagerDialog(self)
        dialog.setWindowState(Qt.WindowMaximized)
        dialog.exec()
        self.load_customers()
        self.load_control_panel_data()

    def load_customers(self):
        self.customer_selector.clear(); self.device_selector.clear()
        customers = database.get_all_customers()
        self.customer_selector.addItem("Seleziona...", -1)
        for cust in customers: self.customer_selector.addItem(cust['name'], cust['id'])

    def load_devices_for_customer(self, customer_id=None):
        """
        Carica i dispositivi per un cliente nel selettore.
        Se customer_id non è fornito, lo recupera dalla selezione corrente.
        """
        if customer_id is None:
            customer_id = self.customer_selector.currentData()

        self.device_selector.clear()

        if customer_id and customer_id != -1:
            devices = database.get_devices_for_customer(customer_id)
            for dev in devices:
                display_text = f"{dev['description']} (S/N: {dev['serial_number']}"
                
                # --- CORREZIONE DEFINITIVA QUI ---
                # Controlla se la colonna 'ams_inventory' esiste nel risultato
                # e se il suo valore non è nullo o vuoto.
                if 'ams_inventory' in dev.keys() and dev['ams_inventory']:
                    display_text += f" / Inv. AMS: {dev['ams_inventory']}"
                # --- FINE CORREZIONE ---

                display_text += ")"
                self.device_selector.addItem(display_text, dev['id'])
    def quick_add_device(self):
        customer_id = self.customer_selector.currentData()
        if not customer_id or customer_id == -1:
            QMessageBox.warning(self, "Attenzione", "Selezionare un cliente prima di aggiungere un dispositivo."); return
        dialog = DeviceDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if data['serial']:
                if database.device_exists(data['serial']):
                    QMessageBox.warning(self, "Errore", "Un dispositivo con questa matricola esiste già."); return
                database.add_device(customer_id, **data)
                self.load_devices_for_customer()
                new_serial = data['serial']
                for i in range(self.device_selector.count()):
                    if f"(S/N: {new_serial})" in self.device_selector.itemText(i):
                        self.device_selector.setCurrentIndex(i); break
            else:
                QMessageBox.warning(self, "Errore", "Il numero di serie non può essere vuoto.")

    def restore_database(self):
        logging.warning("L'utente ha avviato la procedura di ripristino del database.")
        reply = QMessageBox.question(self, 'Conferma Ripristino Database',
                                     "<b>ATTENZIONE:</b> Stai per sovrascrivere il database corrente con un file di backup. L'operazione è irreversibile.\n\nL'applicazione verrà chiusa al termine. Vuoi continuare?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            logging.info("Procedura di ripristino annullata dall'utente."); return
        backup_path, _ = QFileDialog.getOpenFileName(self, "Seleziona un file di backup", "backups", "File di Backup (*.bak)")
        if not backup_path:
            logging.info("Selezione del file di backup annullata."); return
        success = restore_from_backup(backup_path)
        if success:
            QMessageBox.information(self, "Ripristino Completato", "Database ripristinato con successo. L'applicazione verrà chiusa.")
        else:
            QMessageBox.critical(self, "Errore di Ripristino", "Errore durante il ripristino. Controllare i log.")
        QApplication.quit()

    def set_company_logo(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Seleziona Logo", "", "Image Files (*.png *.jpg *.jpeg)")
        if filename:
            self.logo_path = filename; self.settings.setValue("logo_path", filename)
            QMessageBox.information(self, "Impostazioni Salvate", f"Logo impostato su:\n{filename}")

    def open_instrument_manager(self):
        dialog = InstrumentManagerDialog(self)
        dialog.exec()