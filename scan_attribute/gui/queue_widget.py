"""
Queue Widget supporting Multi-Level Nested Folder Tree View (QTreeWidget) with Excel Row & STT Tracking.
"""

import os
from typing import List, Set, Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, 
    QTreeWidgetItem, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

ROLE_PATH = int(Qt.ItemDataRole.UserRole)
ROLE_IS_DONE = int(Qt.ItemDataRole.UserRole) + 1
ROLE_ROW_NUM = int(Qt.ItemDataRole.UserRole) + 2
ROLE_STT_NUM = int(Qt.ItemDataRole.UserRole) + 3


class QueueWidget(QWidget):
    folder_selected = Signal(str, str)  # Emits (serial_name, full_folder_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_dir = ""
        self.processed_map: Dict[str, Dict[str, Any]] = {}
        self.leaf_items: List[QTreeWidgetItem] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header_lbl = QLabel("📁 Cấu trúc Thư mục Hồ sơ")
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        header_lbl.setFont(font)
        layout.addWidget(header_lbl)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm mã hồ sơ (Ví dụ: AE 345823)...")
        self.search_input.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_input)

        # Tree Widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Tên Thư mục / Mã HS", "Vị trí trên Excel"])
        self.tree_widget.setColumnWidth(0, 190)
        self.tree_widget.setAnimated(True)
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree_widget)

        # Footer Stats
        self.stats_lbl = QLabel("Tổng số: 0 | Đã nhập: 0 | Còn lại: 0")
        self.stats_lbl.setStyleSheet("color: #555; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.stats_lbl)

    def load_folders(self, root_dir: str, processed_map: Dict[str, Dict[str, Any]]):
        self.root_dir = root_dir
        self.processed_map = {k.lower(): v for k, v in processed_map.items()}
        self.leaf_items.clear()
        self.tree_widget.clear()

        if not os.path.exists(root_dir):
            self._update_stats(0, 0)
            return

        root_item = self.tree_widget.invisibleRootItem()
        self._build_tree_recursive(root_dir, root_item)

        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setExpanded(True)

        processed_count = sum(1 for item in self.leaf_items if item.data(0, ROLE_IS_DONE))
        self._update_stats(len(self.leaf_items), processed_count)

    def _build_tree_recursive(self, current_dir: str, parent_item: QTreeWidgetItem):
        try:
            entries = sorted(os.listdir(current_dir))
        except Exception:
            return

        subdirs = [e for e in entries if os.path.isdir(os.path.join(current_dir, e)) and not e.startswith('.') and not e.startswith('_') and e != '__pycache__']
        pdf_files = [e for e in entries if e.lower().endswith('.pdf')]

        # If current_dir directly contains PDFs, it's a Leaf Node!
        if pdf_files and parent_item != self.tree_widget.invisibleRootItem():
            serial_name = os.path.basename(current_dir)
            info = self.processed_map.get(serial_name.lower())
            is_done = info is not None

            parent_item.setText(0, f"📜 {serial_name}")
            if is_done:
                row_str = f"✅ Dòng {info['row']} (STT {info['stt']})"
                parent_item.setText(1, row_str)
                parent_item.setForeground(0, QColor("#2e7d32"))
                parent_item.setForeground(1, QColor("#2e7d32"))
            else:
                parent_item.setText(1, "⏳ Chờ nhập")
                parent_item.setForeground(0, QColor("#1565c0"))
                parent_item.setForeground(1, QColor("#1565c0"))

            parent_item.setData(0, ROLE_PATH, current_dir)
            parent_item.setData(0, ROLE_IS_DONE, is_done)

            self.leaf_items.append(parent_item)
            return

        # Process subdirectories
        for sub in subdirs:
            full_sub_path = os.path.join(current_dir, sub)
            try:
                sub_files = os.listdir(full_sub_path) if os.path.exists(full_sub_path) else []
            except Exception:
                sub_files = []

            has_pdfs = any(f.lower().endswith('.pdf') for f in sub_files)
            has_subdirs = any(os.path.isdir(os.path.join(full_sub_path, f)) for f in sub_files if not f.startswith('.') and not f.startswith('_'))

            if has_pdfs:
                info = self.processed_map.get(sub.lower())
                is_done = info is not None
                status_text = f"✅ Dòng {info['row']} (STT {info['stt']})" if is_done else "⏳ Chờ nhập"

                item = QTreeWidgetItem(parent_item, [f"📜 {sub}", status_text])
                item.setData(0, ROLE_PATH, full_sub_path)
                item.setData(0, ROLE_IS_DONE, is_done)

                if is_done:
                    item.setForeground(0, QColor("#2e7d32"))
                    item.setForeground(1, QColor("#2e7d32"))
                else:
                    item.setForeground(0, QColor("#1565c0"))
                    item.setForeground(1, QColor("#1565c0"))

                self.leaf_items.append(item)

            elif has_subdirs:
                item = QTreeWidgetItem(parent_item, [f"📁 {sub}", ""])
                item.setData(0, ROLE_PATH, full_sub_path)
                item.setExpanded(True)
                self._build_tree_recursive(full_sub_path, item)

    def update_processed_status(self, serial: str, row_num: int, stt_num: int):
        self.processed_map[serial.lower()] = {"serial": serial, "row": row_num, "stt": stt_num}
        processed_count = 0
        for item in self.leaf_items:
            path = item.data(0, ROLE_PATH)
            if path:
                s_name = os.path.basename(path)
                info = self.processed_map.get(s_name.lower())
                is_done = info is not None
                if is_done:
                    item.setText(1, f"✅ Dòng {info['row']} (STT {info['stt']})")
                    item.setData(0, ROLE_IS_DONE, True)
                    item.setForeground(0, QColor("#2e7d32"))
                    item.setForeground(1, QColor("#2e7d32"))
                    processed_count += 1
                else:
                    item.setText(1, "⏳ Chờ nhập")
                    item.setData(0, ROLE_IS_DONE, False)
                    item.setForeground(0, QColor("#1565c0"))
                    item.setForeground(1, QColor("#1565c0"))

        self._update_stats(len(self.leaf_items), processed_count)

    def _update_stats(self, total: int, processed: int):
        remaining = total - processed
        self.stats_lbl.setText(f"Tổng số: {total} | Đã nhập: {processed} | Còn lại: {remaining}")

    def _filter_tree(self, text: str):
        query = text.strip().lower()
        if not query:
            for item in self.leaf_items:
                item.setHidden(False)
                p = item.parent()
                while p:
                    p.setHidden(False)
                    p = p.parent()
            return

        for item in self.leaf_items:
            path = item.data(0, ROLE_PATH) or ""
            name = os.path.basename(path).lower()
            match = query in name
            item.setHidden(not match)

            if match:
                p = item.parent()
                while p:
                    p.setHidden(False)
                    p.setExpanded(True)
                    p = p.parent()

    def _on_selection_changed(self):
        items = self.tree_widget.selectedItems()
        if items:
            item = items[0]
            full_path = item.data(0, ROLE_PATH)
            if full_path and os.path.exists(full_path):
                serial_name = os.path.basename(full_path)
                self.folder_selected.emit(serial_name, full_path)

    def select_next_folder(self):
        if not self.leaf_items:
            return
        curr_items = self.tree_widget.selectedItems()
        if not curr_items:
            self.tree_widget.setCurrentItem(self.leaf_items[0])
            return

        curr = curr_items[0]
        try:
            idx = self.leaf_items.index(curr)
            if idx < len(self.leaf_items) - 1:
                self.tree_widget.setCurrentItem(self.leaf_items[idx + 1])
        except ValueError:
            self.tree_widget.setCurrentItem(self.leaf_items[0])
