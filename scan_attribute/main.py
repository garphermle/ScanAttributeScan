"""
Application Entry Point for ScanAttribute Desktop GUI.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from scan_attribute.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ScanAttribute")

    # Clean Fusion / System Style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
