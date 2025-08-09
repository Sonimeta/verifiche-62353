# app/config.py
import json
from PySide6.QtWidgets import QMessageBox
from .data_models import Limit, Test, VerificationProfile
import logging

PROFILES = {}

STYLESHEET = """
    QWidget {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10.5pt;
        color: #222;
    }
    QMainWindow, QDialog {
        background-color: #f6f7fb;
    }
    QStatusBar {
        background: #ffffff;
        border-top: 1px solid #e2e2e2;
    }
    QGroupBox {
        font-weight: 600;
        border: 1px solid #d7d7d7;
        border-radius: 8px;
        margin-top: 14px;
        background: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        color: #333;
    }
    QLabel { color: #333; }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #ffffff;
        border: 1px solid #cfd8dc;
        border-radius: 6px;
        padding: 6px 8px;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 1px solid #0d6efd;
        box-shadow: 0 0 0 2px rgba(13,110,253,0.15);
    }

    QListWidget {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
    }
    QListWidget::item { padding: 8px 10px; }
    QListWidget::item:selected { background: #e7f1ff; color: #0b5ed7; }

    QTableWidget {
        border: 1px solid #d7d7d7;
        gridline-color: #e5e5e5;
        alternate-background-color: #fafafa;
        background: #ffffff;
    }
    QTableWidget::item:selected {
        background: #e7f1ff;
        color: #0b5ed7;
    }
    QHeaderView::section {
        background-color: #f1f3f5;
        padding: 6px 8px;
        border: 1px solid #d7d7d7;
        font-weight: 600;
    }

    QPushButton {
        background-color: #0d6efd;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 9px 16px;
        font-weight: 600;
    }
    QPushButton:hover { background-color: #0b5ed7; }
    QPushButton:pressed { background-color: #0a53be; }
    QPushButton:disabled { background-color: #aab4be; color: #f1f1f1; }

    /* Pulsante + per aggiungere dispositivo */
    #add_device_button {
        font-size: 14pt;
        font-weight: bold;
        padding: 5px 10px;
        min-width: 35px;
        max-width: 35px;
    }
"""

STYLESHEET_DARK = """
    QWidget {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10.5pt;
        color: #eaeef2;
    }
    QMainWindow, QDialog { background-color: #1f2430; }
    QStatusBar {
        background: #1a1e27;
        border-top: 1px solid #2a2f3a;
    }
    QGroupBox {
        font-weight: 600;
        border: 1px solid #2a2f3a;
        border-radius: 8px;
        margin-top: 14px;
        background: #232a36;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        color: #cfd6e0;
    }
    QLabel { color: #dce3ea; }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #1a1f2a;
        border: 1px solid #2e3643;
        border-radius: 6px;
        padding: 6px 8px;
        color: #eaeef2;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 1px solid #4da3ff;
        box-shadow: 0 0 0 2px rgba(77,163,255,0.15);
    }

    QListWidget {
        background: #1a1f2a;
        border: 1px solid #2a2f3a;
        border-radius: 6px;
    }
    QListWidget::item { padding: 8px 10px; }
    QListWidget::item:selected { background: #2b3b55; color: #9ec6ff; }

    QTableWidget {
        border: 1px solid #2a2f3a;
        gridline-color: #2f3542;
        alternate-background-color: #202736;
        background: #1a1f2a;
    }
    QTableWidget::item:selected {
        background: #2b3b55;
        color: #9ec6ff;
    }
    QHeaderView::section {
        background-color: #202736;
        padding: 6px 8px;
        border: 1px solid #2a2f3a;
        font-weight: 600;
        color: #dce3ea;
    }

    QPushButton {
        background-color: #2f6feb;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 9px 16px;
        font-weight: 600;
    }
    QPushButton:hover { background-color: #2862d6; }
    QPushButton:pressed { background-color: #2156c1; }
    QPushButton:disabled { background-color: #40495a; color: #9aa3b0; }

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
