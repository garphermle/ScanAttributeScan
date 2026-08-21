"""
Form Widget with an Ultra-Spacious, High-Visibility Focus Area (Cols 43, 44, 93, 110 + Serial 2)
and Organized Tabbed Sections (Cols 1-186 + Full 186-column support).
Col 93 is a full-width SearchableComboBox on its own line. Cols 91 & 94 are omitted from auto-fill.
Zero default values: clean & empty.
Designed for ultra-fast keyboard-only and OCR data entry.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout, 
    QLineEdit, QComboBox, QCheckBox, QLabel, QGroupBox, QPlainTextEdit,
    QPushButton, QScrollArea, QCompleter, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QFont
from scan_attribute.core.data_models import MasterDataManager, CommuneInfo, MeasurementInfo


DEFAULT_NOI_CAP_LIST = [
    "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Cục Cảnh sát đăng ký quản lý cư trú và dữ liệu quốc gia về dân cư",
    "Công an Tỉnh Quảng Ninh",
    "Cục CSQLHC về TTXH",
    "Cục CS ĐKQL cư trú và DLQG về dân cư",
    "Công an tỉnh Quảng Ninh"
]


class VerticalOnlyScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.horizontalScrollBar().setEnabled(False)
        self.horizontalScrollBar().valueChanged.connect(self._lock_horizontal_scroll)

    def _lock_horizontal_scroll(self, val):
        if val != 0:
            self.horizontalScrollBar().setValue(0)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(0, dy)

    def ensureWidgetVisible(self, child_widget, xmargin=50, ymargin=50):
        if not child_widget or not self.widget():
            return
        try:
            val = self.verticalScrollBar().value()
            target_rect = child_widget.rect()
            pos = child_widget.mapTo(self.widget(), target_rect.topLeft())
            viewport_height = self.viewport().height()

            top = pos.y()
            bottom = pos.y() + child_widget.height()

            if top < val + ymargin:
                self.verticalScrollBar().setValue(max(0, top - ymargin))
            elif bottom > val + viewport_height - ymargin:
                self.verticalScrollBar().setValue(bottom - viewport_height + ymargin)
        except Exception:
            pass
        self.horizontalScrollBar().setValue(0)


class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(6)
        self.setMaxVisibleItems(15)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QComboBox {
                min-height: 34px;
                max-height: 38px;
                font-size: 14px;
                padding: 2px 8px;
                border: 1.5px solid #90caf9;
                border-radius: 4px;
                background-color: #ffffff;
                color: #0d47a1;
            }
            QComboBox:focus {
                border: 2.5px solid #d32f2f;
                background-color: #fffde7;
            }
            QComboBox QAbstractItemView {
                min-width: 480px;
                font-size: 13px;
                background-color: #ffffff;
                color: #212121;
                selection-background-color: #1976d2;
                selection-color: #ffffff;
                border: 1.5px solid #1976d2;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 4px 8px;
                color: #212121;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #bbdefb;
                color: #0d47a1;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
        """)

        comp = self.completer()
        if comp:
            comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        if self.lineEdit():
            self.lineEdit().setPlaceholderText("🔍 Tìm theo tên hoặc mã xã/phường (gõ để tìm)...")

    def wheelEvent(self, event):
        event.ignore()


class AttributeFormWidget(QWidget):
    save_requested = Signal()

    def __init__(self, master_data: MasterDataManager, parent=None):
        super().__init__(parent)
        self.master_data = master_data
        self.last_commune_code: str = ""
        self.field_inputs: Dict[int, QWidget] = {}
        self.active_input_widget: Optional[QWidget] = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. PRIMARY QUICK-FILL FOCUS AREA (Cols 43, 44, 93, 110 + Serial 2)
        # -------------------------------------------------------------
        focus_card = QFrame()
        focus_card.setStyleSheet("""
            QFrame#FocusCard {
                background-color: #f4f9ff;
                border: 2.5px solid #2196f3;
                border-radius: 8px;
                padding: 6px;
            }
            QLabel.focus-label {
                font-size: 13px;
                font-weight: bold;
                color: #0d47a1;
            }
            QLineEdit.focus-input {
                font-size: 15px;
                font-weight: bold;
                min-height: 34px;
                max-height: 38px;
                border: 2px solid #90caf9;
                border-radius: 4px;
                padding: 2px 8px;
                background-color: #ffffff;
                color: #1a237e;
            }
            QLineEdit.focus-input:focus {
                border: 2.5px solid #d32f2f;
                background-color: #fffde7;
            }
            QPlainTextEdit.focus-input {
                font-size: 14px;
                font-weight: normal;
                min-height: 65px;
                max-height: 85px;
                border: 2px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #ffffff;
                color: #212121;
            }
            QPlainTextEdit.focus-input:focus {
                border: 2.5px solid #d32f2f;
                background-color: #fffde7;
            }
        """)
        focus_card.setObjectName("FocusCard")
        focus_layout = QVBoxLayout(focus_card)
        focus_layout.setContentsMargins(10, 8, 10, 8)
        focus_layout.setSpacing(8)

        # Header of Focus Card
        focus_title_row = QHBoxLayout()
        focus_title = QLabel("⚡ VÙNG NHẬP TRỌNG TÂM (Số thửa • Số tờ • Xã, huyện, tỉnh • Ghi chú T2)")
        font_title = QFont()
        font_title.setBold(True)
        font_title.setPointSize(11)
        focus_title.setFont(font_title)
        focus_title.setStyleSheet("color: #0d47a1; font-weight: bold;")
        focus_title_row.addWidget(focus_title)
        focus_title_row.addStretch()

        self.btn_toggle_tabs = QPushButton("🔄 Đổi Chế Độ Tab (Tùy Chọn / Đầy Đủ)")
        self.btn_toggle_tabs.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 4px 10px;
                font-weight: bold;
                background-color: #1976d2;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.btn_toggle_tabs.clicked.connect(self._toggle_view_mode)
        focus_title_row.addWidget(self.btn_toggle_tabs)

        focus_layout.addLayout(focus_title_row)

        # Row 1: Số Serial (2)
        r_serial = QHBoxLayout()
        lbl_s = QLabel("🏷️ Số Serial (2):")
        lbl_s.setProperty("class", "focus-label")
        lbl_s.setFixedWidth(160)
        self.txt_serial = QLineEdit()
        self.txt_serial.setProperty("class", "focus-input")
        self.txt_serial.setStyleSheet("background-color: #e8ecef; color: #37474f; font-size: 14px; font-weight: bold; min-height: 32px;")
        self.txt_serial.textChanged.connect(self._auto_sync_ma_don)
        self._register_input(2, self.txt_serial)
        r_serial.addWidget(lbl_s)
        r_serial.addWidget(self.txt_serial, stretch=1)
        focus_layout.addLayout(r_serial)

        # Row 2: Số thửa (43) (*)
        r_thua = QHBoxLayout()
        lbl_thua = QLabel("📌 Số thửa (43) (*):")
        lbl_thua.setProperty("class", "focus-label")
        lbl_thua.setFixedWidth(160)
        self.txt_thua_so = QLineEdit()
        self.txt_thua_so.setProperty("class", "focus-input")
        self.txt_thua_so.setPlaceholderText("Ví dụ: 124 (Tự động đặt con trỏ nhập ở đây)")
        self._register_input(43, self.txt_thua_so)
        r_thua.addWidget(lbl_thua)
        r_thua.addWidget(self.txt_thua_so, stretch=1)
        focus_layout.addLayout(r_thua)

        # Row 3: Số tờ (44) (*)
        r_to = QHBoxLayout()
        lbl_to = QLabel("📄 Số tờ (44) (*):")
        lbl_to.setProperty("class", "focus-label")
        lbl_to.setFixedWidth(160)
        self.txt_thua_to = QLineEdit()
        self.txt_thua_to.setProperty("class", "focus-input")
        self.txt_thua_to.setPlaceholderText("Ví dụ: 71")
        self._register_input(44, self.txt_thua_to)
        r_to.addWidget(lbl_to)
        r_to.addWidget(self.txt_thua_to, stretch=1)
        focus_layout.addLayout(r_to)

        # Row 4: Xã, huyện, tỉnh (93) (*) - Chiếm trọn 1 dòng to rõ
        r_xa = QHBoxLayout()
        lbl_xa = QLabel("🏛️ Xã, huyện, tỉnh (93) (*):")
        lbl_xa.setProperty("class", "focus-label")
        lbl_xa.setFixedWidth(160)

        self.cmb_thua_xa = SearchableComboBox()
        self._populate_communes(self.cmb_thua_xa)
        self._register_input(93, self.cmb_thua_xa)

        # Backward compatibility alias
        self.txt_thua_xa_huyen_tinh = self.cmb_thua_xa

        r_xa.addWidget(lbl_xa)
        r_xa.addWidget(self.cmb_thua_xa, stretch=1)
        focus_layout.addLayout(r_xa)

        # Row 5: Ghi chú trang 2 (110)
        r_gc = QVBoxLayout()
        lbl_gc2 = QLabel("📝 Ghi chú trang 2 (110) [Kéo chuột OCR để tự dán vào]:")
        lbl_gc2.setProperty("class", "focus-label")
        self.txt_ghi_chu_t2 = QPlainTextEdit()
        self.txt_ghi_chu_t2.setProperty("class", "focus-input")
        self.txt_ghi_chu_t2.setPlaceholderText("Nhập nội dung ghi chú trang 2 hoặc quét chuột OCR trên văn bản PDF...")
        self._register_input(110, self.txt_ghi_chu_t2)
        r_gc.addWidget(lbl_gc2)
        r_gc.addWidget(self.txt_ghi_chu_t2)
        focus_layout.addLayout(r_gc)

        root_layout.addWidget(focus_card)

        # -------------------------------------------------------------
        # 2. TABBED SECTIONS MAPPING ALL 186 COLUMNS
        # -------------------------------------------------------------
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
            }
        """)

        # Tab 0: GCN & Ký cấp (Cols 1-4, 99-109)
        self.tab_gcn = self._create_tab_gcn()
        # Tab 1: Chủ sử dụng (Cols 5-25)
        self.tab_chu = self._create_tab_chu()
        # Tab 2: Vợ (Chồng) (Cols 26-42)
        self.tab_vo = self._create_tab_vo_chong()
        # Tab 3: Thửa đất & MĐSD (Cols 45-98)
        self.tab_thua = self._create_tab_thua_dat()
        # Tab 4: NVTC & Hạn chế (Cols 111-133)
        self.tab_nvtc = self._create_tab_nvtc()
        # Tab 5: Tài sản & Lưu kho (Cols 134-186)
        self.tab_taisan = self._create_tab_tai_san_va_khac()

        self._show_full_tabs = True
        self._build_tab_list()

        self.tab_widget.currentChanged.connect(self._on_tab_switched)
        root_layout.addWidget(self.tab_widget, stretch=1)

        # -------------------------------------------------------------
        # 3. BOTTOM ACTION BAR
        # -------------------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(4, 4, 4, 4)
        self.lbl_status = QLabel("📍 Đang nhắm: Số thửa (43)")
        self.lbl_status.setStyleSheet("color: #1565c0; font-weight: bold; font-size: 12px;")
        
        self.btn_save = QPushButton("💾 LƯU & HỒ SƠ TIẾP THEO (Ctrl+Enter)")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_save.clicked.connect(self.save_requested.emit)

        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)
        root_layout.addLayout(btn_row)

        # Tab Order: 43 -> 44 -> 93 -> 110 -> Save
        QWidget.setTabOrder(self.txt_thua_so, self.txt_thua_to)
        QWidget.setTabOrder(self.txt_thua_to, self.cmb_thua_xa)
        QWidget.setTabOrder(self.cmb_thua_xa, self.txt_ghi_chu_t2)
        QWidget.setTabOrder(self.txt_ghi_chu_t2, self.btn_save)

        self.active_input_widget = self.txt_thua_so
        self._track_focus()

    def _build_tab_list(self):
        self.tab_widget.blockSignals(True)
        self.tab_widget.clear()
        if self._show_full_tabs:
            self.tab_widget.addTab(self.tab_gcn, "1. GCN & Ký Cấp (1-4, 99-109)")
            self.tab_widget.addTab(self.tab_chu, "2. Chủ Sử Dụng (5-25)")
            self.tab_widget.addTab(self.tab_vo, "3. Vợ / Chồng (26-42)")
            self.tab_widget.addTab(self.tab_thua, "4. Thửa Đất & MĐSD (45-98)")
            self.tab_widget.addTab(self.tab_nvtc, "5. NVTC & Hạn Chế (111-133)")
            self.tab_widget.addTab(self.tab_taisan, "6. Tài Sản & Lưu Kho (134-186)")
            self.btn_toggle_tabs.setText("⚡ Thu gọn (Chỉ hiện Tùy chọn 111-186)")
        else:
            self.tab_widget.addTab(self.tab_nvtc, "1. ⚠️ Hạn Chế & NVTC (111-133)")
            self.tab_widget.addTab(self.tab_taisan, "2. 🏡 Tài Sản & Lưu Kho (134-186)")
            self.tab_widget.addTab(self.tab_gcn, "3. GCN & Ký Cấp (1-4, 99-109)")
            self.tab_widget.addTab(self.tab_chu, "4. Chủ Sử Dụng (5-25)")
            self.tab_widget.addTab(self.tab_vo, "5. Vợ / Chồng (26-42)")
            self.tab_widget.addTab(self.tab_thua, "6. Thửa Đất & MĐSD (45-98)")
            self.btn_toggle_tabs.setText("📋 Hiện đầy đủ 6 Tab chuẩn")
        self.tab_widget.blockSignals(False)

    def _toggle_view_mode(self):
        self._show_full_tabs = not self._show_full_tabs
        self._build_tab_list()

    def _setup_form_layout(self, form: QFormLayout):
        form.setContentsMargins(4, 4, 4, 4)
        form.setVerticalSpacing(3)
        form.setHorizontalSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

    def _create_scroll_area(self, widget: QWidget) -> QScrollArea:
        scroll = VerticalOnlyScrollArea()
        scroll.setWidget(widget)
        return scroll

    def _register_input(self, col_idx: int, widget: QWidget):
        self.field_inputs[col_idx] = widget
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return widget

    def _on_tab_switched(self, index: int):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QScrollArea):
            current_widget.verticalScrollBar().setValue(0)
            current_widget.horizontalScrollBar().setValue(0)
        if index == 3 and hasattr(self, 'txt_thua_so'):
            self.txt_thua_so.setFocus()
            self.active_input_widget = self.txt_thua_so
            self._highlight_active_field(self.txt_thua_so, 43)

    def _track_focus(self):
        for c, widget in self.field_inputs.items():
            if isinstance(widget, (QLineEdit, QPlainTextEdit, QComboBox)):
                widget.installEventFilter(self)
                if isinstance(widget, QComboBox) and widget.isEditable() and widget.lineEdit():
                    widget.lineEdit().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == event.Type.Wheel:
            if isinstance(watched, QComboBox) or (watched and isinstance(watched.parent(), QComboBox)):
                event.ignore()
                return True
        if event.type() in (event.Type.FocusIn, event.Type.MouseButtonPress):
            for col, w in self.field_inputs.items():
                if w == watched or (isinstance(w, QComboBox) and w.lineEdit() == watched):
                    self.active_input_widget = w
                    self._highlight_active_field(w, col)
                    break
        return super().eventFilter(watched, event)

    def _highlight_active_field(self, target_widget, col_idx: int):
        field_names = {
            2: "Số Serial", 3: "Mã HS Gốc", 4: "Mã vạch",
            9: "Họ tên Chủ", 14: "CCCD Chủ",
            43: "Số thửa", 44: "Số tờ", 93: "Xã, huyện, tỉnh", 110: "Ghi chú T2",
            111: "Loại hạn chế", 112: "DT hạn chế", 113: "Nội dung hạn chế", 114: "Số VB hạn chế",
            118: "Loại NVTC", 119: "Tổng tiền NVTC", 121: "Tiền nợ NVTC",
            134: "DTXD Nhà ở", 135: "DTS Nhà ở", 142: "Tên CTXD", 155: "Tên CT ngầm",
            163: "Tên rừng", 166: "Tên cây lâu năm", 170: "Số thửa cũ", 179: "Kho lưu", 183: "Thư mục HSQ"
        }
        name = field_names.get(col_idx, f"Cột {col_idx}")
        self.lbl_status.setText(f"📍 Đang nhắm ô: [{name}] (OCR/Scan sẽ dán vào đây)")

    def set_ocr_text_to_active_field(self, text: str):
        if not text:
            return
        clean_text = text.strip()

        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_text)

        target = self.active_input_widget or self.txt_thua_so
        if target:
            if isinstance(target, QLineEdit):
                target.setText(clean_text)
            elif isinstance(target, QPlainTextEdit):
                target.setPlainText(clean_text)
            elif isinstance(target, QComboBox):
                target.setEditText(clean_text)

    def navigate_to_pdf_type(self, pdf_filename: str):
        if not pdf_filename:
            return
        fn = pdf_filename.lower()
        if "vo" in fn or "chong" in fn or "vc" in fn or "spouse" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(2)
            if not self.chk_has_spouse.isChecked():
                self.chk_has_spouse.setChecked(True)
            self.txt_vo_name.setFocus()
            self.active_input_widget = self.txt_vo_name
            self._highlight_active_field(self.txt_vo_name, 26)
        elif "gtk" in fn or "bando" in fn or "trichdo" in fn or "td" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(3)
            self.txt_thua_so.setFocus()
            self.active_input_widget = self.txt_thua_so
            self._highlight_active_field(self.txt_thua_so, 43)
        elif "gt" in fn or "cccd" in fn or "cmnd" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(1)
            self.txt_chu_name.setFocus()
            self.active_input_widget = self.txt_chu_name
            self._highlight_active_field(self.txt_chu_name, 9)
        elif "nvtc" in fn or "thue" in fn or "tien" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(4)
            if not self.chk_has_nvtc.isChecked():
                self.chk_has_nvtc.setChecked(True)
            self.cmb_nvtc_loai.setFocus()
            self.active_input_widget = self.cmb_nvtc_loai
            self._highlight_active_field(self.cmb_nvtc_loai, 118)
        elif "ts" in fn or "nha" in fn or "kho" in fn or "tsglvd" in fn or "congtrinh" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(5)
            self.txt_nha_dt_xd.setFocus()
            self.active_input_widget = self.txt_nha_dt_xd
            self._highlight_active_field(self.txt_nha_dt_xd, 134)
        elif "gcn" in fn or "bia" in fn or "giaychungnhan" in fn:
            if self._show_full_tabs:
                self.tab_widget.setCurrentIndex(0)
            self.txt_barcode.setFocus()
            self.active_input_widget = self.txt_barcode
            self._highlight_active_field(self.txt_barcode, 4)
        else:
            self.txt_thua_so.setFocus()
            self.active_input_widget = self.txt_thua_so
            self._highlight_active_field(self.txt_thua_so, 43)

        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QScrollArea):
            current_widget.verticalScrollBar().setValue(0)
            current_widget.horizontalScrollBar().setValue(0)

    # -------------------------------------------------------------
    # TAB 1: GCN & KÝ CẤP (Cols 1-4, 99-109)
    # -------------------------------------------------------------
    def _create_tab_gcn(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        self._setup_form_layout(form)

        self.txt_ma_hs = QLineEdit()
        self._register_input(3, self.txt_ma_hs)

        self.txt_barcode = QLineEdit()
        self.txt_barcode.setPlaceholderText("Ví dụ: 0667320081887")
        self.txt_barcode.textChanged.connect(self._auto_sync_ma_hs_goc)
        self._register_input(4, self.txt_barcode)

        self.cmb_loai_gcn = SearchableComboBox()
        self.cmb_loai_gcn.addItem("[Không chọn]", "")
        for g in self.master_data.gcn_types:
            self.cmb_loai_gcn.addItem(g, g)
        self._register_input(99, self.cmb_loai_gcn)

        self.txt_so_vao_so = QLineEdit()
        self._register_input(100, self.txt_so_vao_so)

        self.txt_ngay_vao_so = QLineEdit()
        self.txt_ngay_vao_so.textChanged.connect(self._auto_sync_ngay_vao_so)
        self._register_input(101, self.txt_ngay_vao_so)

        self.txt_ngay_ky = QLineEdit()
        self.txt_ngay_ky.textChanged.connect(self._auto_sync_ngay_cap)
        self._register_input(102, self.txt_ngay_ky)

        self.txt_nguoi_ky = QLineEdit()
        self._register_input(103, self.txt_nguoi_ky)

        self.cmb_uy_quyen_ky = SearchableComboBox()
        self.cmb_uy_quyen_ky.addItem("[Không chọn]", "")
        self.cmb_uy_quyen_ky.addItem("0 - Không ủy quyền", "0")
        self.cmb_uy_quyen_ky.addItem("1 - Có ủy quyền", "1")
        self._register_input(104, self.cmb_uy_quyen_ky)

        self.cmb_ky_thay = SearchableComboBox()
        self.cmb_ky_thay.addItem("[Không chọn]", "")
        self.cmb_ky_thay.addItem("0 - Ký trực tiếp", "0")
        self.cmb_ky_thay.addItem("1 - Ký thay (KT.)", "1")
        self._register_input(105, self.cmb_ky_thay)

        self.txt_ngay_cap = QLineEdit()
        self._register_input(106, self.txt_ngay_cap)

        self.txt_ten_dot_cap = QLineEdit()
        self._register_input(107, self.txt_ten_dot_cap)

        self.txt_can_cu_phap_ly = QLineEdit()
        self._register_input(108, self.txt_can_cu_phap_ly)

        self.txt_ghi_chu_t1 = QLineEdit()
        self._register_input(109, self.txt_ghi_chu_t1)

        form.addRow("Mã HS Gốc (3):", self.txt_ma_hs)
        form.addRow("Mã vạch (4):", self.txt_barcode)
        form.addRow("Loại GCN (99):", self.cmb_loai_gcn)
        form.addRow("Số vào sổ (100):", self.txt_so_vao_so)
        form.addRow("Ngày vào sổ (101):", self.txt_ngay_vao_so)
        form.addRow("Ngày ký (102):", self.txt_ngay_ky)
        form.addRow("Người ký (103):", self.txt_nguoi_ky)
        form.addRow("Ủy quyền (104):", self.cmb_uy_quyen_ky)
        form.addRow("Ký thay (105):", self.cmb_ky_thay)
        form.addRow("Ngày cấp (106):", self.txt_ngay_cap)
        form.addRow("Đợt cấp (107):", self.txt_ten_dot_cap)
        form.addRow("Căn cứ PL (108):", self.txt_can_cu_phap_ly)
        form.addRow("Ghi chú T1 (109):", self.txt_ghi_chu_t1)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 2: CHỦ SỬ DỤNG (Cols 5-25)
    # -------------------------------------------------------------
    def _create_tab_chu(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        self._setup_form_layout(form)

        self.txt_chu_ma = QLineEdit()
        self._register_input(5, self.txt_chu_ma)

        self.cmb_chu_dtsd = SearchableComboBox()
        self.cmb_chu_dtsd.addItem("[Không chọn]", "")
        if self.master_data.dtsd_list:
            for code, name in self.master_data.dtsd_list:
                self.cmb_chu_dtsd.addItem(f"{code} - {name}", code)
        else:
            self.cmb_chu_dtsd.addItem("CNV - Cá nhân trong nước", "CNV")
            self.cmb_chu_dtsd.addItem("GDC - Hộ gia đình, cá nhân", "GDC")
            self.cmb_chu_dtsd.addItem("TCC - Tổ chức trong nước", "TCC")
        self._register_input(6, self.cmb_chu_dtsd)

        self.cmb_chu_hgd = SearchableComboBox()
        self.cmb_chu_hgd.addItem("[Không chọn]", "")
        self.cmb_chu_hgd.addItem("0 - Không phải HGD", "0")
        self.cmb_chu_hgd.addItem("1 - Là Hộ gia đình", "1")
        self._register_input(7, self.cmb_chu_hgd)

        self.cmb_chu_daidien = SearchableComboBox()
        self.cmb_chu_daidien.addItem("[Không chọn]", "")
        self.cmb_chu_daidien.addItem("0 - Không phải đại diện", "0")
        self.cmb_chu_daidien.addItem("1 - Là người đại diện", "1")
        self._register_input(8, self.cmb_chu_daidien)

        self.txt_chu_name = QLineEdit()
        self.txt_chu_name.setPlaceholderText("Ví dụ: Nguyễn Anh Tuấn")
        self._register_input(9, self.txt_chu_name)

        self.cmb_chu_gioitinh = SearchableComboBox()
        self.cmb_chu_gioitinh.addItem("[Trống]", "")
        self.cmb_chu_gioitinh.addItem("Nam", "1")
        self.cmb_chu_gioitinh.addItem("Nữ", "0")
        self._register_input(10, self.cmb_chu_gioitinh)

        self.txt_chu_ngay_sinh = QLineEdit()
        self.txt_chu_ngay_sinh.setPlaceholderText("Ví dụ: 15/08/1980")
        self.txt_chu_ngay_sinh.textChanged.connect(self._auto_sync_chu_nam_sinh)
        self._register_input(11, self.txt_chu_ngay_sinh)

        self.txt_chu_nam_sinh = QLineEdit()
        self.txt_chu_nam_sinh.setPlaceholderText("Ví dụ: 1980")
        self._register_input(12, self.txt_chu_nam_sinh)

        self.cmb_chu_id_type = SearchableComboBox()
        self.cmb_chu_id_type.addItem("[Không chọn]", "")
        for code, label in self.master_data.id_types:
            self.cmb_chu_id_type.addItem(label, code)
        self._register_input(13, self.cmb_chu_id_type)

        self.txt_chu_id_num = QLineEdit()
        self.txt_chu_id_num.setPlaceholderText("Số CCCD / CMND")
        self._register_input(14, self.txt_chu_id_num)

        self.txt_chu_id_date = QLineEdit()
        self._register_input(15, self.txt_chu_id_date)

        self.txt_chu_id_place = SearchableComboBox()
        self.txt_chu_id_place.addItem("[Không chọn]", "")
        for opt in DEFAULT_NOI_CAP_LIST:
            self.txt_chu_id_place.addItem(opt, opt)
        self._register_input(16, self.txt_chu_id_place)

        self.txt_chu_address = QLineEdit()
        self._register_input(17, self.txt_chu_address)

        self.txt_chu_sonha = QLineEdit()
        self._register_input(18, self.txt_chu_sonha)

        self.txt_chu_to = QLineEdit()
        self.txt_chu_to.setPlaceholderText("Ví dụ: Khu 5")
        self.txt_chu_to.textChanged.connect(self._update_chu_full_address)
        self._register_input(19, self.txt_chu_to)

        self.cmb_chu_xa = SearchableComboBox()
        self._populate_communes_for_tab(self.cmb_chu_xa)
        self.cmb_chu_xa.currentIndexChanged.connect(self._on_chu_commune_changed)
        self._register_input(20, self.cmb_chu_xa)

        self.txt_chu_xa_huyen_tinh = QLineEdit()
        self.txt_chu_xa_huyen_tinh.textChanged.connect(self._update_chu_full_address)
        self._register_input(21, self.txt_chu_xa_huyen_tinh)

        self.txt_chu_full_addr = QLineEdit()
        self._register_input(22, self.txt_chu_full_addr)

        self.txt_chu_phone = QLineEdit()
        self._register_input(23, self.txt_chu_phone)

        self.cmb_chu_dantoc = SearchableComboBox()
        self.cmb_chu_dantoc.addItem("[Không chọn]", "")
        for eth in self.master_data.ethnicities:
            self.cmb_chu_dantoc.addItem(eth, eth)
        self._register_input(24, self.cmb_chu_dantoc)

        self.cmb_chu_quoctich = SearchableComboBox()
        self.cmb_chu_quoctich.addItem("[Không chọn]", "")
        for nat in self.master_data.nationalities:
            self.cmb_chu_quoctich.addItem(nat, nat)
        self._register_input(25, self.cmb_chu_quoctich)

        form.addRow("Mã Chủ SD (5):", self.txt_chu_ma)
        form.addRow("ĐTSD (6):", self.cmb_chu_dtsd)
        form.addRow("HGD (7):", self.cmb_chu_hgd)
        form.addRow("Đại diện (8):", self.cmb_chu_daidien)
        form.addRow("Họ tên (9):", self.txt_chu_name)
        form.addRow("Giới tính (10):", self.cmb_chu_gioitinh)
        form.addRow("Ngày sinh (11):", self.txt_chu_ngay_sinh)
        form.addRow("Năm sinh (12):", self.txt_chu_nam_sinh)
        form.addRow("Loại GT (13):", self.cmb_chu_id_type)
        form.addRow("Số GT/CCCD (14):", self.txt_chu_id_num)
        form.addRow("Ngày cấp (15):", self.txt_chu_id_date)
        form.addRow("Nơi cấp (16):", self.txt_chu_id_place)
        form.addRow("Địa chỉ chi tiết (17):", self.txt_chu_address)
        form.addRow("Đường phố (18):", self.txt_chu_sonha)
        form.addRow("Tổ/Khu (19):", self.txt_chu_to)
        form.addRow("Mã Xã (20):", self.cmb_chu_xa)
        form.addRow("Xã/Huyện/Tỉnh (21):", self.txt_chu_xa_huyen_tinh)
        form.addRow("Địa chỉ đầy đủ (22):", self.txt_chu_full_addr)
        form.addRow("Số ĐT (23):", self.txt_chu_phone)
        form.addRow("Dân tộc (24):", self.cmb_chu_dantoc)
        form.addRow("Quốc tịch (25):", self.cmb_chu_quoctich)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 3: VỢ / CHỒNG (Cols 26-42)
    # -------------------------------------------------------------
    def _create_tab_vo_chong(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)

        self.chk_has_spouse = QCheckBox("☑ Có thông tin Vợ / Chồng (Cols 26-42)")
        vbox.addWidget(self.chk_has_spouse)

        grp_vo = QGroupBox()
        fv = QFormLayout(grp_vo)
        self._setup_form_layout(fv)

        self.txt_vo_name = QLineEdit()
        self._register_input(26, self.txt_vo_name)
        
        self.cmb_vo_gioitinh = SearchableComboBox()
        self.cmb_vo_gioitinh.addItem("[Trống]", "")
        self.cmb_vo_gioitinh.addItem("Nữ", "0")
        self.cmb_vo_gioitinh.addItem("Nam", "1")
        self._register_input(27, self.cmb_vo_gioitinh)
        
        self.txt_vo_ngay_sinh = QLineEdit()
        self.txt_vo_ngay_sinh.textChanged.connect(self._auto_sync_vo_nam_sinh)
        self._register_input(28, self.txt_vo_ngay_sinh)
        
        self.txt_vo_nam_sinh = QLineEdit()
        self._register_input(29, self.txt_vo_nam_sinh)
        
        self.cmb_vo_id_type = SearchableComboBox()
        self.cmb_vo_id_type.addItem("[Không chọn]", "")
        for code, label in self.master_data.id_types:
            self.cmb_vo_id_type.addItem(label, code)
        self._register_input(30, self.cmb_vo_id_type)
        
        self.txt_vo_id_num = QLineEdit()
        self._register_input(31, self.txt_vo_id_num)
        
        self.txt_vo_id_date = QLineEdit()
        self._register_input(32, self.txt_vo_id_date)
        
        self.txt_vo_id_place = SearchableComboBox()
        self.txt_vo_id_place.addItem("[Không chọn]", "")
        for opt in DEFAULT_NOI_CAP_LIST:
            self.txt_vo_id_place.addItem(opt, opt)
        self._register_input(33, self.txt_vo_id_place)
        
        self.txt_vo_address = QLineEdit()
        self._register_input(34, self.txt_vo_address)
        
        self.txt_vo_sonha = QLineEdit()
        self._register_input(35, self.txt_vo_sonha)
        
        self.txt_vo_to = QLineEdit()
        self.txt_vo_to.textChanged.connect(self._update_vo_full_address)
        self._register_input(36, self.txt_vo_to)
        
        self.cmb_vo_xa = SearchableComboBox()
        self._populate_communes_for_tab(self.cmb_vo_xa)
        self.cmb_vo_xa.currentIndexChanged.connect(self._on_vo_commune_changed)
        self._register_input(37, self.cmb_vo_xa)
        
        self.txt_vo_xa_huyen_tinh = QLineEdit()
        self.txt_vo_xa_huyen_tinh.textChanged.connect(self._update_vo_full_address)
        self._register_input(38, self.txt_vo_xa_huyen_tinh)
        
        self.txt_vo_full_addr = QLineEdit()
        self._register_input(39, self.txt_vo_full_addr)
        
        self.txt_vo_phone = QLineEdit()
        self._register_input(40, self.txt_vo_phone)
        
        self.cmb_vo_dantoc = SearchableComboBox()
        self.cmb_vo_dantoc.addItem("[Không chọn]", "")
        for eth in self.master_data.ethnicities:
            self.cmb_vo_dantoc.addItem(eth, eth)
        self._register_input(41, self.cmb_vo_dantoc)
        
        self.cmb_vo_quoctich = SearchableComboBox()
        self.cmb_vo_quoctich.addItem("[Không chọn]", "")
        for nat in self.master_data.nationalities:
            self.cmb_vo_quoctich.addItem(nat, nat)
        self._register_input(42, self.cmb_vo_quoctich)

        fv.addRow("Họ tên Vợ/Chồng (26):", self.txt_vo_name)
        fv.addRow("Giới tính (27):", self.cmb_vo_gioitinh)
        fv.addRow("Ngày sinh (28):", self.txt_vo_ngay_sinh)
        fv.addRow("Năm sinh (29):", self.txt_vo_nam_sinh)
        fv.addRow("Loại GT (30):", self.cmb_vo_id_type)
        fv.addRow("Số GT/CCCD (31):", self.txt_vo_id_num)
        fv.addRow("Ngày cấp (32):", self.txt_vo_id_date)
        fv.addRow("Nơi cấp (33):", self.txt_vo_id_place)
        fv.addRow("Địa chỉ (34):", self.txt_vo_address)
        fv.addRow("Đường phố (35):", self.txt_vo_sonha)
        fv.addRow("Tổ/Khu (36):", self.txt_vo_to)
        fv.addRow("Mã Xã (37):", self.cmb_vo_xa)
        fv.addRow("Xã/Huyện/Tỉnh (38):", self.txt_vo_xa_huyen_tinh)
        fv.addRow("Địa chỉ đầy đủ (39):", self.txt_vo_full_addr)
        fv.addRow("Số ĐT (40):", self.txt_vo_phone)
        fv.addRow("Dân tộc (41):", self.cmb_vo_dantoc)
        fv.addRow("Quốc tịch (42):", self.cmb_vo_quoctich)

        vbox.addWidget(grp_vo)
        grp_vo.setEnabled(False)
        self.chk_has_spouse.toggled.connect(grp_vo.setEnabled)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 4: THỬA ĐẤT & MĐSD (Cols 45-98)
    # -------------------------------------------------------------
    def _create_tab_thua_dat(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        self._setup_form_layout(form)

        self.txt_ty_le = QLineEdit("")
        self._register_input(45, self.txt_ty_le)
        self.txt_tyle = self.txt_ty_le  # Alias

        self.cmb_loai_bando = SearchableComboBox()
        self.cmb_loai_bando.addItem("[Không chọn]", "")
        for code, name in self.master_data.map_types:
            self.cmb_loai_bando.addItem(name, code)
        self._register_input(46, self.cmb_loai_bando)

        self.cmb_don_vi_do = SearchableComboBox()
        self.cmb_don_vi_do.addItem("[Không chọn]", "")
        for u in ["Xí nghiệp tài nguyên và môi trường 3", "Trung tâm kỹ thuật CNTT", "Công ty CP Đo đạc Bản đồ"]:
            self.cmb_don_vi_do.addItem(u, u)
        self._register_input(47, self.cmb_don_vi_do)
        self.txt_don_vi_do = self.cmb_don_vi_do  # Alias

        self.txt_pp_do = QLineEdit("")
        self._register_input(48, self.txt_pp_do)
        self.txt_phuong_phap_do = self.txt_pp_do  # Alias

        self.txt_do_chinh_xac = QLineEdit("")
        self._register_input(49, self.txt_do_chinh_xac)
        self.txt_nguoi_kiem_tra = self.txt_do_chinh_xac  # Alias

        self.txt_ngay_hoan_thanh = QLineEdit("")
        self._register_input(50, self.txt_ngay_hoan_thanh)
        
        self.cmb_trang_thai = SearchableComboBox()
        self.cmb_trang_thai.addItem("[Không chọn]", "")
        if self.master_data.land_status_list:
            for code, name in self.master_data.land_status_list:
                self.cmb_trang_thai.addItem(f"{code} - {name}", code)
        else:
            self.cmb_trang_thai.addItem("A - Đã cấp GCN, không có tài sản", "A")
            self.cmb_trang_thai.addItem("B - Đã cấp GCN, có tài sản", "B")
        self._register_input(51, self.cmb_trang_thai)
        self.cmb_phan_loai_thua = self.cmb_trang_thai  # Alias

        self.txt_dt_bando = QLineEdit("")
        self._register_input(52, self.txt_dt_bando)
        self.txt_dt_phaply = QLineEdit("")
        self.txt_dt_phaply.textChanged.connect(self._auto_sync_dt_phaply)
        self._register_input(53, self.txt_dt_phaply)

        # MĐSD 1 (54-61)
        self.cmb_mdsd1_loai = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd1_loai)
        self._register_input(54, self.cmb_mdsd1_loai)
        
        self.txt_mdsd1_dt = QLineEdit("")
        self._register_input(56, self.txt_mdsd1_dt)
        
        self.cmb_mdsd1_ht = SearchableComboBox()
        self.cmb_mdsd1_ht.addItem("[Không chọn]", "")
        self.cmb_mdsd1_ht.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd1_ht.addItem("1 - Sử dụng chung", "1")
        self._register_input(57, self.cmb_mdsd1_ht)
        
        self.txt_mdsd1_thoihan = QLineEdit("")
        self._register_input(58, self.txt_mdsd1_thoihan)
        self.txt_mdsd1_thoi_han = self.txt_mdsd1_thoihan  # Alias
        
        self.cmb_mdsd1_nguongoc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd1_nguongoc)
        self.cmb_mdsd1_nguongoc.currentIndexChanged.connect(self._on_mdsd1_nguongoc_changed)
        self._register_input(59, self.cmb_mdsd1_nguongoc)
        self.cmb_mdsd1_nguon_goc = self.cmb_mdsd1_nguongoc  # Alias

        self.cmb_mdsd1_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd1_ma_nguon_goc)
        self.cmb_mdsd1_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd1_nguongoc_changed)
        self._register_input(60, self.cmb_mdsd1_ma_nguon_goc)

        self.txt_mdsd1_nguongoc_chitiet = QLineEdit("")
        self._register_input(61, self.txt_mdsd1_nguongoc_chitiet)
        self.txt_mdsd1_nguon_goc_chi_tiet = self.txt_mdsd1_nguongoc_chitiet  # Alias
        self.txt_mdsd1_nguon_goc_ct = self.txt_mdsd1_nguongoc_chitiet  # Alias

        # MĐSD 2 (62-69)
        self.chk_has_mdsd2 = QCheckBox("☑ Có MĐSD 2 (62-69)")
        self.cmb_mdsd2_loai = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd2_loai)
        self._register_input(62, self.cmb_mdsd2_loai)
        
        self.txt_mdsd2_dt = QLineEdit("")
        self._register_input(64, self.txt_mdsd2_dt)
        
        self.cmb_mdsd2_ht = SearchableComboBox()
        self.cmb_mdsd2_ht.addItem("[Không chọn]", "")
        self.cmb_mdsd2_ht.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd2_ht.addItem("1 - Sử dụng chung", "1")
        self._register_input(65, self.cmb_mdsd2_ht)
        
        self.txt_mdsd2_thoihan = QLineEdit("")
        self._register_input(66, self.txt_mdsd2_thoihan)
        
        self.cmb_mdsd2_nguongoc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd2_nguongoc)
        self.cmb_mdsd2_nguongoc.currentIndexChanged.connect(self._on_mdsd2_nguongoc_changed)
        self._register_input(67, self.cmb_mdsd2_nguongoc)
        self.cmb_mdsd2_nguon_goc = self.cmb_mdsd2_nguongoc  # Alias

        self.cmb_mdsd2_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd2_ma_nguon_goc)
        self.cmb_mdsd2_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd2_nguongoc_changed)
        self._register_input(68, self.cmb_mdsd2_ma_nguon_goc)

        self.txt_mdsd2_nguongoc_chitiet = QLineEdit("")
        self._register_input(69, self.txt_mdsd2_nguongoc_chitiet)
        self.txt_mdsd2_nguon_goc_chi_tiet = self.txt_mdsd2_nguongoc_chitiet  # Alias

        # MĐSD 3 (70-77)
        self.chk_has_mdsd3 = QCheckBox("☑ Có MĐSD 3 (70-77)")
        self.cmb_mdsd3_loai = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd3_loai)
        self._register_input(70, self.cmb_mdsd3_loai)
        
        self.txt_mdsd3_dt = QLineEdit("")
        self._register_input(72, self.txt_mdsd3_dt)
        
        self.cmb_mdsd3_ht = SearchableComboBox()
        self.cmb_mdsd3_ht.addItem("[Không chọn]", "")
        self.cmb_mdsd3_ht.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd3_ht.addItem("1 - Sử dụng chung", "1")
        self._register_input(73, self.cmb_mdsd3_ht)
        
        self.txt_mdsd3_thoihan = QLineEdit("")
        self._register_input(74, self.txt_mdsd3_thoihan)
        
        self.cmb_mdsd3_nguongoc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd3_nguongoc)
        self.cmb_mdsd3_nguongoc.currentIndexChanged.connect(self._on_mdsd3_nguongoc_changed)
        self._register_input(75, self.cmb_mdsd3_nguongoc)
        self.cmb_mdsd3_nguon_goc = self.cmb_mdsd3_nguongoc  # Alias

        self.cmb_mdsd3_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd3_ma_nguon_goc)
        self.cmb_mdsd3_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd3_nguongoc_changed)
        self._register_input(76, self.cmb_mdsd3_ma_nguon_goc)

        self.txt_mdsd3_nguongoc_chitiet = QLineEdit("")
        self._register_input(77, self.txt_mdsd3_nguongoc_chitiet)
        self.txt_mdsd3_nguon_goc_chi_tiet = self.txt_mdsd3_nguongoc_chitiet  # Alias

        # Thửa đất địa chỉ (89-98)
        self.txt_thua_sonha = QLineEdit("")
        self._register_input(89, self.txt_thua_sonha)
        self.txt_thua_to_dp = QLineEdit("")
        self._register_input(90, self.txt_thua_to_dp)
        self.txt_thua_full_addr = QLineEdit("")
        self._register_input(94, self.txt_thua_full_addr)

        self.txt_thua_ma_don = QLineEdit("")
        self._register_input(95, self.txt_thua_ma_don)

        self.chk_has_quan_ly = QCheckBox("☑ Có Người quản lý thửa đất (96-98)")
        self.cmb_ql_dtsd = SearchableComboBox()
        self.cmb_ql_dtsd.addItem("[Không chọn]", "")
        self.cmb_ql_dtsd.addItem("0 - Không", "0")
        self.cmb_ql_dtsd.addItem("1 - Có", "1")
        self._register_input(96, self.cmb_ql_dtsd)

        self.cmb_hinh_thuc_sd = SearchableComboBox()
        self.cmb_hinh_thuc_sd.addItem("[Không chọn]", "")
        self.cmb_hinh_thuc_sd.addItem("0 - Sử dụng riêng", "0")
        self.cmb_hinh_thuc_sd.addItem("1 - Sử dụng chung", "1")
        self._register_input(97, self.cmb_hinh_thuc_sd)
        self.txt_ql_name = self.cmb_hinh_thuc_sd  # Alias

        self.cmb_trang_thai_thua = SearchableComboBox()
        self.cmb_trang_thai_thua.addItem("[Không chọn]", "")
        self.cmb_trang_thai_thua.addItem("1 - Đã đăng ký, chưa cấp GCN", "1")
        self.cmb_trang_thai_thua.addItem("2 - Chưa đăng ký, đủ ĐK cấp GCN", "2")
        self.cmb_trang_thai_thua.addItem("3 - Đã đăng ký, không đủ ĐK cấp GCN", "3")
        self.cmb_trang_thai_thua.addItem("4 - Đã đăng ký, đủ điều kiện cấp GCN", "4")
        self._register_input(98, self.cmb_trang_thai_thua)
        self.txt_ql_diachi = self.cmb_trang_thai_thua  # Alias

        form.addRow("Tỷ lệ (45):", self.txt_ty_le)
        form.addRow("Loại bản đồ (46):", self.cmb_loai_bando)
        form.addRow("Đơn vị đo (47):", self.cmb_don_vi_do)
        form.addRow("Phương pháp đo (48):", self.txt_pp_do)
        form.addRow("Độ chính xác (49):", self.txt_do_chinh_xac)
        form.addRow("Ngày HT đo (50):", self.txt_ngay_hoan_thanh)
        form.addRow("Trạng thái cấp (51):", self.cmb_trang_thai)
        form.addRow("DT bản đồ (52):", self.txt_dt_bando)
        form.addRow("DT pháp lý (53):", self.txt_dt_phaply)
        form.addRow("--- MĐSD 1 ---", QLabel(""))
        form.addRow("Loại đất 1 (54):", self.cmb_mdsd1_loai)
        form.addRow("Diện tích 1 (56):", self.txt_mdsd1_dt)
        form.addRow("Hình thức 1 (57):", self.cmb_mdsd1_ht)
        form.addRow("Thời hạn 1 (58):", self.txt_mdsd1_thoihan)
        form.addRow("Mã nguồn gốc 1 (59):", self.cmb_mdsd1_nguongoc)
        form.addRow("Mã nguồn gốc khác (60):", self.cmb_mdsd1_ma_nguon_goc)
        form.addRow("Nguồn gốc chi tiết 1 (61):", self.txt_mdsd1_nguongoc_chitiet)
        form.addRow(self.chk_has_mdsd2)
        form.addRow("Loại đất 2 (62):", self.cmb_mdsd2_loai)
        form.addRow("Diện tích 2 (64):", self.txt_mdsd2_dt)
        form.addRow("Hình thức 2 (65):", self.cmb_mdsd2_ht)
        form.addRow("Thời hạn 2 (66):", self.txt_mdsd2_thoihan)
        form.addRow("Mã nguồn gốc 2 (67):", self.cmb_mdsd2_nguongoc)
        form.addRow("Mã nguồn gốc khác 2 (68):", self.cmb_mdsd2_ma_nguon_goc)
        form.addRow("Nguồn gốc chi tiết 2 (69):", self.txt_mdsd2_nguongoc_chitiet)
        form.addRow(self.chk_has_mdsd3)
        form.addRow("Loại đất 3 (70):", self.cmb_mdsd3_loai)
        form.addRow("Diện tích 3 (72):", self.txt_mdsd3_dt)
        form.addRow("Hình thức 3 (73):", self.cmb_mdsd3_ht)
        form.addRow("Thời hạn 3 (74):", self.txt_mdsd3_thoihan)
        form.addRow("Mã nguồn gốc 3 (75):", self.cmb_mdsd3_nguongoc)
        form.addRow("Mã nguồn gốc khác 3 (76):", self.cmb_mdsd3_ma_nguon_goc)
        form.addRow("Nguồn gốc chi tiết 3 (77):", self.txt_mdsd3_nguongoc_chitiet)
        form.addRow("Đường phố (89):", self.txt_thua_sonha)
        form.addRow("Tổ/Khu thửa (90):", self.txt_thua_to_dp)
        form.addRow("Địa chỉ đầy đủ thửa (94):", self.txt_thua_full_addr)
        form.addRow("Mã đơn (95):", self.txt_thua_ma_don)
        form.addRow(self.chk_has_quan_ly)
        form.addRow("ĐTSD QL (96):", self.cmb_ql_dtsd)
        form.addRow("Hình thức SD (97):", self.cmb_hinh_thuc_sd)
        form.addRow("Trạng thái ĐK (98):", self.cmb_trang_thai_thua)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 5: NVTC & HẠN CHẾ (Cols 111-133)
    # -------------------------------------------------------------
    def _create_tab_nvtc(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)

        # 1. Hạn chế quyền (111-117)
        self.chk_has_han_che = QCheckBox("☑ Có Hạn chế quyền (Cols 111-117)")
        vbox.addWidget(self.chk_has_han_che)
        grp_hc = QGroupBox("Hạn chế quyền")
        fhc = QFormLayout(grp_hc)
        self._setup_form_layout(fhc)

        self.cmb_hc_loai = SearchableComboBox()
        self.cmb_hc_loai.addItem("[Không chọn]", "")
        for r_code in self.master_data.restriction_types:
            self.cmb_hc_loai.addItem(r_code, r_code)
        self._register_input(111, self.cmb_hc_loai)

        self.txt_hc_dt = QLineEdit("")
        self._register_input(112, self.txt_hc_dt)
        self.txt_hc_noidung = QLineEdit("")
        self._register_input(113, self.txt_hc_noidung)
        self.txt_hc_sovb = QLineEdit("")
        self._register_input(114, self.txt_hc_sovb)
        self.txt_hc_ngaybh = QLineEdit("")
        self._register_input(115, self.txt_hc_ngaybh)
        self.txt_hc_cqbh = QLineEdit("")
        self._register_input(116, self.txt_hc_cqbh)
        self.chk_hc_1phan = QCheckBox("1 - Hạn chế 1 phần")
        self._register_input(117, self.chk_hc_1phan)

        fhc.addRow("Loại hạn chế (111):", self.cmb_hc_loai)
        fhc.addRow("Diện tích (112):", self.txt_hc_dt)
        fhc.addRow("Nội dung (113):", self.txt_hc_noidung)
        fhc.addRow("Số văn bản (114):", self.txt_hc_sovb)
        fhc.addRow("Ngày ban hành (115):", self.txt_hc_ngaybh)
        fhc.addRow("Cơ quan BH (116):", self.txt_hc_cqbh)
        fhc.addRow("Hạn chế 1 phần (117):", self.chk_hc_1phan)
        vbox.addWidget(grp_hc)
        grp_hc.setEnabled(False)
        self.chk_has_han_che.toggled.connect(grp_hc.setEnabled)

        # 2. NVTC (118-123)
        self.chk_has_nvtc = QCheckBox("☑ Có Nghĩa vụ tài chính (Cols 118-123)")
        vbox.addWidget(self.chk_has_nvtc)
        grp_nvtc = QGroupBox("Nghĩa vụ tài chính")
        f1 = QFormLayout(grp_nvtc)
        self._setup_form_layout(f1)

        self.cmb_nvtc_loai = SearchableComboBox()
        self.cmb_nvtc_loai.addItem("[Không chọn]", "")
        for n_code in self.master_data.nvtc_types:
            self.cmb_nvtc_loai.addItem(n_code, n_code)
        self._register_input(118, self.cmb_nvtc_loai)

        self.txt_nvtc_tongtien = QLineEdit("")
        self._register_input(119, self.txt_nvtc_tongtien)
        self.txt_nvtc_miengiam = QLineEdit("")
        self._register_input(120, self.txt_nvtc_miengiam)
        self.txt_nvtc_tienno = QLineEdit("")
        self._register_input(121, self.txt_nvtc_tienno)
        self.txt_nvtc_ngaybd = QLineEdit("")
        self._register_input(122, self.txt_nvtc_ngaybd)
        self.txt_nvtc_ngayht = QLineEdit("")
        self._register_input(123, self.txt_nvtc_ngayht)

        f1.addRow("Loại NVTC (118):", self.cmb_nvtc_loai)
        f1.addRow("Tổng số tiền (119):", self.txt_nvtc_tongtien)
        f1.addRow("Tổng miễn giảm (120):", self.txt_nvtc_miengiam)
        f1.addRow("Tổng tiền nợ (121):", self.txt_nvtc_tienno)
        f1.addRow("Ngày bắt đầu (122):", self.txt_nvtc_ngaybd)
        f1.addRow("Ngày hoàn thành (123):", self.txt_nvtc_ngayht)
        vbox.addWidget(grp_nvtc)
        grp_nvtc.setEnabled(False)
        self.chk_has_nvtc.toggled.connect(grp_nvtc.setEnabled)

        # 3. Miễn giảm (124-128)
        self.chk_has_mg = QCheckBox("☑ Miễn giảm NVTC (Cols 124-128)")
        vbox.addWidget(self.chk_has_mg)
        grp_mg = QGroupBox("Miễn giảm nghĩa vụ tài chính")
        f2 = QFormLayout(grp_mg)
        self._setup_form_layout(f2)

        self.txt_mg_loai = QLineEdit("")
        self._register_input(124, self.txt_mg_loai)
        self.txt_mg_sotien = QLineEdit("")
        self._register_input(125, self.txt_mg_sotien)
        self.txt_mg_sovb = QLineEdit("")
        self._register_input(126, self.txt_mg_sovb)
        self.txt_mg_ngaybh = QLineEdit("")
        self._register_input(127, self.txt_mg_ngaybh)
        self.txt_mg_cqbh = QLineEdit("")
        self._register_input(128, self.txt_mg_cqbh)

        f2.addRow("Loại chế độ (124):", self.txt_mg_loai)
        f2.addRow("Số tiền (125):", self.txt_mg_sotien)
        f2.addRow("Số văn bản (126):", self.txt_mg_sovb)
        f2.addRow("Ngày ban hành (127):", self.txt_mg_ngaybh)
        f2.addRow("Cơ quan BH (128):", self.txt_mg_cqbh)
        vbox.addWidget(grp_mg)
        grp_mg.setEnabled(False)
        self.chk_has_mg.toggled.connect(grp_mg.setEnabled)

        # 4. Nợ NVTC (129-133)
        self.chk_has_no = QCheckBox("☑ Nợ nghĩa vụ tài chính (Cols 129-133)")
        vbox.addWidget(self.chk_has_no)
        grp_no = QGroupBox("Nợ nghĩa vụ tài chính")
        f3 = QFormLayout(grp_no)
        self._setup_form_layout(f3)

        self.txt_no_loai = QLineEdit("")
        self._register_input(129, self.txt_no_loai)
        self.txt_no_sotien = QLineEdit("")
        self._register_input(130, self.txt_no_sotien)
        self.txt_no_soqd = QLineEdit("")
        self._register_input(131, self.txt_no_soqd)
        self.txt_no_ngaybh = QLineEdit("")
        self._register_input(132, self.txt_no_ngaybh)
        self.txt_no_cqbh = QLineEdit("")
        self._register_input(133, self.txt_no_cqbh)

        f3.addRow("Loại chế độ (129):", self.txt_no_loai)
        f3.addRow("Số tiền (130):", self.txt_no_sotien)
        f3.addRow("Số quyết định (131):", self.txt_no_soqd)
        f3.addRow("Ngày ban hành (132):", self.txt_no_ngaybh)
        f3.addRow("Cơ quan BH (133):", self.txt_no_cqbh)
        vbox.addWidget(grp_no)
        grp_no.setEnabled(False)
        self.chk_has_no.toggled.connect(grp_no.setEnabled)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 6: TÀI SẢN & LƯU KHO (Cols 134-186)
    # -------------------------------------------------------------
    def _create_tab_tai_san_va_khac(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)

        # 1. Nhà ở riêng lẻ (134-141)
        self.chk_has_nha = QCheckBox("☑ Nhà ở riêng lẻ (Cols 134-141)")
        vbox.addWidget(self.chk_has_nha)
        grp_nha = QGroupBox("Nhà ở riêng lẻ")
        fnha = QFormLayout(grp_nha)
        self._setup_form_layout(fnha)

        self.txt_nha_dt_xd = QLineEdit("")
        self._register_input(134, self.txt_nha_dt_xd)
        self.txt_nha_dt_san = QLineEdit("")
        self._register_input(135, self.txt_nha_dt_san)
        self.txt_nha_so_tang = QLineEdit("")
        self._register_input(136, self.txt_nha_so_tang)
        self.txt_nha_tang_ham = QLineEdit("")
        self._register_input(137, self.txt_nha_tang_ham)
        self.txt_nha_ket_cau = QLineEdit("")
        self._register_input(138, self.txt_nha_ket_cau)
        self.cmb_nha_cap_hang = SearchableComboBox()
        self.cmb_nha_cap_hang.addItem("[Không chọn]", "")
        for rk in self.master_data.rank_types:
            self.cmb_nha_cap_hang.addItem(rk, rk)
        self._register_input(139, self.cmb_nha_cap_hang)
        self.txt_nha_dia_chi = QLineEdit("")
        self._register_input(140, self.txt_nha_dia_chi)
        self.txt_nha_thoi_han = QLineEdit("")
        self._register_input(141, self.txt_nha_thoi_han)

        fnha.addRow("DT xây dựng (134):", self.txt_nha_dt_xd)
        fnha.addRow("DT sàn (135):", self.txt_nha_dt_san)
        fnha.addRow("Số tầng (136):", self.txt_nha_so_tang)
        fnha.addRow("Số tầng hầm (137):", self.txt_nha_tang_ham)
        fnha.addRow("Kết cấu (138):", self.txt_nha_ket_cau)
        fnha.addRow("Cấp hạng (139):", self.cmb_nha_cap_hang)
        fnha.addRow("Địa chỉ (140):", self.txt_nha_dia_chi)
        fnha.addRow("Thời hạn SH (141):", self.txt_nha_thoi_han)
        vbox.addWidget(grp_nha)
        grp_nha.setEnabled(False)
        self.chk_has_nha.toggled.connect(grp_nha.setEnabled)

        # 2. Công trình XD (142-154)
        self.chk_has_ctxd = QCheckBox("☑ Công trình, hạng mục công trình XD (Cols 142-154)")
        vbox.addWidget(self.chk_has_ctxd)
        grp_ctxd = QGroupBox("Công trình xây dựng")
        fct = QFormLayout(grp_ctxd)
        self._setup_form_layout(fct)

        self.txt_ctxd_ten = QLineEdit("")
        self._register_input(142, self.txt_ctxd_ten)
        self.txt_ctxd_diachi = QLineEdit("")
        self._register_input(143, self.txt_ctxd_diachi)
        self.txt_ctxd_hangmuc = QLineEdit("")
        self._register_input(144, self.txt_ctxd_hangmuc)
        self.txt_ctxd_congnang = QLineEdit("")
        self._register_input(145, self.txt_ctxd_congnang)
        self.txt_ctxd_dtxd = QLineEdit("")
        self._register_input(146, self.txt_ctxd_dtxd)
        self.txt_ctxd_dts = QLineEdit("")
        self._register_input(147, self.txt_ctxd_dts)
        self.txt_ctxd_sotang = QLineEdit("")
        self._register_input(148, self.txt_ctxd_sotang)
        self.txt_ctxd_tangham = QLineEdit("")
        self._register_input(149, self.txt_ctxd_tangham)
        self.txt_ctxd_ketcau = QLineEdit("")
        self._register_input(150, self.txt_ctxd_ketcau)
        self.txt_ctxd_namxd = QLineEdit("")
        self._register_input(151, self.txt_ctxd_namxd)
        self.txt_ctxd_namht = QLineEdit("")
        self._register_input(152, self.txt_ctxd_namht)
        self.txt_ctxd_thoihan = QLineEdit("")
        self._register_input(153, self.txt_ctxd_thoihan)
        self.cmb_ctxd_caphang = SearchableComboBox()
        self.cmb_ctxd_caphang.addItem("[Không chọn]", "")
        for rk in self.master_data.rank_types:
            self.cmb_ctxd_caphang.addItem(rk, rk)
        self._register_input(154, self.cmb_ctxd_caphang)

        fct.addRow("Tên công trình (142):", self.txt_ctxd_ten)
        fct.addRow("Địa chỉ (143):", self.txt_ctxd_diachi)
        fct.addRow("Tên hạng mục (144):", self.txt_ctxd_hangmuc)
        fct.addRow("Công năng (145):", self.txt_ctxd_congnang)
        fct.addRow("DT xây dựng (146):", self.txt_ctxd_dtxd)
        fct.addRow("DT sàn (147):", self.txt_ctxd_dts)
        fct.addRow("Số tầng (148):", self.txt_ctxd_sotang)
        fct.addRow("Số tầng hầm (149):", self.txt_ctxd_tangham)
        fct.addRow("Kết cấu (150):", self.txt_ctxd_ketcau)
        fct.addRow("Năm XD (151):", self.txt_ctxd_namxd)
        fct.addRow("Năm HT (152):", self.txt_ctxd_namht)
        fct.addRow("Thời hạn SH (153):", self.txt_ctxd_thoihan)
        fct.addRow("Cấp hạng (154):", self.cmb_ctxd_caphang)
        vbox.addWidget(grp_ctxd)
        grp_ctxd.setEnabled(False)
        self.chk_has_ctxd.toggled.connect(grp_ctxd.setEnabled)

        # 3. Công trình ngầm (155-162)
        self.chk_has_ctngam = QCheckBox("☑ Công trình ngầm (Cols 155-162)")
        vbox.addWidget(self.chk_has_ctngam)
        grp_ngam = QGroupBox("Công trình ngầm")
        fngam = QFormLayout(grp_ngam)
        self._setup_form_layout(fngam)

        self.txt_ctn_ten = QLineEdit("")
        self._register_input(155, self.txt_ctn_ten)
        self.txt_ctn_loai = QLineEdit("")
        self._register_input(156, self.txt_ctn_loai)
        self.txt_ctn_dt = QLineEdit("")
        self._register_input(157, self.txt_ctn_dt)
        self.txt_ctn_dosau = QLineEdit("")
        self._register_input(158, self.txt_ctn_dosau)
        self.txt_ctn_vitri = QLineEdit("")
        self._register_input(159, self.txt_ctn_vitri)
        self.txt_ctn_namxd = QLineEdit("")
        self._register_input(160, self.txt_ctn_namxd)
        self.txt_ctn_namht = QLineEdit("")
        self._register_input(161, self.txt_ctn_namht)
        self.txt_ctn_thoihan = QLineEdit("")
        self._register_input(162, self.txt_ctn_thoihan)

        fngam.addRow("Tên công trình (155):", self.txt_ctn_ten)
        fngam.addRow("Loại CT (156):", self.txt_ctn_loai)
        fngam.addRow("Diện tích (157):", self.txt_ctn_dt)
        fngam.addRow("Độ sâu tối đa (158):", self.txt_ctn_dosau)
        fngam.addRow("Vị trí đầu nối (159):", self.txt_ctn_vitri)
        fngam.addRow("Năm XD (160):", self.txt_ctn_namxd)
        fngam.addRow("Năm HT (161):", self.txt_ctn_namht)
        fngam.addRow("Thời hạn SH (162):", self.txt_ctn_thoihan)
        vbox.addWidget(grp_ngam)
        grp_ngam.setEnabled(False)
        self.chk_has_ctngam.toggled.connect(grp_ngam.setEnabled)

        # 4. Rừng trồng & Cây lâu năm (163-168)
        self.chk_has_cay = QCheckBox("☑ Rừng trồng & Cây lâu năm (Cols 163-168)")
        vbox.addWidget(self.chk_has_cay)
        grp_cay = QGroupBox("Rừng trồng & Cây lâu năm")
        fcay = QFormLayout(grp_cay)
        self._setup_form_layout(fcay)

        self.txt_rt_ten = QLineEdit("")
        self._register_input(163, self.txt_rt_ten)
        self.txt_rt_loai = QLineEdit("")
        self._register_input(164, self.txt_rt_loai)
        self.txt_rt_dt = QLineEdit("")
        self._register_input(165, self.txt_rt_dt)
        self.txt_cln_ten = QLineEdit("")
        self._register_input(166, self.txt_cln_ten)
        self.txt_cln_loai = QLineEdit("")
        self._register_input(167, self.txt_cln_loai)
        self.txt_cln_dt = QLineEdit("")
        self._register_input(168, self.txt_cln_dt)

        fcay.addRow("Tên rừng (163):", self.txt_rt_ten)
        fcay.addRow("Loại cây rừng (164):", self.txt_rt_loai)
        fcay.addRow("Diện tích rừng (165):", self.txt_rt_dt)
        fcay.addRow("Tên cây lâu năm (166):", self.txt_cln_ten)
        fcay.addRow("Loại cây trồng (167):", self.txt_cln_loai)
        fcay.addRow("Diện tích cây (168):", self.txt_cln_dt)
        vbox.addWidget(grp_cay)
        grp_cay.setEnabled(False)
        self.chk_has_cay.toggled.connect(grp_cay.setEnabled)

        # 5. Thửa đất cũ (169-178)
        self.chk_has_thua_cu = QCheckBox("☑ Thửa đất cũ (Cols 169-178)")
        vbox.addWidget(self.chk_has_thua_cu)
        grp_tc = QGroupBox("Thông tin thửa đất cũ")
        ftc = QFormLayout(grp_tc)
        self._setup_form_layout(ftc)

        self.txt_tc_to = QLineEdit("")
        self._register_input(169, self.txt_tc_to)
        self.txt_tc_thua = QLineEdit("")
        self._register_input(170, self.txt_tc_thua)
        self.txt_tc_dt = QLineEdit("")
        self._register_input(171, self.txt_tc_dt)
        self.cmb_tc_loaidat = SearchableComboBox()
        self._populate_land_types(self.cmb_tc_loaidat)
        self._register_input(172, self.cmb_tc_loaidat)
        self.txt_tc_thoihan = QLineEdit("")
        self._register_input(173, self.txt_tc_thoihan)
        self.cmb_tc_nguongoc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_tc_nguongoc)
        self._register_input(174, self.cmb_tc_nguongoc)
        self.txt_tc_serial = QLineEdit("")
        self._register_input(175, self.txt_tc_serial)
        self.txt_tc_sovaoso = QLineEdit("")
        self._register_input(176, self.txt_tc_sovaoso)
        self.txt_tc_ngaycap = QLineEdit("")
        self._register_input(177, self.txt_tc_ngaycap)
        self.cmb_tc_hinhthuc = SearchableComboBox()
        self.cmb_tc_hinhthuc.addItem("[Không chọn]", "")
        self.cmb_tc_hinhthuc.addItem("0 - Sử dụng riêng", "0")
        self.cmb_tc_hinhthuc.addItem("1 - Sử dụng chung", "1")
        self._register_input(178, self.cmb_tc_hinhthuc)

        ftc.addRow("Tờ bản đồ (169):", self.txt_tc_to)
        ftc.addRow("Số thửa (170):", self.txt_tc_thua)
        ftc.addRow("Diện tích (171):", self.txt_tc_dt)
        ftc.addRow("Loại đất GCN (172):", self.cmb_tc_loaidat)
        ftc.addRow("Thời hạn (173):", self.txt_tc_thoihan)
        ftc.addRow("Nguồn gốc (174):", self.cmb_tc_nguongoc)
        ftc.addRow("Số Serial (175):", self.txt_tc_serial)
        ftc.addRow("Số vào sổ (176):", self.txt_tc_sovaoso)
        ftc.addRow("Ngày cấp (177):", self.txt_tc_ngaycap)
        ftc.addRow("Hình thức SD (178):", self.cmb_tc_hinhthuc)
        vbox.addWidget(grp_tc)
        grp_tc.setEnabled(False)
        self.chk_has_thua_cu.toggled.connect(grp_tc.setEnabled)

        # 6. Lưu kho & Giao nộp (179-186)
        grp_lk = QGroupBox("Lưu kho & Giao nộp (Cols 179-186)")
        flk = QFormLayout(grp_lk)
        self._setup_form_layout(flk)

        self.txt_lk_kho = QLineEdit("")
        self._register_input(179, self.txt_lk_kho)
        self.txt_lk_gia = QLineEdit("")
        self._register_input(180, self.txt_lk_gia)
        self.txt_lk_ke = QLineEdit("")
        self._register_input(181, self.txt_lk_ke)
        self.txt_lk_ngan = QLineEdit("")
        self._register_input(182, self.txt_lk_ngan)
        self.txt_hsq_folder = QLineEdit("")
        self._register_input(183, self.txt_hsq_folder)
        self.txt_thu_muc_hsq = self.txt_hsq_folder  # Alias
        self.txt_gn_dot = QLineEdit("")
        self._register_input(184, self.txt_gn_dot)
        self.cmb_kt_trangthai = SearchableComboBox()
        self.cmb_kt_trangthai.addItem("[Không chọn]", "")
        self.cmb_kt_trangthai.addItem("0 - Chưa kiểm tra", "0")
        self.cmb_kt_trangthai.addItem("1 - Đã kiểm tra", "1")
        self._register_input(185, self.cmb_kt_trangthai)
        self.txt_gn_ghichu = QLineEdit("")
        self._register_input(186, self.txt_gn_ghichu)

        flk.addRow("Kho (179):", self.txt_lk_kho)
        flk.addRow("Giá (180):", self.txt_lk_gia)
        flk.addRow("Kệ (181):", self.txt_lk_ke)
        flk.addRow("Ngăn (182):", self.txt_lk_ngan)
        flk.addRow("Thư mục lưu HSQ (183):", self.txt_hsq_folder)
        flk.addRow("Đợt giao nộp (184):", self.txt_gn_dot)
        flk.addRow("Trạng thái KT (185):", self.cmb_kt_trangthai)
        flk.addRow("Nội dung ghi chú (186):", self.txt_gn_ghichu)
        vbox.addWidget(grp_lk)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # AUTO-SYNC AND HELPER LOGIC
    # -------------------------------------------------------------
    def _populate_communes(self, combo: QComboBox):
        """Populates commune selector for Col 93 (saving full location text)."""
        combo.clear()
        combo.addItem("[Không chọn]", "")
        for c in self.master_data.communes:
            disp_text = f"{c.name_3cap}, {c.district}, Tỉnh Quảng Ninh ({c.code_3cap})"
            combo.addItem(disp_text, c.full_location)

    def _populate_communes_for_tab(self, combo: QComboBox):
        """Populates commune selector for tabbed fields (Cols 20, 37)."""
        combo.clear()
        combo.addItem("[Không chọn]", "")
        for c in self.master_data.communes:
            disp_text = f"{c.code_3cap} - {c.name_3cap}, {c.district}"
            combo.addItem(disp_text, c)

    def _populate_land_types(self, combo: QComboBox):
        combo.clear()
        combo.addItem("[Không chọn]", "")
        for lt in self.master_data.land_types:
            disp_text = f"{lt.code} - {lt.name}"
            combo.addItem(disp_text, lt.code)

    def _populate_land_use_origins(self, combo: QComboBox):
        combo.clear()
        combo.addItem("[Không chọn]", "")
        for code, name in self.master_data.land_use_origins:
            disp_text = f"{code} - {name}"
            combo.addItem(disp_text, code)

    def _auto_sync_ma_hs_goc(self, text: str):
        clean = text.strip()
        if len(clean) >= 6:
            self.txt_ma_hs.setText(clean[-6:])
        elif clean:
            self.txt_ma_hs.setText(clean)

    def _auto_sync_ma_don(self, text: str):
        clean = text.replace(" ", "").strip()
        if hasattr(self, 'txt_thua_ma_don'):
            self.txt_thua_ma_don.setText(clean)

    def _auto_sync_ngay_vao_so(self, text: str):
        clean = text.strip()
        if clean:
            self.txt_ngay_ky.setText(clean)
            self.txt_ngay_cap.setText(clean)

    def _auto_sync_ngay_cap(self, text: str):
        clean = text.strip()
        if clean and not self.txt_ngay_cap.text():
            self.txt_ngay_cap.setText(clean)

    def _auto_sync_chu_nam_sinh(self, text: str):
        clean = text.strip()
        if len(clean) >= 4:
            year_part = clean[-4:]
            if year_part.isdigit() and (not self.txt_chu_nam_sinh.text() or len(self.txt_chu_nam_sinh.text()) != 4):
                self.txt_chu_nam_sinh.setText(year_part)

    def _auto_sync_vo_nam_sinh(self, text: str):
        clean = text.strip()
        if len(clean) >= 4:
            year_part = clean[-4:]
            if year_part.isdigit() and (not self.txt_vo_nam_sinh.text() or len(self.txt_vo_nam_sinh.text()) != 4):
                self.txt_vo_nam_sinh.setText(year_part)

    def _auto_sync_dt_phaply(self, text: str):
        clean = text.strip()
        if clean:
            if not self.txt_mdsd1_dt.text() or self.txt_mdsd1_dt.text() == clean:
                self.txt_mdsd1_dt.setText(clean)

    def _on_chu_commune_changed(self, idx: int):
        data = self.cmb_chu_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.last_commune_code = data.code_3cap
            self.txt_chu_xa_huyen_tinh.setText(data.full_location)
            self._update_chu_full_address()
            if self.chk_has_spouse.isChecked() and not self.txt_vo_xa_huyen_tinh.text():
                self.cmb_vo_xa.setCurrentIndex(idx)

    def _on_vo_commune_changed(self, idx: int):
        data = self.cmb_vo_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.txt_vo_xa_huyen_tinh.setText(data.full_location)
            self._update_vo_full_address()

    def _update_chu_full_address(self):
        to = self.txt_chu_to.text().strip()
        location = self.txt_chu_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_chu_full_addr.setText(full)

    def _update_vo_full_address(self):
        to = self.txt_vo_to.text().strip()
        location = self.txt_vo_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_vo_full_addr.setText(full)

    def _on_mdsd1_nguongoc_changed(self, *args):
        parts = []
        code1 = self.cmb_mdsd1_nguongoc.currentData()
        code2 = self.cmb_mdsd1_ma_nguon_goc.currentData()
        if code1 and code1 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code1])
        if code2 and code2 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code2])
        self.txt_mdsd1_nguongoc_chitiet.setText(" ".join(parts))

    def _on_mdsd2_nguongoc_changed(self, *args):
        parts = []
        code1 = self.cmb_mdsd2_nguongoc.currentData()
        code2 = self.cmb_mdsd2_ma_nguon_goc.currentData()
        if code1 and code1 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code1])
        if code2 and code2 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code2])
        self.txt_mdsd2_nguongoc_chitiet.setText(" ".join(parts))

    def _on_mdsd3_nguongoc_changed(self, *args):
        parts = []
        code1 = self.cmb_mdsd3_nguongoc.currentData()
        code2 = self.cmb_mdsd3_ma_nguon_goc.currentData()
        if code1 and code1 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code1])
        if code2 and code2 in self.master_data.land_use_origins_by_code:
            parts.append(self.master_data.land_use_origins_by_code[code2])
        self.txt_mdsd3_nguongoc_chitiet.setText(" ".join(parts))

    # -------------------------------------------------------------
    # GET & LOAD FORM DATA
    # -------------------------------------------------------------
    def get_attr_dict(self) -> Dict[int, Any]:
        data: Dict[int, Any] = {}

        for col, widget in self.field_inputs.items():
            if not widget.isEnabled():
                data[col] = ""
                continue

            if isinstance(widget, QLineEdit):
                data[col] = widget.text().strip()
            elif isinstance(widget, QPlainTextEdit):
                data[col] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                text = widget.currentText().strip()
                if not text or text == "[Không chọn]" or text == "--" or text == "[Trống]":
                    data[col] = ""
                else:
                    match_idx = widget.findText(text)
                    if match_idx >= 0:
                        val = widget.itemData(match_idx)
                        if isinstance(val, CommuneInfo):
                            data[col] = val.code_3cap
                        elif val is not None and str(val) != "":
                            data[col] = str(val)
                        elif " - " in text:
                            data[col] = text.split(" - ")[0].strip()
                        else:
                            data[col] = text
                    else:
                        if " - " in text:
                            data[col] = text.split(" - ")[0].strip()
                        else:
                            data[col] = text
            elif isinstance(widget, QCheckBox):
                data[col] = "1" if widget.isChecked() else "0"

        # Gender conversion
        if 10 in data:
            if data[10] in ("Nam", "1"):
                data[10] = "1"
            elif data[10] in ("Nữ", "0"):
                data[10] = "0"
            else:
                data[10] = ""
        if 27 in data:
            if data[27] in ("Nam", "1"):
                data[27] = "1"
            elif data[27] in ("Nữ", "0"):
                data[27] = "0"
            else:
                data[27] = ""

        # Specific unchecked group clears
        if hasattr(self, 'chk_has_spouse') and not self.chk_has_spouse.isChecked():
            for c in range(26, 43):
                data[c] = ""

        if hasattr(self, 'chk_has_mdsd2') and not self.chk_has_mdsd2.isChecked():
            for c in range(62, 70):
                data[c] = ""

        if hasattr(self, 'chk_has_mdsd3') and not self.chk_has_mdsd3.isChecked():
            for c in range(70, 78):
                data[c] = ""

        if hasattr(self, 'chk_has_quan_ly') and not self.chk_has_quan_ly.isChecked():
            for c in (96, 97, 98):
                data[c] = ""

        if hasattr(self, 'chk_has_han_che') and not self.chk_has_han_che.isChecked():
            for c in range(111, 118):
                data[c] = ""

        if hasattr(self, 'chk_has_nvtc') and not self.chk_has_nvtc.isChecked():
            for c in range(118, 124):
                data[c] = ""

        if hasattr(self, 'chk_has_mg') and not self.chk_has_mg.isChecked():
            for c in range(124, 129):
                data[c] = ""

        if hasattr(self, 'chk_has_no') and not self.chk_has_no.isChecked():
            for c in range(129, 134):
                data[c] = ""

        if hasattr(self, 'chk_has_nha') and not self.chk_has_nha.isChecked():
            for c in range(134, 142):
                data[c] = ""

        if hasattr(self, 'chk_has_ctxd') and not self.chk_has_ctxd.isChecked():
            for c in range(142, 155):
                data[c] = ""

        if hasattr(self, 'chk_has_ctngam') and not self.chk_has_ctngam.isChecked():
            for c in range(155, 163):
                data[c] = ""

        if hasattr(self, 'chk_has_cay') and not self.chk_has_cay.isChecked():
            for c in range(163, 169):
                data[c] = ""

        if hasattr(self, 'chk_has_thua_cu') and not self.chk_has_thua_cu.isChecked():
            for c in range(169, 179):
                data[c] = ""

        return data

    def load_attr_dict(self, data: Dict[int, Any], serial: str):
        for col, widget in self.field_inputs.items():
            val = str(data.get(col, "") or "").strip()
            if col == 2 and not val and serial:
                val = serial

            if isinstance(widget, QLineEdit):
                widget.setText(val)
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(val)
            elif isinstance(widget, QComboBox):
                if not val:
                    widget.setCurrentIndex(0)
                    continue

                if col == 93:
                    # Searchable commune by location text or code
                    found = False
                    for i in range(widget.count()):
                        c_data = str(widget.itemData(i) or "")
                        c_text = widget.itemText(i)
                        if val.lower() in c_data.lower() or val.lower() in c_text.lower() or c_data == val:
                            widget.setCurrentIndex(i)
                            found = True
                            break
                    if not found:
                        widget.setEditText(val)

                elif col in (20, 37):
                    match_c = self.master_data.get_commune(val)
                    if match_c:
                        disp = f"{match_c.code_3cap} - {match_c.name_3cap}, {match_c.district}"
                        widget.setCurrentText(disp)
                    else:
                        widget.setCurrentText(val)
                elif col in (54, 62, 70, 172):
                    match_lt = self.master_data.get_land_type(val)
                    if match_lt:
                        disp = f"{match_lt.code} - {match_lt.name}"
                        widget.setCurrentText(disp)
                    else:
                        widget.setCurrentText(val)
                elif col in (59, 60, 67, 68, 75, 76, 174):
                    if val in self.master_data.land_use_origins_by_code:
                        disp = f"{val} - {self.master_data.land_use_origins_by_code[val]}"
                        widget.setCurrentText(disp)
                    else:
                        widget.setCurrentText(val)
                elif col in (10, 27):
                    if val in ("1", "Nam"):
                        widget.setCurrentText("Nam")
                    elif val in ("0", "Nữ"):
                        widget.setCurrentText("Nữ")
                    else:
                        widget.setCurrentIndex(0)
                else:
                    found = False
                    for i in range(widget.count()):
                        c_data = widget.itemData(i)
                        c_text = widget.itemText(i)
                        if c_data == val or (c_data and str(c_data) == str(val)):
                            widget.setCurrentIndex(i)
                            found = True
                            break
                        if c_text.startswith(f"{val} - ") or c_text == val:
                            widget.setCurrentIndex(i)
                            found = True
                            break
                    if not found:
                        widget.setEditText(val)

            elif isinstance(widget, QCheckBox):
                widget.setChecked(val in ("1", "True", "true", "x", "X"))

        # Check sub-groups activation
        has_vo = any(str(data.get(c, "") or "").strip() for c in range(26, 43))
        self.chk_has_spouse.setChecked(has_vo)

        has_hc = any(str(data.get(c, "") or "").strip() for c in range(111, 118))
        self.chk_has_han_che.setChecked(has_hc)

        has_nvtc = any(str(data.get(c, "") or "").strip() for c in range(118, 124))
        self.chk_has_nvtc.setChecked(has_nvtc)

        has_mg = any(str(data.get(c, "") or "").strip() for c in range(124, 129))
        self.chk_has_mg.setChecked(has_mg)

        has_no = any(str(data.get(c, "") or "").strip() for c in range(129, 134))
        self.chk_has_no.setChecked(has_no)

        has_nha = any(str(data.get(c, "") or "").strip() for c in range(134, 142))
        self.chk_has_nha.setChecked(has_nha)

        has_ctxd = any(str(data.get(c, "") or "").strip() for c in range(142, 155))
        self.chk_has_ctxd.setChecked(has_ctxd)

        has_ctngam = any(str(data.get(c, "") or "").strip() for c in range(155, 163))
        self.chk_has_ctngam.setChecked(has_ctngam)

        has_cay = any(str(data.get(c, "") or "").strip() for c in range(163, 169))
        self.chk_has_cay.setChecked(has_cay)

        has_thua_cu = any(str(data.get(c, "") or "").strip() for c in range(169, 179))
        self.chk_has_thua_cu.setChecked(has_thua_cu)

        # Always focus on Số thửa (43) on load
        self.txt_thua_so.setFocus()
        self.active_input_widget = self.txt_thua_so
        self._highlight_active_field(self.txt_thua_so, 43)
