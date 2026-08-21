"""
Main Window combining Queue Panel, PDF Viewer, and Attribute Input Form into a Splitter Layout.
Supports Excel-driven rows (B5+), Range Chunking, PDF Indexing for 22,000+ files, and LAN sharing workflows.
"""

import os
from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog, 
    QMessageBox, QStatusBar, QToolBar, QStyle, QApplication, QLabel, QPushButton, QFrame,
    QSizePolicy, QDialog, QSpinBox, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QFont

from scan_attribute.core.master_data import get_default_excel_path
from scan_attribute.core.data_models import MasterDataManager
from scan_attribute.core.excel_engine import ExcelEngine
from scan_attribute.core.pdf_indexer import PDFIndexer
from scan_attribute.core.file_tracker import FileTracker
from scan_attribute.gui.queue_widget import QueueWidget
from scan_attribute.gui.pdf_viewer import PDFViewerWidget
from scan_attribute.gui.form_widget import AttributeFormWidget


class SplitRangeDialog(QDialog):
    def __init__(self, max_stt: int = 1000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📑 Tách File Excel Theo Khoảng (200 dòng / file)")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.spn_start = QSpinBox()
        self.spn_start.setRange(1, max(max_stt, 100000))
        self.spn_start.setValue(1)

        self.spn_end = QSpinBox()
        self.spn_end.setRange(1, max(max_stt, 100000))
        self.spn_end.setValue(min(200, max(max_stt, 1)))

        form.addRow("STT Bắt đầu:", self.spn_start)
        form.addRow("STT Kết thúc:", self.spn_end)
        layout.addLayout(form)

        # Quick preset buttons (200 rows each)
        quick_layout = QHBoxLayout()
        for s in [1, 201, 401, 601, 801]:
            if s <= max_stt:
                e = min(s + 199, max_stt)
                btn = QPushButton(f"{s}-{e}")
                btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
                btn.clicked.connect(lambda _, st=s, ed=e: self._set_quick_range(st, ed))
                quick_layout.addWidget(btn)
        layout.addLayout(quick_layout)

        info_lbl = QLabel("ℹ️ File tách ra gồm 200 dòng giữ nguyên cấu trúc 186 cột để máy khác trên mạng LAN nhập độc lập.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #555; font-size: 11px; margin-top: 6px;")
        layout.addWidget(info_lbl)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _set_quick_range(self, start: int, end: int):
        self.spn_start.setValue(start)
        self.spn_end.setValue(end)

    def get_range(self):
        return self.spn_start.value(), self.spn_end.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanAttribute — Tool Nhập Liệu Thuộc Tính Đất Đai Siêu Tốc")
        self.resize(1620, 960)

        self.root_dir = ""
        self.template_path = get_default_excel_path()
        self.excel_path = self.template_path
        
        self.master_data = MasterDataManager()
        self.master_data.load_from_excel(self.template_path)

        self.excel_engine = ExcelEngine(self.template_path, self.excel_path)
        self.excel_engine.initialize()

        self.pdf_indexer = PDFIndexer()
        self.file_tracker = FileTracker()

        self.current_item_type = "excel_row"  # "excel_row", "folder", or "file"
        self.current_row = 5
        self.current_stt = 1
        self.current_serial = ""
        self.current_folder = ""
        self.current_full_path = ""
        self.current_file = ""
        self.current_file_path = ""

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
                font-size: 11px;
                padding: 3px 8px;
                font-weight: bold;
                border-radius: 3px;
            }
        """)
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(6, 2, 6, 2)
        banner_layout.setSpacing(6)

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

        self.btn_select_excel = QPushButton("📂 Chọn Excel")
        self.btn_select_excel.setStyleSheet("background-color: #1565c0; color: white;")
        self.btn_select_excel.clicked.connect(self.select_excel_file)

        self.btn_new_excel = QPushButton("➕ Tạo Excel")
        self.btn_new_excel.setStyleSheet("background-color: #00796b; color: white;")
        self.btn_new_excel.clicked.connect(self.create_new_excel_file)

        self.btn_split_excel = QPushButton("📑 Tách Khoảng LAN")
        self.btn_split_excel.setStyleSheet("background-color: #5c6bc0; color: white;")
        self.btn_split_excel.clicked.connect(self.export_range_dialog)

        self.btn_merge_excel = QPushButton("📥 Gộp File LAN")
        self.btn_merge_excel.setStyleSheet("background-color: #ef6c00; color: white;")
        self.btn_merge_excel.clicked.connect(self.merge_sub_excel_dialog)

        self.btn_select_dir = QPushButton("📁 Thư Mục Scan")
        self.btn_select_dir.setStyleSheet("background-color: #455a64; color: white;")
        self.btn_select_dir.clicked.connect(self.select_root_directory)

        banner_layout.addWidget(self.btn_select_excel)
        banner_layout.addWidget(self.btn_new_excel)
        banner_layout.addWidget(self.btn_split_excel)
        banner_layout.addWidget(self.btn_merge_excel)
        banner_layout.addWidget(self.btn_select_dir)

        root_layout.addWidget(banner_card)

        # MAIN 3-COLUMN SPLITTER
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setHandleWidth(6)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            QSplitter::handle:hover {
                background-color: #1976d2;
            }
        """)

        # 1. Left Queue (QTreeWidget)
        self.queue_widget = QueueWidget()
        self.queue_widget.setMinimumWidth(260)
        self.queue_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.queue_widget.excel_row_selected.connect(self.on_excel_row_selected)
        self.queue_widget.folder_selected.connect(self.on_folder_selected)
        self.queue_widget.file_selected.connect(self.on_file_selected)
        main_splitter.addWidget(self.queue_widget)

        # 2. Center PDF Viewer
        self.pdf_viewer = PDFViewerWidget()
        self.pdf_viewer.setMinimumWidth(380)
        self.pdf_viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.pdf_viewer.ocr_text_captured.connect(self.on_ocr_text_captured)
        self.pdf_viewer.pdf_tab_changed.connect(self.on_pdf_tab_changed)
        main_splitter.addWidget(self.pdf_viewer)

        # 3. Right Form
        self.form_widget = AttributeFormWidget(self.master_data)
        self.form_widget.setMinimumWidth(360)
        self.form_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.form_widget.save_requested.connect(self.save_and_next)
        main_splitter.addWidget(self.form_widget)

        # Stretch: Left fixed/low stretch, Center 2, Right 2
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 2)
        main_splitter.setSizes([280, 700, 640])

        root_layout.addWidget(main_splitter, stretch=1)
        self.setCentralWidget(central_container)

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self._update_banner_and_status()

    def _update_banner_and_status(self, msg: str = ""):
        total_rows = self.excel_engine.get_data_rows_count()
        completed_rows = self.excel_engine.get_completed_rows_count()
        file_name = os.path.basename(self.excel_path)
        pdf_count = self.pdf_indexer.total_indexed_count

        display_text = f"📊 EXCEL: [{file_name}] | Tổng: {total_rows} dòng | Đã sửa: {completed_rows}/{total_rows} | 📁 Đã index: {pdf_count} PDF"
        self.lbl_excel_path.setText(display_text)

        status_text = f"File Excel: {file_name} | Đã sửa {completed_rows}/{total_rows} dòng | PDF quét được: {pdf_count}"
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
        # Auto-load nhapthua1.xlsx if present in current directory
        local_nhapthua = os.path.join(os.getcwd(), "nhapthua1.xlsx")
        if os.path.exists(local_nhapthua):
            self.excel_path = local_nhapthua
            self.excel_engine.switch_target_file(local_nhapthua, copy_template_if_new=False)
            self.master_data.load_from_excel(local_nhapthua)

        default_source = "/home/garpherm/VNPT/Source"
        if os.path.exists(default_source):
            self.root_dir = default_source
            self.refresh_queue()

    def select_root_directory(self):
        initial_dir = self.root_dir or self._get_default_working_dir()
        dir_path = QFileDialog.getExistingDirectory(
            self, "📁 Chọn thư mục scan / kho dùng chung LAN chứa file PDF", initial_dir
        )
        if dir_path:
            self.root_dir = dir_path
            self.refresh_queue()

    def select_excel_file(self):
        initial_dir = os.path.dirname(self.excel_path) if self.excel_path else self._get_default_working_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "📂 Chọn file Excel (nhapthua1.xlsx hoặc file mẫu 186 cột)", 
            initial_dir, 
            "File Excel (*.xlsx *.xls);;Tất cả các file (*.*)"
        )
        if file_path:
            self.excel_path = file_path
            self.excel_engine.switch_target_file(file_path, copy_template_if_new=False)
            self.master_data.load_from_excel(file_path)
            self.refresh_queue()
            
            total_rows = self.excel_engine.get_data_rows_count()
            QMessageBox.information(
                self, "Đã Chọn File Excel", 
                f"Đã mở file Excel đích:\n{file_path}\n\n📊 File này có {total_rows} dòng dữ liệu / số serial."
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
                f"Đã tạo thành công file Excel mới:\n{file_path}\n\nMọi hồ sơ nhập tiếp theo sẽ ghi nối tiếp từ dòng 5 (STT 1) trở đi."
            )
            self._update_banner_and_status(f"Đã tạo file Excel mới: {os.path.basename(file_path)}")

    def export_range_dialog(self):
        """Allows exporting a slice of STTs to a sub-excel file for LAN multi-computer work."""
        total_rows = self.excel_engine.get_data_rows_count()
        if total_rows == 0:
            QMessageBox.warning(self, "Không có dữ liệu", "File Excel hiện tại chưa có dữ liệu để tách!")
            return

        dlg = SplitRangeDialog(max_stt=total_rows, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            start_stt, end_stt = dlg.get_range()
            initial_name = f"nhapthua_STT_{start_stt:04d}_{end_stt:04d}.xlsx"
            initial_dir = os.path.dirname(self.excel_path) or self._get_default_working_dir()
            out_file, _ = QFileDialog.getSaveFileName(
                self, f"Lưu file Excel khoảng STT {start_stt} - {end_stt}",
                os.path.join(initial_dir, initial_name),
                "File Excel (*.xlsx)"
            )
            if out_file:
                try:
                    exported = self.excel_engine.export_sub_excel(start_stt, end_stt, out_file)
                    QMessageBox.information(
                        self, "Tách File Thành Công",
                        f"Đã tách {exported} dòng (STT {start_stt} -> {end_stt}) sang file:\n{out_file}\n\nBạn có thể gửi file này cho máy con trên mạng LAN để nhập độc lập!"
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi khi tách file", f"Không thể tách file: {e}")

    def merge_sub_excel_dialog(self):
        """Allows merging completed sub-excel files from other LAN machines into master Excel."""
        initial_dir = os.path.dirname(self.excel_path) or self._get_default_working_dir()
        sub_files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn một hoặc nhiều file Excel con đã nhập từ máy khác",
            initial_dir,
            "File Excel (*.xlsx *.xls)"
        )
        if sub_files:
            total_merged = 0
            for sf in sub_files:
                try:
                    merged, skipped = self.excel_engine.merge_sub_excel(sf)
                    total_merged += merged
                except Exception as e:
                    QMessageBox.warning(self, "Cảnh báo khi gộp", f"Lỗi khi đọc file {os.path.basename(sf)}: {e}")

            self.refresh_queue()
            QMessageBox.information(
                self, "Gộp File Hoàn Tất",
                f"Đã gộp thành công {total_merged} dòng dữ liệu vào file Excel chính!"
            )

    def refresh_queue(self):
        if self.root_dir and os.path.exists(self.root_dir):
            self.pdf_indexer.index_directory(self.root_dir)
            self.queue_widget.set_pdf_indexer(self.pdf_indexer)

        excel_rows = self.excel_engine.get_serial_rows()
        self.queue_widget.set_excel_rows(excel_rows)

        if self.root_dir:
            self.file_tracker.load(self.root_dir, self.excel_path)
            processed_map = self.excel_engine.get_processed_serials_info()
            file_map = self.file_tracker.get_all_file_mappings()
            self.queue_widget.load_folders(self.root_dir, processed_map, file_map)

        self._update_banner_and_status()

    def on_excel_row_selected(self, row_num: int, stt_num: int, serial: str, pdf_paths: List[str]):
        """Triggered when user selects a row in the Excel queue (B5+)."""
        self.current_item_type = "excel_row"
        self.current_row = row_num
        self.current_stt = stt_num
        self.current_serial = serial

        # 1. Load PDF(s) into viewer
        if pdf_paths:
            self.current_file_path = pdf_paths[0]
            self.pdf_viewer.load_pdf_list(pdf_paths)
        else:
            self.current_file_path = ""
            self.pdf_viewer.load_pdf_list([])

        # 2. Load row data from Excel
        row_data = self.excel_engine.read_row_data(row_num)
        self.form_widget.load_attr_dict(row_data, serial)

        # 3. Update status
        pdf_info = f"({len(pdf_paths)} file PDF)" if pdf_paths else "(⚠️ Chưa thấy PDF)"
        self._update_banner_and_status(f"📊 STT {stt_num} | Serial [{serial}] ➔ Dòng {row_num} Excel {pdf_info}")

    def on_folder_selected(self, folder_name: str, full_folder_path: str = ""):
        self.current_item_type = "folder"
        self.current_folder = folder_name
        self.current_full_path = full_folder_path or os.path.join(self.root_dir, folder_name)
        self.current_file = ""
        self.current_file_path = ""

        self.pdf_viewer.load_folder_pdfs(self.current_full_path)
        self._load_record_to_form(folder_name)

    def on_file_selected(self, folder_name: str, full_folder_path: str, pdf_filename: str):
        is_new_folder = (self.current_full_path != full_folder_path)
        self.current_item_type = "file"
        self.current_folder = folder_name
        self.current_full_path = full_folder_path
        self.current_file = pdf_filename
        self.current_file_path = os.path.join(full_folder_path, pdf_filename)

        if is_new_folder:
            self.pdf_viewer.load_folder_pdfs(full_folder_path, select_filename=pdf_filename)
        else:
            self.pdf_viewer.select_pdf_tab_by_name(pdf_filename)

        self._load_file_record_to_form(self.current_file_path, folder_name, pdf_filename)
        self.form_widget.navigate_to_pdf_type(pdf_filename)

    def on_pdf_tab_changed(self, filename: str):
        self.queue_widget.highlight_pdf_file(filename)
        self.form_widget.navigate_to_pdf_type(filename)

    def _load_file_record_to_form(self, file_path: str, folder_name: str, pdf_filename: str):
        info = self.file_tracker.get_file_info(file_path)
        base_clean = os.path.splitext(pdf_filename)[0]

        if info:
            row_idx = info["row"]
            row_data = self.excel_engine.read_row_data(row_idx)
            serial_val = str(info.get("serial") or row_data.get(2) or base_clean)
            self.form_widget.load_attr_dict(row_data, serial_val)
            self._update_banner_and_status(f"📄 File: [{pdf_filename}] ➔ Đã lưu tại Dòng {row_idx} (STT {info['stt']})")
        else:
            row_idx = self.excel_engine.find_row_by_serial(pdf_filename) or self.excel_engine.find_row_by_serial(base_clean)
            if row_idx:
                row_data = self.excel_engine.read_row_data(row_idx)
                serial_val = str(row_data.get(2) or base_clean)
                self.form_widget.load_attr_dict(row_data, serial_val)
                self.file_tracker.record_file_saved(file_path, row_idx, row_idx - 4, serial_val)
                self._update_banner_and_status(f"📄 File: [{pdf_filename}] ➔ Khớp Dòng {row_idx} trong Excel")
            else:
                empty_data = {2: base_clean}
                self.form_widget.load_attr_dict(empty_data, base_clean)
                next_row = self.excel_engine.find_first_empty_row()
                self._update_banner_and_status(f"📄 File mới: [{pdf_filename}] ➔ Chưa lưu (Sẽ ghi vào Dòng {next_row})")

    def _load_record_to_form(self, folder_name: str):
        info = self.file_tracker.get_folder_info(self.current_full_path)
        row_idx = info.get("row") if info else None
        if not row_idx:
            row_idx = self.excel_engine.find_row_by_serial(folder_name)

        if row_idx:
            row_data = self.excel_engine.read_row_data(row_idx)
            self.form_widget.load_attr_dict(row_data, folder_name)
            stt = row_idx - 4
            self._update_banner_and_status(f"📁 Hồ sơ: [{folder_name}] (Đã có tại Dòng {row_idx} - STT {stt})")
        else:
            empty_data = {2: folder_name}
            self.form_widget.load_attr_dict(empty_data, folder_name)
            next_row = self.excel_engine.find_first_empty_row()
            next_stt = next_row - 4
            self._update_banner_and_status(f"📁 Hồ sơ mới: [{folder_name}] (Sẽ ghi vào Dòng {next_row} - STT {next_stt})")

    def on_ocr_text_captured(self, text: str):
        self.form_widget.set_ocr_text_to_active_field(text)

    def save_and_next(self):
        try:
            attr_dict = self.form_widget.get_attr_dict()

            if self.current_item_type == "excel_row":
                # 1. EXCEL-ROW LEVEL SAVE (Primary Mode for nhapthua1.xlsx)
                target_row = self.current_row
                serial_val = self.current_serial or attr_dict.get(2) or ""
                attr_dict[1] = self.current_stt
                attr_dict[2] = serial_val

                row_idx = self.excel_engine.save_row_data(serial=serial_val, attr_dict=attr_dict, target_row=target_row)
                owner_name = str(attr_dict.get(9) or "")

                self.queue_widget.mark_excel_row_completed(row_idx, owner_name)
                self._update_banner_and_status(f"✅ Đã lưu Dòng {row_idx} (STT {self.current_stt}: {serial_val})")

                # Advance to next row
                self.queue_widget.select_next_item()

            elif self.current_item_type == "file" and self.current_file_path:
                # 2. FILE-LEVEL SAVE
                info = self.file_tracker.get_file_info(self.current_file_path)
                target_row = info.get("row") if info else None
                serial_val = attr_dict.get(2) or os.path.splitext(self.current_file)[0]

                row_idx = self.excel_engine.save_row_data(serial=serial_val, attr_dict=attr_dict, target_row=target_row)
                stt_val = row_idx - 4

                self.file_tracker.record_file_saved(self.current_file_path, row_idx, stt_val, serial_val)
                self.queue_widget.update_file_status(self.current_file_path, row_idx, stt_val)
                self._update_banner_and_status(f"✅ Đã lưu file [{self.current_file}] vào Dòng {row_idx} (STT {stt_val})")

                self.queue_widget.select_next_item()

            else:
                # 3. FOLDER-LEVEL SAVE
                info = self.file_tracker.get_folder_info(self.current_full_path)
                target_row = info.get("row") if info else None
                serial_val = attr_dict.get(2) or self.current_folder

                row_idx = self.excel_engine.save_row_data(serial=serial_val, attr_dict=attr_dict, target_row=target_row)
                stt_val = row_idx - 4

                self.file_tracker.record_folder_saved(self.current_full_path, row_idx, stt_val, serial_val)
                self.queue_widget.update_processed_status(self.current_folder, row_idx, stt_val)
                self._update_banner_and_status(f"✅ Đã lưu hồ sơ [{self.current_folder}] vào Dòng {row_idx} (STT {stt_val})")

                self.queue_widget.select_next_item()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi khi lưu Excel", f"Không thể lưu dữ liệu: {e}")
