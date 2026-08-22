"""
Queue Widget supporting 3 View Modes:
1. "📊 Theo Excel (B5+)" (Excel-driven rows with Lightweight 200-row Chunking for 22,000+ files and LAN sharing)
2. "📁 Chỉ Thư mục" (Compact Folder View)
3. "📑 Chi tiết File PDF" (Expanded PDF Files View with icon classification)
"""

import os
from typing import List, Set, Dict, Optional, Any, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, 
    QTreeWidgetItem, QLabel, QPushButton, QFrame, QButtonGroup,
    QComboBox, QSpinBox, QProgressBar, QToolTip
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from scan_attribute.core.pdf_indexer import PDFIndexer

ROLE_PATH = int(Qt.ItemDataRole.UserRole)
ROLE_IS_DONE = int(Qt.ItemDataRole.UserRole) + 1
ROLE_ROW_NUM = int(Qt.ItemDataRole.UserRole) + 2
ROLE_STT_NUM = int(Qt.ItemDataRole.UserRole) + 3
ROLE_ITEM_TYPE = int(Qt.ItemDataRole.UserRole) + 4   # "excel_row", "folder", "file"
ROLE_PARENT_FOLDER = int(Qt.ItemDataRole.UserRole) + 5
ROLE_FILE_NAME = int(Qt.ItemDataRole.UserRole) + 6
ROLE_SERIAL = int(Qt.ItemDataRole.UserRole) + 7
ROLE_PDF_PATHS = int(Qt.ItemDataRole.UserRole) + 8


class QueueWidget(QWidget):
    # Signals
    excel_row_selected = Signal(int, int, str, list)  # (row_num, stt_num, serial, matching_pdf_paths)
    folder_selected = Signal(str, str)                 # (serial_name, full_folder_path)
    file_selected = Signal(str, str, str)              # (serial_name, full_folder_path, pdf_filename)
    split_range_requested = Signal(int, int)           # (start_stt, end_stt)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_dir = ""
        self.pdf_indexer = PDFIndexer()
        self.excel_rows: List[Dict[str, Any]] = []
        self.processed_map: Dict[str, Dict[str, Any]] = {}
        self.file_map: Dict[str, Dict[str, Any]] = {}
        
        self.view_mode = "excel"  # "excel", "folder", "files"
        self.chunk_size = 200     # Default 200 rows per chunk for optimal speed
        self.current_chunk_idx = 0
        self.status_filter = "all"  # "all", "todo", "done"

        self.excel_items: List[QTreeWidgetItem] = []
        self.folder_items: List[QTreeWidgetItem] = []
        self.file_items: List[QTreeWidgetItem] = []
        self._block_selection_signals = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header Title
        header_lbl = QLabel("📋 Danh sách Hồ sơ / File Scan")
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        header_lbl.setFont(font)
        layout.addWidget(header_lbl)

        # 3 View Options Segmented Toggle Buttons
        opt_container = QFrame()
        opt_container.setStyleSheet("""
            QFrame {
                background-color: #f0f4f8;
                border: 1px solid #cfd8dc;
                border-radius: 4px;
                padding: 1px;
            }
            QPushButton {
                border: none;
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 11px;
                font-weight: bold;
                color: #455a64;
                background-color: transparent;
            }
            QPushButton:checked {
                background-color: #1976d2;
                color: white;
            }
            QPushButton:hover:!checked {
                background-color: #e2e8f0;
            }
        """)
        opt_layout = QHBoxLayout(opt_container)
        opt_layout.setContentsMargins(2, 2, 2, 2)
        opt_layout.setSpacing(2)

        self.btn_opt_excel = QPushButton("📊 Theo Excel (B5+)")
        self.btn_opt_excel.setCheckable(True)
        self.btn_opt_excel.setChecked(True)

        self.btn_opt_folder = QPushButton("📁 Chỉ Folder")
        self.btn_opt_folder.setCheckable(True)

        self.btn_opt_files = QPushButton("📑 Chi tiết PDF")
        self.btn_opt_files.setCheckable(True)

        self.btn_group_mode = QButtonGroup(self)
        self.btn_group_mode.addButton(self.btn_opt_excel, 0)
        self.btn_group_mode.addButton(self.btn_opt_folder, 1)
        self.btn_group_mode.addButton(self.btn_opt_files, 2)
        self.btn_group_mode.idClicked.connect(self._on_view_mode_changed)

        opt_layout.addWidget(self.btn_opt_excel)
        opt_layout.addWidget(self.btn_opt_folder)
        opt_layout.addWidget(self.btn_opt_files)
        layout.addWidget(opt_container)

        # CHUNKING & RANGE CONTROLS FOR EXCEL MODE
        self.chunk_container = QFrame()
        self.chunk_container.setStyleSheet("""
            QFrame {
                background-color: #e8eaf6;
                border: 1px solid #c5cae9;
                border-radius: 4px;
                padding: 2px;
            }
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #1a237e;
            }
            QComboBox {
                font-size: 11px;
                padding: 3px 6px;
                font-weight: bold;
                border: 1.5px solid #7986cb;
                border-radius: 3px;
                background-color: #ffffff;
                color: #1a237e;
                min-height: 24px;
            }
            QComboBox:hover {
                border: 1.5px solid #1a237e;
                background-color: #e8eaf6;
                color: #0d47a1;
            }
            QComboBox:focus {
                border: 2px solid #303f9f;
                background-color: #ffffff;
                color: #1a237e;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left-width: 1px;
                border-left-color: #c5cae9;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                background-color: #e8eaf6;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1a237e;
                selection-background-color: #3f51b5;
                selection-color: #ffffff;
                border: 1.5px solid #3f51b5;
                padding: 2px;
                font-size: 11px;
                font-weight: bold;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 4px 8px;
                color: #1a237e;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #c5cae9;
                color: #000051;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3f51b5;
                color: #ffffff;
            }
            QPushButton {
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
                background-color: #3f51b5;
                color: white;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #303f9f;
            }
        """)
        chunk_vbox = QVBoxLayout(self.chunk_container)
        chunk_vbox.setContentsMargins(4, 3, 4, 3)
        chunk_vbox.setSpacing(3)

        # Row 1: Chunk Selector Dropdown + Prev/Next Buttons + Chunk size combo
        chunk_row1 = QHBoxLayout()
        chunk_row1.setContentsMargins(0, 0, 0, 0)
        chunk_row1.setSpacing(3)

        self.btn_prev_chunk = QPushButton("◀")
        self.btn_prev_chunk.setFixedWidth(24)
        self.btn_prev_chunk.clicked.connect(self._on_prev_chunk)

        self.cbo_chunks = QComboBox()
        self.cbo_chunks.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.cbo_chunks.currentIndexChanged.connect(self._on_chunk_dropdown_changed)

        self.btn_next_chunk = QPushButton("▶")
        self.btn_next_chunk.setFixedWidth(24)
        self.btn_next_chunk.clicked.connect(self._on_next_chunk)

        self.cbo_chunk_size = QComboBox()
        self.cbo_chunk_size.addItem("200 dòng", 200)
        self.cbo_chunk_size.addItem("100 dòng", 100)
        self.cbo_chunk_size.addItem("50 dòng", 50)
        self.cbo_chunk_size.addItem("500 dòng", 500)
        self.cbo_chunk_size.addItem("Tất cả", 1000000)
        self.cbo_chunk_size.currentIndexChanged.connect(self._on_chunk_size_changed)

        chunk_row1.addWidget(self.btn_prev_chunk)
        chunk_row1.addWidget(self.cbo_chunks, stretch=1)
        chunk_row1.addWidget(self.btn_next_chunk)
        chunk_row1.addWidget(self.cbo_chunk_size)
        chunk_vbox.addLayout(chunk_row1)

        # Row 2: Status Filter Segmented Buttons (Tất cả, Chưa nhập, Đã sửa)
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(2)

        self.btn_filter_all = QPushButton("Tất cả (0)")
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setChecked(True)
        self.btn_filter_all.setStyleSheet("background-color: #1976d2; color: white;")

        self.btn_filter_todo = QPushButton("⏳ Chưa sửa (0)")
        self.btn_filter_todo.setCheckable(True)
        self.btn_filter_todo.setStyleSheet("background-color: #e0e0e0; color: #333;")

        self.btn_filter_done = QPushButton("✅ Đã sửa (0)")
        self.btn_filter_done.setCheckable(True)
        self.btn_filter_done.setStyleSheet("background-color: #e0e0e0; color: #333;")

        self.btn_filter_group = QButtonGroup(self)
        self.btn_filter_group.addButton(self.btn_filter_all, 0)
        self.btn_filter_group.addButton(self.btn_filter_todo, 1)
        self.btn_filter_group.addButton(self.btn_filter_done, 2)
        self.btn_filter_group.idClicked.connect(self._on_status_filter_changed)

        filter_row.addWidget(self.btn_filter_all)
        filter_row.addWidget(self.btn_filter_todo)
        filter_row.addWidget(self.btn_filter_done)
        chunk_vbox.addLayout(filter_row)

        # Progress bar in current chunk
        self.chunk_progress = QProgressBar()
        self.chunk_progress.setFixedHeight(12)
        self.chunk_progress.setTextVisible(False)
        self.chunk_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #c5cae9;
                border-radius: 2px;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
            }
        """)
        chunk_vbox.addWidget(self.chunk_progress)

        layout.addWidget(self.chunk_container)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm theo số Serial, STT, Tên chủ...")
        self.search_input.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_input)

        # Tree Widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Hồ sơ / Serial / File", "Vị trí Excel / Tình trạng"])
        self.tree_widget.setColumnWidth(0, 200)
        self.tree_widget.setAnimated(False)  # Disabled animation for zero-lag
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree_widget)

        # Footer Stats
        self.stats_lbl = QLabel("Tổng số: 0 | Đã sửa: 0 | Còn lại: 0")
        self.stats_lbl.setStyleSheet("color: #37474f; font-size: 11px; font-weight: bold; padding: 2px;")
        layout.addWidget(self.stats_lbl)

    def _on_chunk_size_changed(self, idx: int):
        val = self.cbo_chunk_size.currentData()
        if val:
            self.chunk_size = val
            self.current_chunk_idx = 0
            self._build_chunk_dropdown()
            self._render_excel_tree()

    def _on_view_mode_changed(self, btn_id: int):
        modes = {0: "excel", 1: "folder", 2: "files"}
        new_mode = modes.get(btn_id, "excel")
        if new_mode != self.view_mode:
            self.view_mode = new_mode
            self.chunk_container.setVisible(self.view_mode == "excel")
            self.reload()

    def set_pdf_indexer(self, indexer: PDFIndexer):
        self.pdf_indexer = indexer

    def set_excel_rows(self, rows: List[Dict[str, Any]]):
        """Loads data rows from Excel Engine."""
        self.excel_rows = rows
        self._build_chunk_dropdown()
        if self.view_mode == "excel":
            self._render_excel_tree()

    def _build_chunk_dropdown(self):
        self.cbo_chunks.blockSignals(True)
        self.cbo_chunks.clear()

        total = len(self.excel_rows)
        if total == 0:
            self.cbo_chunks.addItem("Không có dữ liệu Excel", (0, 0))
            self.cbo_chunks.blockSignals(False)
            return

        num_chunks = (total + self.chunk_size - 1) // self.chunk_size
        for i in range(num_chunks):
            start_idx = i * self.chunk_size
            end_idx = min(start_idx + self.chunk_size, total)
            stt_start = self.excel_rows[start_idx]["stt"]
            stt_end = self.excel_rows[end_idx - 1]["stt"]
            chunk_rows = self.excel_rows[start_idx:end_idx]
            done_cnt = sum(1 for r in chunk_rows if r["is_completed"])
            label = f"STT {stt_start} - {stt_end} ({done_cnt}/{len(chunk_rows)} đã sửa)"
            self.cbo_chunks.addItem(label, (start_idx, end_idx))

        if num_chunks > 1:
            self.cbo_chunks.addItem(f"Tất cả ({total} hồ sơ)", (0, total))

        if self.current_chunk_idx < self.cbo_chunks.count():
            self.cbo_chunks.setCurrentIndex(self.current_chunk_idx)
        else:
            self.cbo_chunks.setCurrentIndex(0)
            self.current_chunk_idx = 0

        self.cbo_chunks.blockSignals(False)

    def _on_chunk_dropdown_changed(self, index: int):
        if index >= 0:
            self.current_chunk_idx = index
            self._render_excel_tree()

    def _on_prev_chunk(self):
        cur = self.cbo_chunks.currentIndex()
        if cur > 0:
            self.cbo_chunks.setCurrentIndex(cur - 1)

    def _on_next_chunk(self):
        cur = self.cbo_chunks.currentIndex()
        if cur < self.cbo_chunks.count() - 1:
            self.cbo_chunks.setCurrentIndex(cur + 1)

    def _on_status_filter_changed(self, btn_id: int):
        filters = {0: "all", 1: "todo", 2: "done"}
        self.status_filter = filters.get(btn_id, "all")

        # Update button visual styling
        for idx, btn in enumerate([self.btn_filter_all, self.btn_filter_todo, self.btn_filter_done]):
            if idx == btn_id:
                btn.setStyleSheet("background-color: #1976d2; color: white;")
            else:
                btn.setStyleSheet("background-color: #e0e0e0; color: #333;")

        if self.view_mode == "excel":
            self._render_excel_tree()

    def reload(self):
        if self.view_mode == "excel":
            self.chunk_container.setVisible(True)
            self._render_excel_tree()
        else:
            self.chunk_container.setVisible(False)
            if self.root_dir:
                self.load_folders(self.root_dir, self.processed_map, self.file_map)

    def load_folders(self, root_dir: str, processed_map: Dict[str, Dict[str, Any]], file_map: Optional[Dict[str, Dict[str, Any]]] = None):
        self.root_dir = root_dir
        self.processed_map = {k.lower(): v for k, v in processed_map.items()}
        if file_map is not None:
            self.file_map = {k.lower(): v for k, v in file_map.items()}

        if self.view_mode == "excel":
            self._render_excel_tree()
            return

        self.folder_items.clear()
        self.file_items.clear()
        self.tree_widget.setUpdatesEnabled(False)
        self.tree_widget.clear()

        if not os.path.exists(root_dir):
            self.tree_widget.setUpdatesEnabled(True)
            self._update_stats(0, 0)
            return

        root_item = self.tree_widget.invisibleRootItem()
        self._build_tree_recursive(root_dir, root_item)

        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setExpanded(True)

        self.tree_widget.setUpdatesEnabled(True)
        if self.view_mode == "files":
            processed_count = sum(1 for item in self.file_items if item.data(0, ROLE_IS_DONE))
            self._update_stats(len(self.file_items), processed_count)
        else:
            processed_count = sum(1 for item in self.folder_items if item.data(0, ROLE_IS_DONE))
            self._update_stats(len(self.folder_items), processed_count)

    def _render_excel_tree(self):
        """Renders Excel-driven row queue with Lightweight Chunking & Status filtering in 0ms."""
        self.excel_items.clear()
        self.tree_widget.setUpdatesEnabled(False)
        self.tree_widget.clear()

        if not self.excel_rows:
            self.tree_widget.setUpdatesEnabled(True)
            self._update_stats(0, 0)
            return

        chunk_data = self.cbo_chunks.currentData()
        if not chunk_data:
            start_idx, end_idx = 0, len(self.excel_rows)
        else:
            start_idx, end_idx = chunk_data

        visible_rows = self.excel_rows[start_idx:end_idx]

        # Calculate counts for filters
        total_chunk = len(visible_rows)
        done_chunk = sum(1 for r in visible_rows if r["is_completed"])
        todo_chunk = total_chunk - done_chunk

        self.btn_filter_all.setText(f"Tất cả ({total_chunk})")
        self.btn_filter_todo.setText(f"⏳ Chưa ({todo_chunk})")
        self.btn_filter_done.setText(f"✅ Đã sửa ({done_chunk})")

        # Update progress bar
        if total_chunk > 0:
            self.chunk_progress.setMaximum(total_chunk)
            self.chunk_progress.setValue(done_chunk)
        else:
            self.chunk_progress.setValue(0)

        items_to_add = []
        for item_data in visible_rows:
            is_done = item_data["is_completed"]
            if self.status_filter == "todo" and is_done:
                continue
            if self.status_filter == "done" and not is_done:
                continue

            serial = item_data["serial"]
            stt = item_data["stt"]
            row_idx = item_data["row"]
            owner_name = item_data["owner_name"]

            matching_pdfs = self.pdf_indexer.find_pdfs_for_serial(serial)
            pdf_count = len(matching_pdfs)

            note_a = str(item_data.get("note_a", "") or "").strip()

            if is_done:
                icon = "✅"
                note_tag = f" [{note_a}]" if note_a else ""
                info_text = f"Dòng {row_idx}{note_tag} (Đã nhập: {owner_name or 'OK'})"
                color = QColor("#2e7d32")
            else:
                icon = "⏳"
                note_tag = f" [{note_a}]" if note_a else ""
                if pdf_count > 0:
                    info_text = f"Dòng {row_idx}{note_tag} ({pdf_count} PDF)"
                    color = QColor("#e65100")
                else:
                    info_text = f"Dòng {row_idx}{note_tag} (Chưa thấy PDF)"
                    color = QColor("#757575")

            title_text = f"{icon} STT {stt:04d}: {serial}"
            if note_a:
                title_text += f" [{note_a}]"
            tree_item = QTreeWidgetItem([title_text, info_text])
            tree_item.setData(0, ROLE_ITEM_TYPE, "excel_row")
            tree_item.setData(0, ROLE_ROW_NUM, row_idx)
            tree_item.setData(0, ROLE_STT_NUM, stt)
            tree_item.setData(0, ROLE_SERIAL, serial)
            tree_item.setData(0, ROLE_IS_DONE, is_done)
            tree_item.setData(0, ROLE_PDF_PATHS, matching_pdfs)

            tree_item.setForeground(0, color)
            tree_item.setForeground(1, color)
            font = tree_item.font(0)
            font.setBold(is_done)
            tree_item.setFont(0, font)

            items_to_add.append(tree_item)
            self.excel_items.append(tree_item)

        self.tree_widget.addTopLevelItems(items_to_add)
        self.tree_widget.setUpdatesEnabled(True)

        total_all = len(self.excel_rows)
        done_all = sum(1 for r in self.excel_rows if r["is_completed"])
        self._update_stats(total_all, done_all)

        # Select first item if nothing selected
        if self.excel_items and not self.tree_widget.selectedItems():
            self.tree_widget.setCurrentItem(self.excel_items[0])

    def _build_tree_recursive(self, current_path: str, parent_item: QTreeWidgetItem):
        try:
            entries = sorted(os.scandir(current_path), key=lambda e: e.name.lower())
        except Exception:
            return

        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if entry.name.startswith('.') or entry.name.startswith('_') or entry.name == '__pycache__':
                    continue

                folder_name = entry.name
                folder_path = entry.path

                serial_key = folder_name.lower()
                is_processed = serial_key in self.processed_map
                p_info = self.processed_map.get(serial_key, {})
                excel_row = p_info.get("row")
                stt_val = p_info.get("stt", (excel_row - 4) if excel_row else 0)

                icon = "✅" if is_processed else "📁"
                status_text = f"Dòng {excel_row} (STT {stt_val})" if is_processed else "Chưa lưu"
                item_text = f"{icon} {folder_name}"

                folder_item = QTreeWidgetItem([item_text, status_text])
                folder_item.setData(0, ROLE_PATH, folder_path)
                folder_item.setData(0, ROLE_IS_DONE, is_processed)
                folder_item.setData(0, ROLE_ROW_NUM, excel_row)
                folder_item.setData(0, ROLE_STT_NUM, stt_val)
                folder_item.setData(0, ROLE_ITEM_TYPE, "folder")
                folder_item.setData(0, ROLE_PARENT_FOLDER, folder_name)

                if is_processed:
                    folder_item.setForeground(0, QColor("#2e7d32"))
                    folder_item.setForeground(1, QColor("#2e7d32"))
                    f = folder_item.font(0)
                    f.setBold(True)
                    folder_item.setFont(0, f)

                parent_item.addChild(folder_item)
                self.folder_items.append(folder_item)

                if self.view_mode == "files":
                    self._build_files_in_folder(folder_path, folder_name, folder_item)

            elif entry.is_file(follow_symlinks=False) and entry.name.lower().endswith('.pdf'):
                if self.view_mode == "files" and parent_item == self.tree_widget.invisibleRootItem():
                    self._add_file_item(entry.path, entry.name, "", parent_item)

    def _build_files_in_folder(self, folder_path: str, folder_name: str, parent_item: QTreeWidgetItem):
        try:
            entries = sorted(os.scandir(folder_path), key=lambda e: e.name.lower())
        except Exception:
            return

        for entry in entries:
            if entry.is_file(follow_symlinks=False) and entry.name.lower().endswith('.pdf'):
                self._add_file_item(entry.path, entry.name, folder_name, parent_item)

    def _add_file_item(self, file_path: str, file_name: str, folder_name: str, parent_item: QTreeWidgetItem):
        file_key = file_path.lower()
        info = self.file_map.get(file_key, {})
        is_processed = bool(info)
        excel_row = info.get("row")
        stt_val = info.get("stt", (excel_row - 4) if excel_row else 0)

        fn_lower = file_name.lower()
        if "gcn" in fn_lower:
            type_icon = "📜"
        elif "gtk" in fn_lower:
            type_icon = "📐"
        elif "gt" in fn_lower or "cccd" in fn_lower or "cmnd" in fn_lower:
            type_icon = "📑"
        elif "vo" in fn_lower or "chong" in fn_lower:
            type_icon = "💍"
        else:
            type_icon = "📄"

        status_icon = "✅" if is_processed else "⏳"
        item_text = f"  {status_icon} {type_icon} {file_name}"
        status_text = f"Dòng {excel_row} (STT {stt_val})" if is_processed else "Chưa lưu"

        file_item = QTreeWidgetItem([item_text, status_text])
        file_item.setData(0, ROLE_PATH, file_path)
        file_item.setData(0, ROLE_IS_DONE, is_processed)
        file_item.setData(0, ROLE_ROW_NUM, excel_row)
        file_item.setData(0, ROLE_STT_NUM, stt_val)
        file_item.setData(0, ROLE_ITEM_TYPE, "file")
        file_item.setData(0, ROLE_PARENT_FOLDER, folder_name)
        file_item.setData(0, ROLE_FILE_NAME, file_name)

        if is_processed:
            file_item.setForeground(0, QColor("#2e7d32"))
            file_item.setForeground(1, QColor("#2e7d32"))
        else:
            file_item.setForeground(0, QColor("#e65100"))

        parent_item.addChild(file_item)
        self.file_items.append(file_item)

    def _on_selection_changed(self):
        if self._block_selection_signals:
            return

        selected = self.tree_widget.selectedItems()
        if not selected:
            return

        item = selected[0]
        item_type = item.data(0, ROLE_ITEM_TYPE)

        if item_type == "excel_row":
            row_num = item.data(0, ROLE_ROW_NUM)
            stt_num = item.data(0, ROLE_STT_NUM)
            serial = item.data(0, ROLE_SERIAL)
            pdf_paths = item.data(0, ROLE_PDF_PATHS) or []
            self.excel_row_selected.emit(row_num, stt_num, serial, pdf_paths)

        elif item_type == "folder":
            folder_name = item.data(0, ROLE_PARENT_FOLDER)
            folder_path = item.data(0, ROLE_PATH)
            self.folder_selected.emit(folder_name, folder_path)

        elif item_type == "file":
            folder_name = item.data(0, ROLE_PARENT_FOLDER)
            file_name = item.data(0, ROLE_FILE_NAME)
            file_path = item.data(0, ROLE_PATH)
            full_folder_path = os.path.dirname(file_path)
            self.file_selected.emit(folder_name, full_folder_path, file_name)

    def mark_excel_row_completed(self, row_idx: int, owner_name: str = ""):
        """Updates tree item and in-memory list when a row is marked completed in 0ms."""
        for r in self.excel_rows:
            if r["row"] == row_idx:
                r["is_completed"] = True
                if owner_name:
                    r["owner_name"] = owner_name
                break

        for item in self.excel_items:
            if item.data(0, ROLE_ROW_NUM) == row_idx:
                stt = item.data(0, ROLE_STT_NUM)
                serial = item.data(0, ROLE_SERIAL)
                item.setData(0, ROLE_IS_DONE, True)
                item.setText(0, f"✅ STT {stt:04d}: {serial}")
                item.setText(1, f"Dòng {row_idx} (Đã nhập: {owner_name or 'OK'})")
                item.setForeground(0, QColor("#2e7d32"))
                item.setForeground(1, QColor("#2e7d32"))
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                break

        # Update progress bar
        val = self.chunk_progress.value()
        if val < self.chunk_progress.maximum():
            self.chunk_progress.setValue(val + 1)

    def update_processed_status(self, folder_name: str, row_idx: int, stt: int):
        folder_clean = folder_name.lower()
        self.processed_map[folder_clean] = {"row": row_idx, "stt": stt}
        for item in self.folder_items:
            if item.data(0, ROLE_PARENT_FOLDER) == folder_name:
                item.setData(0, ROLE_IS_DONE, True)
                item.setData(0, ROLE_ROW_NUM, row_idx)
                item.setData(0, ROLE_STT_NUM, stt)
                item.setText(0, f"✅ {folder_name}")
                item.setText(1, f"Dòng {row_idx} (STT {stt})")
                item.setForeground(0, QColor("#2e7d32"))
                item.setForeground(1, QColor("#2e7d32"))
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                break

    def update_file_status(self, file_path: str, row_idx: int, stt: int):
        file_key = file_path.lower()
        self.file_map[file_key] = {"row": row_idx, "stt": stt}
        for item in self.file_items:
            if item.data(0, ROLE_PATH) == file_path:
                file_name = item.data(0, ROLE_FILE_NAME)
                fn_lower = file_name.lower()
                if "gcn" in fn_lower:
                    type_icon = "📜"
                elif "gtk" in fn_lower:
                    type_icon = "📐"
                elif "gt" in fn_lower or "cccd" in fn_lower or "cmnd" in fn_lower:
                    type_icon = "📑"
                elif "vo" in fn_lower or "chong" in fn_lower:
                    type_icon = "💍"
                else:
                    type_icon = "📄"

                item.setData(0, ROLE_IS_DONE, True)
                item.setData(0, ROLE_ROW_NUM, row_idx)
                item.setData(0, ROLE_STT_NUM, stt)
                item.setText(0, f"  ✅ {type_icon} {file_name}")
                item.setText(1, f"Dòng {row_idx} (STT {stt})")
                item.setForeground(0, QColor("#2e7d32"))
                item.setForeground(1, QColor("#2e7d32"))
                break

    def highlight_pdf_file(self, filename: str):
        if not filename or self.view_mode != "files":
            return
        fn_clean = os.path.basename(filename).lower()
        for item in self.file_items:
            if str(item.data(0, ROLE_FILE_NAME)).lower() == fn_clean:
                self._block_selection_signals = True
                self.tree_widget.setCurrentItem(item)
                self._block_selection_signals = False
                break

    def select_next_item(self):
        selected = self.tree_widget.selectedItems()
        if not selected:
            if self.tree_widget.topLevelItemCount() > 0:
                self.tree_widget.setCurrentItem(self.tree_widget.topLevelItem(0))
            return

        current_item = selected[0]
        next_item = self.tree_widget.itemBelow(current_item)
        if next_item:
            self.tree_widget.setCurrentItem(next_item)
            self.tree_widget.scrollToItem(next_item)
        else:
            cur_chunk = self.cbo_chunks.currentIndex()
            if cur_chunk < self.cbo_chunks.count() - 1:
                self.cbo_chunks.setCurrentIndex(cur_chunk + 1)
                if self.excel_items:
                    self.tree_widget.setCurrentItem(self.excel_items[0])

    def _filter_tree(self, text: str):
        query = text.strip().lower()
        if not query:
            for item in self.excel_items + self.folder_items + self.file_items:
                item.setHidden(False)
            return

        for item in self.excel_items:
            match = query in item.text(0).lower() or query in item.text(1).lower()
            item.setHidden(not match)

        for item in self.folder_items:
            match = query in item.text(0).lower() or query in item.text(1).lower()
            item.setHidden(not match)

        for item in self.file_items:
            match = query in item.text(0).lower() or query in item.text(1).lower()
            item.setHidden(not match)

    def _update_stats(self, total: int, completed: int):
        remaining = max(0, total - completed)
        pct = (completed / total * 100) if total > 0 else 0
        self.stats_lbl.setText(f"Tổng: {total} | Đã sửa: {completed} ({pct:.1f}%) | Còn: {remaining}")
