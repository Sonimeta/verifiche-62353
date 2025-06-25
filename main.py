# main.py (Nuova versione, solo punto d'avvio)
import logging
import sys
from PySide6.QtWidgets import QApplication

# Importa i componenti necessari dai nuovi moduli
from app.config import STYLESHEET, load_verification_profiles
from app.ui.main_window import MainWindow
from app.logging_config import setup_logging
from app.backup_manager import create_backup

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Configura il logging
    setup_logging()
    
    logging.info("=====================================")
    logging.info("||   Avvio Safety Test Manager     ||")
    logging.info("=====================================")

    create_backup()  # Crea un backup del database all'avvio
    

    try:
        # Tenta di caricare i profili
        load_verification_profiles()
        logging.info("Profili di verifica caricati con successo.")
        
        # Se tutto va bene, procedi con l'avvio dell'applicazione
        app.setStyleSheet(STYLESHEET)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    except Exception as e:
        # Se load_verification_profiles lancia un errore, catturalo qui
        logging.critical("Errore critico durante l'avvio: Impossibile caricare i profili.", exc_info=True)
        # E mostra la QMessageBox dal thread principale
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Errore Critico di Avvio", f"Impossibile caricare i profili di verifica.\n\n{e}\n\nL'applicazione verrà chiusa.")
        sys.exit(1)

    