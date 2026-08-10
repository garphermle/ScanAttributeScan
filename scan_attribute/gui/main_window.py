"""
Main Window combining Queue Panel, PDF Viewer, and Attribute Input Form into a Splitter Layout.
Supports multi-level nested folder trees, Excel row/STT tracking, and continuous row appending.
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog, 
    QMessageBox, QStatusBar, QToolBar, QStyle, QApplication, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QFont

from scan_attribute.core.master_data import get_default_excel_path
from scan_attribute.core.data_models import MasterDataManager
from scan_attribute.core.excel_engine import ExcelEngine
from scan_attribute.gui.queue_widget import QueueWidget
from scan_attribute.gui.pdf_viewer import PDFViewerWidget
from scan_attribute.gui.form_widget import AttributeFormWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanAttribute — Tool Nhập Liệu Thuộc Tính Đất Đai Siêu Tốc")
        self.resize(1600, 950)

        self.root_dir = ""
        self.template_path = get_default_excel_path()
        self.excel_path = self.template_path
        
        self.master_data = MasterDataManager()
        self.master_data.load_from_excel(self.template_path)

        self.excel_engine = ExcelEngine(self.template_path, self.excel_path)
        self.excel_engine.initialize()

        self.current_folder = ""
        self.current_full_path = ""

        self._init_ui()
        self._setup_shortcuts()
        self._load_initial_state()

    def _init_ui(self):
        central_container = QWidget()
        root_layout = QVBoxLayout(central_container)
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.setSpacing(2)

        # SLEEK 1-ROW TOP EXCEL BANNER
        banner_card = QFrame()
        banner_card.setStyleSheet("""
            QFrame {
                background-color: #f1f3f4;
                border-bottom: 1px solid #dcdcdc;
                padding: 1px;
            }
            QPushButton {
                font-size: 12px;
                padding: 3px 10px;
                font-weight: bold;
                border-radius: 3px;
            }
        """)
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(6, 2, 6, 2)
        banner_layout.setSpacing(8)

        self.lbl_excel_path = QLabel()
        self.lbl_excel_path.setStyleSheet("""
            background-color: #e8f5e9;
            color: #1b5e20;
            font-weight: bold;
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 3px;
            border: 1px solid #a5d6a7;
        """)
        banner_layout.addWidget(self.lbl_excel_path, stretch=1)

        self.btn_select_excel = QPushButton("📂 Chọn Excel Có Sẵn")
        self.btn_select_excel.setStyleSheet("background-color: #1565c0; color: white;")
        self.btn_select_excel.clicked.connect(self.select_excel_file)

        self.btn_new_excel = QPushButton("➕ Tạo Excel Mới")
        self.btn_new_excel.setStyleSheet("background-color: #00796b; color: white;")
        self.btn_new_excel.clicked.connect(self.create_new_excel_file)

        self.btn_select_dir = QPushButton("📁 Đổi Thư Mục Scan")
        self.btn_select_dir.setStyleSheet("background-color: #616161; color: white;")
        self.btn_select_dir.clicked.connect(self.select_root_directory)

        banner_layout.addWidget(self.btn_select_excel)
        banner_layout.addWidget(self.btn_new_excel)
        banner_layout.addWidget(self.btn_select_dir)

        root_layout.addWidget(banner_card)

        # MAIN 3-COLUMN SPLITTER
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Left Queue (QTreeWidget)
        self.queue_widget = QueueWidget()
        self.queue_widget.folder_selected.connect(self.on_folder_selected)
        main_splitter.addWidget(self.queue_widget)

        # 2. Center PDF Viewer
        self.pdf_viewer = PDFViewerWidget()
        self.pdf_viewer.ocr_text_captured.connect(self.on_ocr_text_captured)
        main_splitter.addWidget(self.pdf_viewer)

        # 3. Right Form
        self.form_widget = AttributeFormWidget(self.master_data)
        self.form_widget.save_requested.connect(self.save_and_next)
        main_splitter.addWidget(self.form_widget)

        # Proportions: 20% Queue, 40% PDF Viewer, 40% Form
        main_splitter.setSizes([300, 660, 640])

        root_layout.addWidget(main_splitter, stretch=1)
        self.setCentralWidget(central_container)

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self._update_banner_and_status()

    def _update_banner_and_status(self, msg: str = ""):
        total_rows = self.excel_engine.get_data_rows_count()
        next_row = self.excel_engine.find_first_empty_row()
        file_name = os.path.basename(self.excel_path)

        display_text = f"📊 EXCEL: [{file_name}] | Hiện có {total_rows} dòng | Dòng kế tiếp sẽ ghi: Dòng {next_row} (STT {next_row - 4})"
        self.lbl_excel_path.setText(display_text)

        status_text = f"File Excel đích: {file_name} | Đã ghi {total_rows} dòng dữ liệu"
        if msg:
            status_text = f"{msg} | {status_text}"
        self.statusBar.showMessage(status_text)

    def _setup_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        save_shortcut.activated.connect(self.save_and_next)

        open_dir_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_dir_shortcut.activated.connect(self.select_root_directory)

        f5_shortcut = QShortcut(QKeySequence("F5"), self)
        f5_shortcut.activated.connect(self.refresh_queue)

    def _get_default_working_dir(self) -> str:
        default_source = "/home/garpherm/VNPT/Source"
        if os.path.exists(default_source):
            return default_source
        return os.path.expanduser("~")

    def _load_initial_state(self):
        default_source = "/home/garpherm/VNPT/Source"
        if os.path.exists(default_source):
            self.root_dir = default_source
            self.refresh_queue()

    def select_root_directory(self):
        initial_dir = self.root_dir or self._get_default_working_dir()
        dir_path = QFileDialog.getExistingDirectory(
            self, "📁 Chọn thư mục gốc chứa các hồ sơ", initial_dir
        )
        if dir_path:
            self.root_dir = dir_path
            self.refresh_queue()

    def select_excel_file(self):
        initial_dir = os.path.dirname(self.excel_path) if self.excel_path else self._get_default_working_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "📂 Chọn file Excel đang làm dở để tiếp tục ghi nối dòng", 
            initial_dir, 
            "File Excel mẫu (*.xlsx *.xls);;Tất cả các file (*.*)"
        )
        if file_path:
            self.excel_path = file_path
            self.excel_engine.switch_target_file(file_path, copy_template_if_new=False)
            self.master_data.load_from_excel(file_path)
            self.refresh_queue()
            
            total_rows = self.excel_engine.get_data_rows_count()
            QMessageBox.information(
                self, "Đã Chọn File Excel", 
                f"Đã chuyển sang file Excel đích:\n{file_path}\n\n📊 File này hiện chứa {total_rows} dòng dữ liệu.\nCác lần nhập tiếp theo sẽ ghi nối tiếp từ dòng {self.excel_engine.find_first_empty_row()}."
            )
            self._update_banner_and_status(f"Đã mở file Excel: {os.path.basename(file_path)}")

    def create_new_excel_file(self):
        initial_dir = os.path.dirname(self.excel_path) if self.excel_path else self._get_default_working_dir()
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "➕ Tạo file Excel mới từ mẫu chuẩn 186 cột", 
            os.path.join(initial_dir, "DuLieu_ThuocTinh_Moi.xlsx"), 
            "File Excel (*.xlsx)"
        )
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            self.excel_path = file_path
            self.excel_engine.switch_target_file(file_path, copy_template_if_new=True)
            self.refresh_queue()
            QMessageBox.information(
                self, "Tạo File Excel Mới", 
                f"Đã tạo thành công file Excel mới sạch dòng mẫu:\n{file_path}\n\nMọi hồ sơ nhập tiếp theo sẽ được ghi nối tiếp từ dòng 5 (STT 1) trở đi vào file này."
            )
            self._update_banner_and_status(f"Đã tạo file Excel mới: {os.path.basename(file_path)}")

    def refresh_queue(self):
        if not self.root_dir:
            return
        processed_map = self.excel_engine.get_processed_serials_info()
        self.queue_widget.load_folders(self.root_dir, processed_map)
        self._update_banner_and_status()

    def on_folder_selected(self, folder_name: str, full_folder_path: str = ""):
        self.current_folder = folder_name
        self.current_full_path = full_folder_path or os.path.join(self.root_dir, folder_name)

        # 1. Load PDFs in viewer using full path
        self.pdf_viewer.load_folder_pdfs(self.current_full_path)

        # 2. Check if row exists in target Excel
        row_idx = self.excel_engine.find_row_by_serial(folder_name)
        if row_idx:
            row_data = self.excel_engine.read_row_data(row_idx)
            self.form_widget.load_attr_dict(row_data, folder_name)
            stt = row_idx - 4
            self._update_banner_and_status(f"Đã mở {folder_name} (Đã có tại Dòng {row_idx} - STT {stt})")
        else:
            empty_data = {2: folder_name, 183: folder_name}
            self.form_widget.load_attr_dict(empty_data, folder_name)
            next_row = self.excel_engine.find_first_empty_row()
            next_stt = next_row - 4
            self._update_banner_and_status(f"Đã mở {folder_name} (Sẽ ghi vào Dòng {next_row} - STT {next_stt})")

    def on_ocr_text_captured(self, text: str):
        self.form_widget.set_ocr_text_to_active_field(text)

    def save_and_next(self):
        if not self.current_folder:
            QMessageBox.warning(self, "Chưa chọn hồ sơ", "Vui lòng chọn 1 hồ sơ trong danh sách trước khi lưu!")
            return

        try:
            attr_dict = self.form_widget.get_attr_dict()
            row_idx = self.excel_engine.save_row_data(self.current_folder, attr_dict)
            stt_val = row_idx - 4

            # Update Queue status with exact Row and STT
            self.queue_widget.update_processed_status(self.current_folder, row_idx, stt_val)
            self._update_banner_and_status(f"✅ Đã lưu {self.current_folder} vào Dòng {row_idx} (STT {stt_val})")

            # Auto advance to next folder in Tree
            self.queue_widget.select_next_folder()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi khi lưu Excel", f"Không thể lưu dữ liệu: {e}")
