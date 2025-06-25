# app/config.py
import json
from PySide6.QtWidgets import QMessageBox
from .data_models import Limit, Test, VerificationProfile
import logging

PROFILES = {}

STYLESHEET = """
    QWidget {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QDialog {
        background-color: #f0f0f0;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #c0c0c0;
        border-radius: 6px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }
    QLabel {
        color: #333;
    }
    QLineEdit, QTextEdit, QComboBox {
        background-color: white;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 5px;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 1px solid #0078d4;
    }
    QTableWidget {
        border: 1px solid #c0c0c0;
        gridline-color: #d0d0d0;
        alternate-background-color: #f7f7f7;
    }
    QHeaderView::section {
        background-color: #e8e8e8;
        padding: 4px;
        border: 1px solid #c0c0c0;
        font-weight: bold;
    }
    QPushButton {
        background-color: #0078d4;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #005a9e;
    }
    QPushButton:pressed {
        background-color: #004578;
    }
    QPushButton:disabled {
        background-color: #a0a0a0;
    }
    #add_device_button {
        font-size: 14pt;
        font-weight: bold;
        padding: 5px 10px;
        min-width: 35px;
        max-width: 35px;
    }
"""

def load_verification_profiles(file_path="profiles.json"):
    global PROFILES
    PROFILES = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            profiles_data = json.load(f)
        for p_data in profiles_data:
            tests = []
            for t_data in p_data.get("tests", []):
                limits = {}
                for key, l_data in t_data.get("limits", {}).items():
                    limits[key] = Limit(**l_data)
                t_data["limits"] = limits
                tests.append(Test(**t_data))
            PROFILES[p_data["profile_key"]] = VerificationProfile(
                name=p_data["profile_name"],
                tests=tests
            )
        if not PROFILES:
            # Lancia un errore se il file JSON è valido ma non contiene profili
            raise ValueError("Il file profiles.json è vuoto o non contiene profili validi.")

        logging.info(f"Profili caricati con successo dal file: {list(PROFILES.keys())}")
        return True

    except FileNotFoundError:
        # Lancia l'errore specifico, sarà gestito dal main.py
        raise FileNotFoundError(f"File dei profili non trovato: {file_path}")
    except json.JSONDecodeError as e:
            # Lancia un errore più descrittivo
        raise ValueError(f"Errore di formato nel file JSON dei profili: {file_path}\nDettagli: {e}")
    except Exception as e:
        # Rilancia qualsiasi altra eccezione
        raise e
