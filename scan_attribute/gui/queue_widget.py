"""
Queue Widget supporting 2 View Options:
1. "Chỉ Thư mục" (Compact Folder View)
2. "Chi tiết File PDF" (Expanded PDF Files View with icon classification and per-file marking)
"""

import os
from typing import List, Set, Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, 
    QTreeWidgetItem, QLabel, QPushButton, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

ROLE_PATH = int(Qt.ItemDataRole.UserRole)
ROLE_IS_DONE = int(Qt.ItemDataRole.UserRole) + 1
ROLE_ROW_NUM = int(Qt.ItemDataRole.UserRole) + 2
ROLE_STT_NUM = int(Qt.ItemDataRole.UserRole) + 3
ROLE_ITEM_TYPE = int(Qt.ItemDataRole.UserRole) + 4   # "folder" or "file"
ROLE_PARENT_FOLDER = int(Qt.ItemDataRole.UserRole) + 5
ROLE_FILE_NAME = int(Qt.ItemDataRole.UserRole) + 6


class QueueWidget(QWidget):
    folder_selected = Signal(str, str)             # Emits (serial_name, full_folder_path)
    file_selected = Signal(str, str, str)          # Emits (serial_name, full_folder_path, pdf_filename)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_dir = ""
        self.processed_map: Dict[str, Dict[str, Any]] = {}
        self.file_map: Dict[str, Dict[str, Any]] = {}
        self.view_mode = "folder"
        self.folder_items: List[QTreeWidgetItem] = []
        self.file_items: List[QTreeWidgetItem] = []
        self._block_selection_signals = False
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

        # 2 View Options Segmented Toggle Buttons
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

        self.btn_opt_folder = QPushButton("📁 Chỉ Thư mục")
        self.btn_opt_folder.setCheckable(True)
        self.btn_opt_folder.setChecked(True)

        self.btn_opt_files = QPushButton("📑 Chi tiết File PDF")
        self.btn_opt_files.setCheckable(True)

        self.btn_group_mode = QButtonGroup(self)
        self.btn_group_mode.addButton(self.btn_opt_folder, 0)
        self.btn_group_mode.addButton(self.btn_opt_files, 1)
        self.btn_group_mode.idClicked.connect(self._on_view_mode_changed)

        opt_layout.addWidget(self.btn_opt_folder)
        opt_layout.addWidget(self.btn_opt_files)
        layout.addWidget(opt_container)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm mã hồ sơ / tên file...")
        self.search_input.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_input)

        # Tree Widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Tên Thư mục / File PDF", "Vị trí Excel / Loại File"])
        self.tree_widget.setColumnWidth(0, 195)
        self.tree_widget.setAnimated(True)
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree_widget)

        # Footer Stats
        self.stats_lbl = QLabel("Tổng số: 0 | Đã nhập: 0 | Còn lại: 0")
        self.stats_lbl.setStyleSheet("color: #555; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.stats_lbl)

    def _on_view_mode_changed(self, btn_id: int):
        new_mode = "folder" if btn_id == 0 else "files"
        if new_mode != self.view_mode:
            self.view_mode = new_mode
            self.reload()

    def reload(self):
        if self.root_dir:
            self.load_folders(self.root_dir, self.processed_map)

    def load_folders(self, root_dir: str, processed_map: Dict[str, Dict[str, Any]], file_map: Optional[Dict[str, Dict[str, Any]]] = None):
        self.root_dir = root_dir
        self.processed_map = {k.lower(): v for k, v in processed_map.items()}
        if file_map is not None:
            self.file_map = {k.lower(): v for k, v in file_map.items()}
        self.folder_items.clear()
        self.file_items.clear()
        self.tree_widget.clear()

        if not os.path.exists(root_dir):
            self._update_stats(0, 0)
            return

        root_item = self.tree_widget.invisibleRootItem()
        self._build_tree_recursive(root_dir, root_item)

        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setExpanded(True)

        if self.view_mode == "files":
            processed_count = sum(1 for item in self.file_items if item.data(0, ROLE_IS_DONE))
            self._update_stats(len(self.file_items), processed_count)
        else:
            processed_count = sum(1 for item in self.folder_items if item.data(0, ROLE_IS_DONE))
            self._update_stats(len(self.folder_items), processed_count)

    def _build_tree_recursive(self, current_dir: str, parent_item: QTreeWidgetItem):
        try:
            entries = sorted(os.listdir(current_dir))
        except Exception:
            return

        subdirs = [e for e in entries if os.path.isdir(os.path.join(current_dir, e)) and not e.startswith('.') and not e.startswith('_') and e != '__pycache__']
        pdf_files = [e for e in entries if e.lower().endswith('.pdf')]

        # Check if current_dir directly contains PDFs (Leaf Folder)
        if pdf_files and parent_item != self.tree_widget.invisibleRootItem():
            serial_name = os.path.basename(current_dir)
            self._create_folder_item(parent_item, serial_name, current_dir, pdf_files)
            return

        # Process subdirectories
        for sub in subdirs:
            full_sub_path = os.path.join(current_dir, sub)
            try:
                sub_files = os.listdir(full_sub_path) if os.path.exists(full_sub_path) else []
            except Exception:
                sub_files = []

            has_pdfs = [f for f in sub_files if f.lower().endswith('.pdf')]
            has_subdirs = any(os.path.isdir(os.path.join(full_sub_path, f)) for f in sub_files if not f.startswith('.') and not f.startswith('_'))

            if has_pdfs:
                item = QTreeWidgetItem(parent_item)
                self._create_folder_item(item, sub, full_sub_path, has_pdfs)
            elif has_subdirs:
                item = QTreeWidgetItem(parent_item, [f"📁 {sub}", ""])
                item.setData(0, ROLE_ITEM_TYPE, "group")
                item.setData(0, ROLE_PATH, full_sub_path)
                item.setExpanded(True)
                self._build_tree_recursive(full_sub_path, item)

    def _create_folder_item(self, item: QTreeWidgetItem, serial_name: str, folder_path: str, pdf_files: List[str]):
        info = self.processed_map.get(serial_name.lower())
        is_done = info is not None
        pdf_count = len(pdf_files)

        if is_done:
            status_text = f"✅ Dòng {info['row']} (STT {info['stt']})"
            color = QColor("#2e7d32")
        else:
            status_text = f"⏳ Chờ nhập ({pdf_count} PDF)"
            color = QColor("#1565c0")

        item.setText(0, f"📜 {serial_name}")
        item.setText(1, status_text)
        item.setForeground(0, color)
        item.setForeground(1, color)
        item.setData(0, ROLE_ITEM_TYPE, "folder")
        item.setData(0, ROLE_PATH, folder_path)
        item.setData(0, ROLE_IS_DONE, is_done)

        self.folder_items.append(item)

        # In Option 2 ("Chi tiết File PDF"), add child items for each PDF file!
        if self.view_mode == "files" and pdf_files:
            item.setExpanded(True)
            self._add_pdf_children(item, folder_path, pdf_files, is_done)

    def _add_pdf_children(self, parent_item: QTreeWidgetItem, folder_path: str, pdf_files: List[str], folder_is_done: bool):
        # Priority order: GCN -> GT -> GTK -> others
        gcn_files = [f for f in pdf_files if 'gcn' in f.lower()]
        gt_files = [f for f in pdf_files if 'gt' in f.lower() and 'gcn' not in f.lower() and 'gtk' not in f.lower()]
        gtk_files = [f for f in pdf_files if 'gtk' in f.lower()]
        other_files = [f for f in pdf_files if f not in gcn_files and f not in gt_files and f not in gtk_files]

        ordered_pdfs = gcn_files + gt_files + gtk_files + other_files
        serial_name = os.path.basename(folder_path)

        done_child_count = 0
        for f in ordered_pdfs:
            f_lower = f.lower()
            if 'gcn' in f_lower:
                icon = "📜"
                desc = "[GCN] Giấy chứng nhận"
            elif 'gtk' in f_lower:
                icon = "📐"
                desc = "[GTK] Bản đồ / Khác"
            elif 'gt' in f_lower:
                icon = "📑"
                desc = "[GT] Tùy thân / CCCD"
            else:
                icon = "📄"
                desc = "[PDF] Đính kèm"

            full_file_path = os.path.join(folder_path, f)
            f_key = full_file_path.lower()
            file_info = self.file_map.get(f_key) or self.file_map.get(f_lower) or self.processed_map.get(f_lower) or self.processed_map.get(os.path.splitext(f_lower)[0])

            if file_info:
                file_is_done = True
                row_status = f"✅ Dòng {file_info['row']} (STT {file_info['stt']})"
                done_child_count += 1
            else:
                file_is_done = False
                row_status = f"⏳ Chờ nhập ({desc})"

            file_item = QTreeWidgetItem(parent_item, [f"  {icon} {f}", row_status])
            file_item.setData(0, ROLE_ITEM_TYPE, "file")
            file_item.setData(0, ROLE_PATH, full_file_path)
            file_item.setData(0, ROLE_PARENT_FOLDER, folder_path)
            file_item.setData(0, ROLE_FILE_NAME, f)
            file_item.setData(0, ROLE_IS_DONE, file_is_done)
            if file_info:
                file_item.setData(0, ROLE_ROW_NUM, file_info.get('row'))
                file_item.setData(0, ROLE_STT_NUM, file_info.get('stt'))

            if file_is_done:
                file_item.setForeground(0, QColor("#388e3c"))
                file_item.setForeground(1, QColor("#388e3c"))
            else:
                file_item.setForeground(0, QColor("#37474f"))
                file_item.setForeground(1, QColor("#78909c"))

            self.file_items.append(file_item)

        # Update parent folder header in files view mode
        total_child = len(ordered_pdfs)
        if done_child_count == total_child and total_child > 0:
            parent_item.setText(1, f"✅ Hoàn thành ({total_child}/{total_child} PDF)")
            parent_item.setForeground(0, QColor("#2e7d32"))
            parent_item.setForeground(1, QColor("#2e7d32"))
            parent_item.setData(0, ROLE_IS_DONE, True)
        elif done_child_count > 0:
            parent_item.setText(1, f"⏳ Đã nhập {done_child_count}/{total_child} PDF")
            parent_item.setForeground(0, QColor("#e65100"))
            parent_item.setForeground(1, QColor("#e65100"))
            parent_item.setData(0, ROLE_IS_DONE, False)
        else:
            parent_item.setText(1, f"⏳ Chờ nhập ({total_child} PDF)")
            parent_item.setForeground(0, QColor("#1565c0"))
            parent_item.setForeground(1, QColor("#1565c0"))
            parent_item.setData(0, ROLE_IS_DONE, False)

    def update_file_status(self, file_path: str, row_num: int, stt_num: int):
        """Updates status of a single PDF file and updates parent folder progress."""
        f_key = file_path.lower()
        self.file_map[f_key] = {"row": row_num, "stt": stt_num}
        base_name = os.path.basename(file_path).lower()
        self.file_map[base_name] = {"row": row_num, "stt": stt_num}

        parent_tree_item = None
        for f_item in self.file_items:
            item_path = str(f_item.data(0, ROLE_PATH) or "").lower()
            item_fn = str(f_item.data(0, ROLE_FILE_NAME) or "").lower()
            if item_path == f_key or item_fn == base_name:
                f_item.setText(1, f"✅ Dòng {row_num} (STT {stt_num})")
                f_item.setData(0, ROLE_IS_DONE, True)
                f_item.setData(0, ROLE_ROW_NUM, row_num)
                f_item.setData(0, ROLE_STT_NUM, stt_num)
                f_item.setForeground(0, QColor("#2e7d32"))
                f_item.setForeground(1, QColor("#2e7d32"))
                parent_tree_item = f_item.parent()
                break

        if parent_tree_item:
            total_c = parent_tree_item.childCount()
            done_c = sum(1 for i in range(total_c) if parent_tree_item.child(i).data(0, ROLE_IS_DONE))
            if done_c == total_c and total_c > 0:
                parent_tree_item.setText(1, f"✅ Hoàn thành ({total_c}/{total_c} PDF)")
                parent_tree_item.setForeground(0, QColor("#2e7d32"))
                parent_tree_item.setForeground(1, QColor("#2e7d32"))
                parent_tree_item.setData(0, ROLE_IS_DONE, True)
            elif done_c > 0:
                parent_tree_item.setText(1, f"⏳ Đã nhập {done_c}/{total_c} PDF")
                parent_tree_item.setForeground(0, QColor("#e65100"))
                parent_tree_item.setForeground(1, QColor("#e65100"))
                parent_tree_item.setData(0, ROLE_IS_DONE, False)

        processed_count = sum(1 for item in self.file_items if item.data(0, ROLE_IS_DONE))
        self._update_stats(len(self.file_items), processed_count)

    def update_processed_status(self, serial: str, row_num: int, stt_num: int):
        self.processed_map[serial.lower()] = {"serial": serial, "row": row_num, "stt": stt_num}
        processed_count = 0
        for item in self.folder_items:
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

        self._update_stats(len(self.folder_items), processed_count)

    def _update_stats(self, total: int, processed: int):
        remaining = total - processed
        unit = "file" if self.view_mode == "files" else "hồ sơ"
        self.stats_lbl.setText(f"Tổng số: {total} {unit} | Đã nhập: {processed} | Còn lại: {remaining}")

    def _filter_tree(self, text: str):
        query = text.strip().lower()
        if not query:
            for item in self.folder_items:
                item.setHidden(False)
                p = item.parent()
                while p:
                    p.setHidden(False)
                    p = p.parent()
            for f_item in self.file_items:
                f_item.setHidden(False)
            return

        for item in self.folder_items:
            path = item.data(0, ROLE_PATH) or ""
            name = os.path.basename(path).lower()
            match_folder = query in name

            # Check if any child file matches
            match_any_child = False
            for i in range(item.childCount()):
                child = item.child(i)
                child_name = (child.data(0, ROLE_FILE_NAME) or "").lower()
                child_match = query in child_name
                child.setHidden(not child_match and not match_folder)
                if child_match:
                    match_any_child = True

            visible = match_folder or match_any_child
            item.setHidden(not visible)

            if visible:
                p = item.parent()
                while p:
                    p.setHidden(False)
                    p.setExpanded(True)
                    p = p.parent()

    def _on_selection_changed(self):
        if self._block_selection_signals:
            return

        items = self.tree_widget.selectedItems()
        if not items:
            return

        item = items[0]
        item_type = item.data(0, ROLE_ITEM_TYPE)

        if item_type == "file":
            parent_folder = item.data(0, ROLE_PARENT_FOLDER)
            file_name = item.data(0, ROLE_FILE_NAME)
            if parent_folder and os.path.exists(parent_folder):
                serial_name = os.path.basename(parent_folder)
                self.file_selected.emit(serial_name, parent_folder, file_name)
        elif item_type == "folder":
            full_path = item.data(0, ROLE_PATH)
            if full_path and os.path.exists(full_path):
                serial_name = os.path.basename(full_path)
                self.folder_selected.emit(serial_name, full_path)

    def highlight_pdf_file(self, filename: str):
        """Highlights the child item in tree matching filename without triggering signal loops."""
        if not filename or self.view_mode != "files":
            return

        fn_clean = os.path.basename(filename).lower()
        for f_item in self.file_items:
            item_fn = str(f_item.data(0, ROLE_FILE_NAME) or "").lower()
            if item_fn == fn_clean:
                self._block_selection_signals = True
                self.tree_widget.setCurrentItem(f_item)
                self.tree_widget.scrollToItem(f_item)
                self._block_selection_signals = False
                break

    def select_next_item(self):
        """Auto advances selection to next item based on current view mode."""
        if self.view_mode == "files":
            if not self.file_items:
                return
            curr_items = self.tree_widget.selectedItems()
            if not curr_items:
                self.tree_widget.setCurrentItem(self.file_items[0])
                self.tree_widget.scrollToItem(self.file_items[0])
                return
            curr = curr_items[0]
            if curr in self.file_items:
                idx = self.file_items.index(curr)
                if idx < len(self.file_items) - 1:
                    next_item = self.file_items[idx + 1]
                    self.tree_widget.setCurrentItem(next_item)
                    self.tree_widget.scrollToItem(next_item)
            else:
                self.tree_widget.setCurrentItem(self.file_items[0])
                self.tree_widget.scrollToItem(self.file_items[0])
        else:
            self.select_next_folder()

    def select_next_folder(self):
        if not self.folder_items:
            return
        curr_items = self.tree_widget.selectedItems()
        if not curr_items:
            self.tree_widget.setCurrentItem(self.folder_items[0])
            self.tree_widget.scrollToItem(self.folder_items[0])
            return

        curr = curr_items[0]
        if curr.data(0, ROLE_ITEM_TYPE) == "file":
            curr = curr.parent() or curr

        try:
            idx = self.folder_items.index(curr)
            if idx < len(self.folder_items) - 1:
                next_f = self.folder_items[idx + 1]
                self.tree_widget.setCurrentItem(next_f)
                self.tree_widget.scrollToItem(next_f)
        except ValueError:
            self.tree_widget.setCurrentItem(self.folder_items[0])
            self.tree_widget.scrollToItem(self.folder_items[0])

