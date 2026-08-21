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

    # Clean Fusion Style with robust, high-contrast combobox theme
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QComboBox {
            color: #1a237e;
            background-color: #ffffff;
            selection-background-color: #1976d2;
            selection-color: #ffffff;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #212121;
            selection-background-color: #1976d2;
            selection-color: #ffffff;
            border: 1px solid #90caf9;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            min-height: 24px;
            padding: 4px 8px;
            color: #212121;
            background-color: #ffffff;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #e3f2fd;
            color: #0d47a1;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #1976d2;
            color: #ffffff;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
