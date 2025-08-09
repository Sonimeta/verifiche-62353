# app/ui/widgets.py
import json
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
    QLineEdit, QTableWidget, QTableWidgetItem, QGroupBox, QMessageBox, QFileDialog)
from PySide6.QtGui import QFont, QColor

# Import locali dai nuovi moduli
from app.data_models import AppliedPart
from app import config
import database
import report_generator
import logging

class TestRunnerWidget(QWidget):
    def __init__(self, device_info, customer_info, mti_info, report_settings, profile_name, visual_inspection_data, technician_name, parent=None):
        super().__init__(parent)
        self.device_info = device_info
        self.customer_info = customer_info
        self.mti_info = mti_info
        self.report_settings = report_settings
        self.profile_name = profile_name
        self.visual_inspection_data = visual_inspection_data
        self.technician_name = technician_name  # Memorizza il nome del tecnico
        self.parent_window = parent
        
        self.current_profile = config.PROFILES[profile_name]
        self.applied_parts = [AppliedPart(**pa) for pa in json.loads(device_info['applied_parts_json'])]
        self.current_test_index = -1
        self.current_pa_index = -1
        self.results = []

        layout = QVBoxLayout(self)
        test_group = QGroupBox(f"Verifica su: {device_info['description']} (S/N: {device_info['serial_number']})")
        test_layout = QVBoxLayout()
        self.test_name_label = QLabel("Inizio verifica...")
        self.test_name_label.setStyleSheet("font-size: 14pt; font-weight: 700;")
        self.limit_label = QLabel("Limite:")
        self.value_input = QLineEdit()
        self.next_button = QPushButton("Avanti")
        
        self.next_button.clicked.connect(self.next_step)
        self.value_input.returnPressed.connect(self.next_step)
        
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Test / P.A.", "Limite", "Valore", "Esito"])
        self.results_table.setAlternatingRowColors(True)
        
        test_layout.addWidget(self.test_name_label); test_layout.addWidget(self.limit_label)
        test_layout.addWidget(self.value_input); test_layout.addWidget(self.next_button)
        test_layout.addWidget(self.results_table)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        self.next_step()

    def next_step(self):
        if self.current_test_index >= 0:
            if not self.record_result(): return
        
        current_test_object = self.current_profile.tests[self.current_test_index] if self.current_test_index >= 0 else None
        
        if current_test_object and current_test_object.is_applied_part_test and self.current_pa_index < len(self.applied_parts) - 1:
            self.current_pa_index += 1
            self.display_test(current_test_object)
            return

        while True:
            self.current_test_index += 1
            if self.current_test_index >= len(self.current_profile.tests):
                self.show_summary(); return
            
            next_test = self.current_profile.tests[self.current_test_index]
            if next_test.is_applied_part_test:
                if self.applied_parts: self.current_pa_index = 0; self.display_test(next_test); return
                else: continue
            else:
                self.current_pa_index = -1; self.display_test(next_test); return

    def record_result(self):
        test = self.current_profile.tests[self.current_test_index]
        value_str = self.value_input.text().replace(',', '.')
        if not value_str: self.value_input.setStyleSheet("border: 1px solid red;"); return False
        try:
            value_float = float(value_str)
        except ValueError:
            self.value_input.setStyleSheet("border: 1px solid red;"); return False
        
        self.value_input.setStyleSheet("")
        result_name, limit_key = f"{test.name} ({test.parameter})", "::ST"
        if test.is_applied_part_test:
            if not self.applied_parts: return True
            pa = self.applied_parts[self.current_pa_index]; limit_key, result_name = f"::{pa.part_type}", f"{test.name} - {pa.name}"
        
        limit_obj = test.limits.get(limit_key); is_passed, limit_text = True, "N/A"
        if limit_obj and limit_obj.high_value is not None:
            is_passed = (value_float <= limit_obj.high_value)
            limit_text = f"≤ {limit_obj.high_value} {limit_obj.unit}"
        elif limit_obj:
            limit_text = f"N/A (misura in {limit_obj.unit})"
            
        self.results.append({"name": result_name, "limit": limit_text, "value": value_str, "passed": is_passed})
        self.update_results_table()
        return True

    def display_test(self, test):
        self.value_input.clear(); self.value_input.show(); self.limit_label.show()
        self.value_input.setStyleSheet(""); self.value_input.setFocus()
        
        limit_key = "::ST"
        if test.is_applied_part_test:
            pa = self.applied_parts[self.current_pa_index]
            self.test_name_label.setText(f"{test.name}\nParte Applicata: {pa.name} (Tipo {pa.part_type})")
            limit_key = f"::{pa.part_type}"
        else:
            self.test_name_label.setText(f"{test.name}\n{test.parameter}")
        
        limit_obj = test.limits.get(limit_key); limit_text = "<b>Limite:</b> Non specificato"
        if limit_obj:
            if limit_obj.high_value is not None: limit_text = f"<b>Limite:</b> ≤ {limit_obj.high_value} {limit_obj.unit}"
            else: limit_text = f"<b>Limite:</b> N/A (misura in {limit_obj.unit})"
        self.limit_label.setText(limit_text)

    def update_results_table(self):
        last_result = self.results[-1]; row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        for i, key in enumerate(["name", "limit", "value"]): self.results_table.setItem(row, i, QTableWidgetItem(last_result[key]))
        passed_item = QTableWidgetItem("PASSATO" if last_result['passed'] else "FALLITO")
        passed_item.setBackground(QColor('#D4EDDA') if last_result['passed'] else QColor('#F8D7DA'))
        self.results_table.setItem(row, 3, passed_item)

    def show_summary(self):
        self.test_name_label.setText("Verifica Completata."); self.value_input.hide()
        self.limit_label.hide(); self.next_button.setText("Salva Report e PDF")
        self.next_button.clicked.disconnect(); self.next_button.clicked.connect(self.save_all)

    def save_all(self):
        overall_status = "PASSATO" if all(r['passed'] for r in self.results) else "FALLITO"
        
        database.save_verification(
            device_id=self.device_info['id'], profile_name=self.profile_name,
            results=self.results, overall_status=overall_status,
            visual_inspection_data=self.visual_inspection_data, mti_info=self.mti_info,
            technician_name=self.technician_name
        )
        
        try:
            device_data = database.get_device_by_id(self.device_info['id'])
            if device_data and device_data['verification_interval'] is not None:
                interval = int(device_data['verification_interval'])
                database.update_device_next_verification_date(self.device_info['id'], interval)
        except Exception as e:
            logging.error(f"Impossibile aggiornare la data di prossima verifica.", exc_info=True)

        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", f"./Report_{self.device_info['serial_number']}_{datetime.now().strftime('%Y%m%d')}.pdf", "PDF Files (*.pdf)")
        if not filename: self.parent_window.reset_main_ui(); return
            
        verification_data = {'date': datetime.now().strftime('%d/%m/%Y'), 'profile_name': self.profile_name, 
                             'overall_status': overall_status, 'results': self.results, 
                             'visual_inspection_data': self.visual_inspection_data}
        
        report_generator.create_report(filename, self.device_info, self.customer_info, self.mti_info, 
                                     self.report_settings, verification_data, self.technician_name)
        
        QMessageBox.information(self, "Successo", f"Verifica salvata e report generato:\n{filename}")
        self.next_button.setDisabled(True)
        self.parent_window.reset_main_ui()