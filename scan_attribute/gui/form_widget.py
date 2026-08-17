"""
Form Widget hosting 6 tabbed sections mapping all 186 columns.
All fields are explicitly visible and editable on the right panel with searchable dropdowns and compact layout.
Guaranteed no horizontal scrolling needed across all tabs.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout, 
    QLineEdit, QComboBox, QCheckBox, QLabel, QGroupBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QApplication, QCompleter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from scan_attribute.core.data_models import MasterDataManager, CommuneInfo, MeasurementInfo


class SearchableComboBox(QComboBox):
    """A compact, filterable QComboBox with editable search and substring matching auto-complete."""
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
                min-height: 25px;
                max-height: 25px;
                font-size: 12px;
                padding: 1px 4px;
            }
            QComboBox QAbstractItemView {
                min-width: 320px;
                font-size: 12px;
            }
        """)

        comp = self.completer()
        if comp:
            comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        if self.lineEdit():
            self.lineEdit().setPlaceholderText("🔍 Tìm / Chọn...")


class AttributeFormWidget(QWidget):
    save_requested = Signal()  # Emits on Ctrl+Enter or Save button

    def __init__(self, master_data: MasterDataManager, parent=None):
        super().__init__(parent)
        self.master_data = master_data
        self.last_commune_code: str = ""
        self.field_inputs: Dict[int, QWidget] = {}
        self.active_input_widget: Optional[QWidget] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                font-size: 11px;
                font-weight: bold;
                padding: 4px 6px;
            }
        """)

        # Tab 1: GCN & Ký cấp (Cols 1-4, 99-110)
        self.tab_widget.addTab(self._create_tab_gcn(), "1. GCN & Ký Cấp")
        # Tab 2: Chủ sử dụng (Cols 5-25)
        self.tab_widget.addTab(self._create_tab_chu(), "2. Chủ Sử Dụng")
        # Tab 3: Vợ (Chồng) (Cols 26-42)
        self.tab_widget.addTab(self._create_tab_vo_chong(), "3. Vợ / Chồng")
        # Tab 4: Thửa đất & MĐSD (Cols 43-98)
        self.tab_widget.addTab(self._create_tab_thua_dat(), "4. Thửa Đất & MĐSD")
        # Tab 5: NVTC & Hạn chế (Cols 111-133)
        self.tab_widget.addTab(self._create_tab_nvtc(), "5. NVTC & Hạn Chế")
        # Tab 6: Tài sản & Lưu kho (Cols 134-186)
        self.tab_widget.addTab(self._create_tab_tai_san_va_khac(), "6. Tài Sản & Lưu Kho")

        layout.addWidget(self.tab_widget)

        # Bottom Action Row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(4, 2, 4, 2)
        self.lbl_status = QLabel("📍 Đang nhắm: Mã vạch")
        self.lbl_status.setStyleSheet("color: #1565c0; font-weight: bold; font-size: 11px;")
        
        self.btn_save = QPushButton("💾 Lưu & Tiếp (Ctrl+Enter)")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 5px 14px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_save.clicked.connect(self.save_requested.emit)

        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)

        layout.addLayout(btn_row)

        self._track_focus()

    def _track_focus(self):
        """Connects focus events of all input widgets to remember active_input_widget."""
        for c, widget in self.field_inputs.items():
            if isinstance(widget, (QLineEdit, QPlainTextEdit, QComboBox)):
                widget.installEventFilter(self)
                if isinstance(widget, QComboBox) and widget.isEditable() and widget.lineEdit():
                    widget.lineEdit().installEventFilter(self)

    def eventFilter(self, watched, event):
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
            6: "ĐTSD", 7: "HGD", 8: "Người đại diện", 9: "Họ tên Chủ", 13: "Loại GT", 14: "Số GT/CCCD Chủ", 19: "Tổ/Khu Chủ", 20: "Mã Xã Chủ", 21: "Xã/Huyện/Tỉnh Chủ", 22: "Địa chỉ đầy đủ Chủ",
            26: "Họ tên Vợ/Chồng", 30: "Loại GT Vợ/Chồng", 31: "CCCD Vợ/Chồng", 36: "Tổ/Khu Vợ/Chồng", 37: "Mã Xã Vợ/Chồng", 38: "Xã/Huyện/Tỉnh Vợ/Chồng", 39: "Địa chỉ đầy đủ Vợ/Chồng", 41: "Dân tộc Vợ/Chồng", 42: "Quốc tịch Vợ/Chồng",
            43: "Số thửa", 44: "Số tờ", 46: "Loại bản đồ", 47: "Đơn vị đo", 48: "Phương pháp đo", 49: "Mức độ chính xác", 50: "Ngày hoàn thành",
            52: "Diện tích bản đồ", 53: "Diện tích pháp lý",
            54: "MĐSD 1", 56: "Diện tích 1", 60: "Mã nguồn gốc 1", 61: "Nguồn gốc chi tiết 1",
            62: "MĐSD 2", 64: "Diện tích 2", 68: "Mã nguồn gốc 2", 69: "Nguồn gốc chi tiết 2",
            70: "MĐSD 3", 72: "Diện tích 3", 76: "Mã nguồn gốc 3", 77: "Nguồn gốc chi tiết 3",
            90: "Tổ/Khu Thửa đất", 91: "Mã Xã Thửa đất", 92: "Xã/Huyện/Tỉnh Thửa đất", 94: "Địa chỉ thửa đất",
            99: "Loại GCN", 100: "Số vào sổ", 102: "Ngày ký GCN", 103: "Người ký", 104: "Ủy quyền ký", 105: "Ký thay", 106: "Ngày cấp", 110: "Ghi chú T2",
            118: "Loại NVTC", 119: "Số tiền NVTC", 183: "Thư mục lưu HSQ"
        }
        name = field_names.get(col_idx, f"Cột {col_idx}")
        self.lbl_status.setText(f"📍 Đang nhắm ô: [{name}] (OCR/Scan sẽ dán vào đây)")

        for w in self.field_inputs.values():
            if isinstance(w, QLineEdit):
                if w == target_widget:
                    w.setStyleSheet("border: 2px solid #1565c0; background-color: #e3f2fd; font-weight: bold; min-height: 24px;")
                else:
                    w.setStyleSheet("min-height: 24px;")
            elif isinstance(w, QPlainTextEdit):
                if w == target_widget:
                    w.setStyleSheet("border: 2px solid #1565c0; background-color: #e3f2fd; font-weight: bold;")
                else:
                    w.setStyleSheet("")

    def navigate_to_pdf_type(self, pdf_filename: str):
        """Automatically switches to the corresponding form tab and focuses the primary field based on PDF type."""
        if not pdf_filename:
            return

        fn = pdf_filename.lower()
        if "vo" in fn or "chong" in fn or "vc" in fn or "spouse" in fn:
            self.tab_widget.setCurrentIndex(2)  # Tab 3: Vợ / Chồng
            if not self.chk_has_spouse.isChecked():
                self.chk_has_spouse.setChecked(True)
            self.txt_vo_name.setFocus()
            self.active_input_widget = self.txt_vo_name
            self._highlight_active_field(self.txt_vo_name, 26)
        elif "gtk" in fn or "bando" in fn or "trichluc" in fn or "td" in fn or "tl" in fn or "thua" in fn or "mdsd" in fn:
            self.tab_widget.setCurrentIndex(3)  # Tab 4: Thửa đất & MĐSD
            self.txt_thua_so.setFocus()
            self.active_input_widget = self.txt_thua_so
            self._highlight_active_field(self.txt_thua_so, 43)
        elif "gt" in fn or "cccd" in fn or "cmnd" in fn or "hochieu" in fn or "hk" in fn or "nhanthan" in fn:
            self.tab_widget.setCurrentIndex(1)  # Tab 2: Chủ sử dụng
            self.txt_chu_name.setFocus()
            self.active_input_widget = self.txt_chu_name
            self._highlight_active_field(self.txt_chu_name, 9)
        elif "nvtc" in fn or "thue" in fn or "lptb" in fn or "tien" in fn:
            self.tab_widget.setCurrentIndex(4)  # Tab 5: NVTC & Hạn chế
            self.cmb_nvtc_loai.setFocus()
            self.active_input_widget = self.cmb_nvtc_loai
            self._highlight_active_field(self.cmb_nvtc_loai, 118)
        elif "ts" in fn or "nha" in fn or "kho" in fn or "tsglvd" in fn or "congtrinh" in fn:
            self.tab_widget.setCurrentIndex(5)  # Tab 6: Tài sản & Lưu kho
            self.txt_nha_dt_xd.setFocus()
            self.active_input_widget = self.txt_nha_dt_xd
            self._highlight_active_field(self.txt_nha_dt_xd, 134)
        elif "gcn" in fn or "bia" in fn or "giaychungnhan" in fn:
            self.tab_widget.setCurrentIndex(0)  # Tab 1: GCN & Ký Cấp
            self.txt_barcode.setFocus()
            self.active_input_widget = self.txt_barcode
            self._highlight_active_field(self.txt_barcode, 4)
        else:
            self.tab_widget.setCurrentIndex(0)

    def set_ocr_text_to_active_field(self, text: str):
        """Pastes OCR text into active focused input widget and updates clipboard."""
        if not text:
            return
        clean_text = text.strip()

        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_text)

        target = self.active_input_widget
        if not target:
            target = self.txt_barcode

        if target:
            if isinstance(target, QLineEdit):
                target.setText(clean_text)
            elif isinstance(target, QPlainTextEdit):
                target.setPlainText(clean_text)
            elif isinstance(target, QComboBox):
                target.setEditText(clean_text)

    def _register_input(self, col_idx: int, widget: QWidget):
        self.field_inputs[col_idx] = widget
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return widget

    def _setup_form_layout(self, form: QFormLayout):
        form.setContentsMargins(4, 4, 4, 4)
        form.setVerticalSpacing(3)
        form.setHorizontalSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

    def _create_scroll_area(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        return scroll

    # -------------------------------------------------------------
    # TAB 1: GCN & KÝ CẤP (Cols 1-4, 99-110)
    # -------------------------------------------------------------
    def _create_tab_gcn(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        self._setup_form_layout(form)

        self.txt_serial = QLineEdit()
        self.txt_serial.textChanged.connect(self._auto_sync_ma_don)
        self._register_input(2, self.txt_serial)

        self.txt_ma_hs = QLineEdit()
        self._register_input(3, self.txt_ma_hs)

        self.txt_barcode = QLineEdit()
        self.txt_barcode.setPlaceholderText("Ví dụ: 0667320081887")
        self.txt_barcode.textChanged.connect(self._auto_sync_ma_hs_goc)
        self._register_input(4, self.txt_barcode)
        self.active_input_widget = self.txt_barcode

        # Ký cấp GCN
        self.cmb_loai_gcn = SearchableComboBox()
        for g in self.master_data.gcn_types:
            self.cmb_loai_gcn.addItem(g, g)
        if "Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP" not in self.master_data.gcn_types:
            self.cmb_loai_gcn.addItem("Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP", "Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP")
        self.cmb_loai_gcn.setCurrentText("Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP")
        self._register_input(99, self.cmb_loai_gcn)

        self.txt_so_vao_so = QLineEdit()
        self.txt_so_vao_so.setPlaceholderText("Ví dụ: CH89147")
        self._register_input(100, self.txt_so_vao_so)

        self.txt_ngay_vao_so = QLineEdit()
        self.txt_ngay_vao_so.setPlaceholderText("Ví dụ: 31/07/2024")
        self._register_input(101, self.txt_ngay_vao_so)

        self.txt_ngay_ky = QLineEdit()
        self.txt_ngay_ky.setPlaceholderText("Ví dụ: 31/07/2024")
        self.txt_ngay_ky.textChanged.connect(self._auto_sync_ngay_cap)
        self._register_input(102, self.txt_ngay_ky)

        self.txt_nguoi_ky = QLineEdit()
        self.txt_nguoi_ky.setPlaceholderText("Ví dụ: Vũ Ngọc Lâm")
        self._register_input(103, self.txt_nguoi_ky)

        self.cmb_uy_quyen_ky = SearchableComboBox()
        self.cmb_uy_quyen_ky.addItem("0 - Không ủy quyền", "0")
        self.cmb_uy_quyen_ky.addItem("1 - Có ủy quyền", "1")
        self._register_input(104, self.cmb_uy_quyen_ky)

        self.cmb_ky_thay = SearchableComboBox()
        self.cmb_ky_thay.addItem("1 - Ký thay (KT.)", "1")
        self.cmb_ky_thay.addItem("0 - Ký trực tiếp", "0")
        self._register_input(105, self.cmb_ky_thay)

        self.txt_ngay_cap = QLineEdit()
        self.txt_ngay_cap.setPlaceholderText("Ví dụ: 31/07/2024")
        self._register_input(106, self.txt_ngay_cap)

        self.txt_ten_dot_cap = QLineEdit()
        self._register_input(107, self.txt_ten_dot_cap)

        self.txt_can_cu_phap_ly = QLineEdit()
        self._register_input(108, self.txt_can_cu_phap_ly)

        self.txt_ghi_chu_t1 = QLineEdit()
        self._register_input(109, self.txt_ghi_chu_t1)

        self.txt_ghi_chu_t2 = QPlainTextEdit()
        self.txt_ghi_chu_t2.setMaximumHeight(50)
        self._register_input(110, self.txt_ghi_chu_t2)

        form.addRow("Số Serial (2):", self.txt_serial)
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
        form.addRow("Ghi chú T2 (110):", self.txt_ghi_chu_t2)

        return self._create_scroll_area(container)

    def _auto_sync_ma_hs_goc(self, text: str):
        clean = text.strip()
        if len(clean) >= 6:
            self.txt_ma_hs.setText(clean[-6:])
        elif clean:
            self.txt_ma_hs.setText(clean)

    def _auto_sync_ma_don(self, text: str):
        """Auto-populates Col 95 (Mã đơn) from Col 2 (Số Serial) without spaces."""
        clean = text.replace(" ", "").strip()
        self.txt_thua_ma_don.setText(clean)

    def _auto_sync_ngay_cap(self, text: str):
        if not self.txt_ngay_cap.text() or self.txt_ngay_cap.text() == text[:-1]:
            self.txt_ngay_cap.setText(text)

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
        if self.master_data.dtsd_list:
            for code, name in self.master_data.dtsd_list:
                self.cmb_chu_dtsd.addItem(f"{code} - {name}", code)
        else:
            self.cmb_chu_dtsd.addItem("CNV - Cá nhân trong nước", "CNV")
            self.cmb_chu_dtsd.addItem("GDC - Hộ gia đình, cá nhân", "GDC")
            self.cmb_chu_dtsd.addItem("TCC - Tổ chức trong nước", "TCC")
        self.cmb_chu_dtsd.setCurrentText("CNV - Cá nhân trong nước")
        self._register_input(6, self.cmb_chu_dtsd)

        self.cmb_chu_hgd = SearchableComboBox()
        self.cmb_chu_hgd.addItem("0 - Không phải HGD", "0")
        self.cmb_chu_hgd.addItem("1 - Là Hộ gia đình", "1")
        self._register_input(7, self.cmb_chu_hgd)

        self.cmb_chu_daidien = SearchableComboBox()
        self.cmb_chu_daidien.addItem("0 - Không phải đại diện", "0")
        self.cmb_chu_daidien.addItem("1 - Là người đại diện", "1")
        self._register_input(8, self.cmb_chu_daidien)

        self.txt_chu_name = QLineEdit()
        self.txt_chu_name.setPlaceholderText("Ví dụ: Nguyễn Anh Tuấn")
        self._register_input(9, self.txt_chu_name)

        self.cmb_chu_gioitinh = SearchableComboBox()
        self.cmb_chu_gioitinh.addItem("Nam", "1")
        self.cmb_chu_gioitinh.addItem("Nữ", "0")
        self.cmb_chu_gioitinh.addItem("[Trống]", "")
        self.cmb_chu_gioitinh.setCurrentText("Nam")
        self._register_input(10, self.cmb_chu_gioitinh)

        self.txt_chu_namsinh = QLineEdit()
        self.txt_chu_namsinh.setPlaceholderText("Ví dụ: 1980")
        self._register_input(11, self.txt_chu_namsinh)

        self.txt_chu_nammat = QLineEdit()
        self._register_input(12, self.txt_chu_nammat)

        # Loại GT: lấy mã viết tắt CCCD, CMND, HC, GKS, QD, K
        self.cmb_chu_id_type = SearchableComboBox()
        for code, label in self.master_data.id_types:
            self.cmb_chu_id_type.addItem(label, code)
        self.cmb_chu_id_type.setCurrentText("CCCD - Căn cước công dân")
        self._register_input(13, self.cmb_chu_id_type)

        self.txt_chu_id_num = QLineEdit()
        self.txt_chu_id_num.setPlaceholderText("Số CCCD / CMND")
        self._register_input(14, self.txt_chu_id_num)

        self.txt_chu_id_date = QLineEdit()
        self._register_input(15, self.txt_chu_id_date)

        self.txt_chu_id_place = QLineEdit("Cục CSQLHC về TTXH")
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
        self._populate_communes(self.cmb_chu_xa)
        self.cmb_chu_xa.currentIndexChanged.connect(self._on_chu_commune_changed)
        self._register_input(20, self.cmb_chu_xa)

        self.txt_chu_xa_huyen_tinh = QLineEdit()
        self.txt_chu_xa_huyen_tinh.setPlaceholderText("Xã/Phường, Quận/Huyện, Tỉnh/TP")
        self.txt_chu_xa_huyen_tinh.textChanged.connect(self._update_chu_full_address)
        self._register_input(21, self.txt_chu_xa_huyen_tinh)

        self.txt_chu_full_addr = QLineEdit()
        self.txt_chu_full_addr.textChanged.connect(self._on_chu_full_addr_changed)
        self._register_input(22, self.txt_chu_full_addr)

        self.txt_chu_phone = QLineEdit()
        self._register_input(23, self.txt_chu_phone)

        self.cmb_chu_dantoc = SearchableComboBox()
        self.cmb_chu_dantoc.addItems(self.master_data.ethnicities)
        self.cmb_chu_dantoc.setCurrentText("Kinh")
        self._register_input(24, self.cmb_chu_dantoc)

        self.cmb_chu_quoctich = SearchableComboBox()
        self.cmb_chu_quoctich.addItems(self.master_data.nationalities)
        self.cmb_chu_quoctich.setCurrentText("Viet Nam")
        self._register_input(25, self.cmb_chu_quoctich)

        form.addRow("Mã chủ (5):", self.txt_chu_ma)
        form.addRow("ĐTSD (6):", self.cmb_chu_dtsd)
        form.addRow("Là HGD (7):", self.cmb_chu_hgd)
        form.addRow("Đại diện (8):", self.cmb_chu_daidien)
        form.addRow("Họ tên Chủ (9):", self.txt_chu_name)
        form.addRow("Giới tính (10):", self.cmb_chu_gioitinh)
        form.addRow("Năm sinh (11):", self.txt_chu_namsinh)
        form.addRow("Năm mất (12):", self.txt_chu_nammat)
        form.addRow("Loại GT (13):", self.cmb_chu_id_type)
        form.addRow("Số GT/CCCD (14):", self.txt_chu_id_num)
        form.addRow("Ngày cấp (15):", self.txt_chu_id_date)
        form.addRow("Nơi cấp (16):", self.txt_chu_id_place)
        form.addRow("Địa chỉ CT (17):", self.txt_chu_address)
        form.addRow("Số nhà (18):", self.txt_chu_sonha)
        form.addRow("Tổ/Khu (19):", self.txt_chu_to)
        form.addRow("Mã Xã (20):", self.cmb_chu_xa)
        form.addRow("Xã/Huyện (21):", self.txt_chu_xa_huyen_tinh)
        form.addRow("Đ/C đầy đủ (22):", self.txt_chu_full_addr)
        form.addRow("SĐT (23):", self.txt_chu_phone)
        form.addRow("Dân tộc (24):", self.cmb_chu_dantoc)
        form.addRow("Quốc tịch (25):", self.cmb_chu_quoctich)

        return self._create_scroll_area(container)

    # -------------------------------------------------------------
    # TAB 3: VỢ / CHỒNG (Cols 26-42)
    # -------------------------------------------------------------
    def _create_tab_vo_chong(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        self._setup_form_layout(form)

        self.chk_has_spouse = QCheckBox("Có thông tin Vợ / Chồng (Đồng sử dụng)")
        self.chk_has_spouse.setStyleSheet("font-weight: bold; color: #d81b60; font-size: 11px;")
        self.chk_has_spouse.toggled.connect(self._toggle_spouse_fields)
        form.addRow(self.chk_has_spouse)

        self.txt_vo_name = QLineEdit()
        self._register_input(26, self.txt_vo_name)

        self.cmb_vo_gioitinh = SearchableComboBox()
        self.cmb_vo_gioitinh.addItem("Nữ", "0")
        self.cmb_vo_gioitinh.addItem("Nam", "1")
        self.cmb_vo_gioitinh.addItem("[Trống]", "")
        self.cmb_vo_gioitinh.setCurrentText("Nữ")
        self._register_input(27, self.cmb_vo_gioitinh)

        self.txt_vo_namsinh = QLineEdit()
        self._register_input(28, self.txt_vo_namsinh)

        self.txt_vo_nammat = QLineEdit()
        self._register_input(29, self.txt_vo_nammat)

        self.cmb_vo_id_type = SearchableComboBox()
        for code, label in self.master_data.id_types:
            self.cmb_vo_id_type.addItem(label, code)
        self.cmb_vo_id_type.setCurrentText("CCCD - Căn cước công dân")
        self._register_input(30, self.cmb_vo_id_type)

        self.txt_vo_id_num = QLineEdit()
        self._register_input(31, self.txt_vo_id_num)

        self.txt_vo_id_date = QLineEdit()
        self._register_input(32, self.txt_vo_id_date)

        self.txt_vo_id_place = QLineEdit("Cục CSQLHC về TTXH")
        self._register_input(33, self.txt_vo_id_place)

        self.txt_vo_address = QLineEdit()
        self._register_input(34, self.txt_vo_address)

        self.txt_vo_sonha = QLineEdit()
        self._register_input(35, self.txt_vo_sonha)

        self.txt_vo_to = QLineEdit()
        self.txt_vo_to.textChanged.connect(self._update_vo_full_address)
        self._register_input(36, self.txt_vo_to)

        self.cmb_vo_xa = SearchableComboBox()
        self._populate_communes(self.cmb_vo_xa)
        self.cmb_vo_xa.currentIndexChanged.connect(self._on_vo_commune_changed)
        self._register_input(37, self.cmb_vo_xa)

        self.txt_vo_xa_huyen_tinh = QLineEdit()
        self.txt_vo_xa_huyen_tinh.setPlaceholderText("Xã/Phường, Quận/Huyện, Tỉnh/TP")
        self.txt_vo_xa_huyen_tinh.textChanged.connect(self._update_vo_full_address)
        self._register_input(38, self.txt_vo_xa_huyen_tinh)

        self.txt_vo_full_addr = QLineEdit()
        self.txt_vo_full_addr.setPlaceholderText("Địa chỉ đầy đủ của Vợ / Chồng")
        self._register_input(39, self.txt_vo_full_addr)

        self.txt_vo_phone = QLineEdit()
        self._register_input(40, self.txt_vo_phone)

        self.cmb_vo_dantoc = SearchableComboBox()
        if "Không rõ" not in self.master_data.ethnicities:
            self.cmb_vo_dantoc.addItem("Không rõ", "Không rõ")
        for e in self.master_data.ethnicities:
            if e != "Không rõ":
                self.cmb_vo_dantoc.addItem(e, e)
        self.cmb_vo_dantoc.setCurrentText("Không rõ")
        self._register_input(41, self.cmb_vo_dantoc)

        self.cmb_vo_quoctich = SearchableComboBox()
        for n in self.master_data.nationalities:
            self.cmb_vo_quoctich.addItem(n, n)
        self.cmb_vo_quoctich.setCurrentText("Viet Nam")
        self._register_input(42, self.cmb_vo_quoctich)

        form.addRow("Họ tên VC (26):", self.txt_vo_name)
        form.addRow("Giới tính (27):", self.cmb_vo_gioitinh)
        form.addRow("Năm sinh (28):", self.txt_vo_namsinh)
        form.addRow("Năm mất (29):", self.txt_vo_nammat)
        form.addRow("Loại GT (30):", self.cmb_vo_id_type)
        form.addRow("Số GT/CCCD (31):", self.txt_vo_id_num)
        form.addRow("Ngày cấp (32):", self.txt_vo_id_date)
        form.addRow("Nơi cấp (33):", self.txt_vo_id_place)
        form.addRow("Địa chỉ CT (34):", self.txt_vo_address)
        form.addRow("Số nhà (35):", self.txt_vo_sonha)
        form.addRow("Tổ/Khu (36):", self.txt_vo_to)
        form.addRow("Mã Xã (37):", self.cmb_vo_xa)
        form.addRow("Xã/Huyện (38):", self.txt_vo_xa_huyen_tinh)
        form.addRow("Đ/C đầy đủ (39):", self.txt_vo_full_addr)
        form.addRow("SĐT (40):", self.txt_vo_phone)
        form.addRow("Dân tộc (41):", self.cmb_vo_dantoc)
        form.addRow("Quốc tịch (42):", self.cmb_vo_quoctich)

        self._toggle_spouse_fields(False)
        return self._create_scroll_area(container)

    def _toggle_spouse_fields(self, enabled: bool):
        for col in range(26, 43):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    # -------------------------------------------------------------
    # TAB 4: THỬA ĐẤT & MĐSD (Cols 43-98)
    # -------------------------------------------------------------
    def _create_tab_thua_dat(self) -> QWidget:
        container = QWidget()
        root_vbox = QVBoxLayout(container)
        root_vbox.setContentsMargins(2, 2, 2, 2)
        root_vbox.setSpacing(4)

        # Top Thửa Đất Fields
        f_top = QFormLayout()
        self._setup_form_layout(f_top)

        self.txt_thua_so = QLineEdit()
        self.txt_thua_so.setPlaceholderText("Ví dụ: 124")
        self._register_input(43, self.txt_thua_so)

        self.txt_to_so = QLineEdit()
        self.txt_to_so.setPlaceholderText("Ví dụ: 71")
        self._register_input(44, self.txt_to_so)

        self.txt_tyle = QLineEdit("500")
        self._register_input(45, self.txt_tyle)

        # Loại bản đồ: lấy giá trị 1, 2, 3, 4, 5
        self.cmb_loai_bando = SearchableComboBox()
        for code, label in self.master_data.map_types:
            self.cmb_loai_bando.addItem(label, code)
        self.cmb_loai_bando.setCurrentText("1 - Bản đồ địa chính (VN2000)")
        self._register_input(46, self.cmb_loai_bando)

        # Đơn vị đo đạc từ QNH_ThongTinDoDac.xlsx
        self.cmb_don_vi_do = SearchableComboBox()
        self.cmb_don_vi_do.addItem("", "")
        for u in self.master_data.measurement_units:
            self.cmb_don_vi_do.addItem(u, u)
        self._register_input(47, self.cmb_don_vi_do)

        # Mặc định Col 48: Toàn đạc điện tử
        self.txt_phuong_phap_do = QLineEdit("Toàn đạc điện tử")
        self._register_input(48, self.txt_phuong_phap_do)

        # Mặc định Col 49: Cao
        self.txt_nguoi_kiem_tra = QLineEdit("Cao")
        self._register_input(49, self.txt_nguoi_kiem_tra)

        # Ngày hoàn thành từ QNH_ThongTinDoDac.xlsx
        self.txt_ngay_hoan_thanh = QLineEdit()
        self._register_input(50, self.txt_ngay_hoan_thanh)

        self.cmb_phan_loai_thua = SearchableComboBox()
        self.cmb_phan_loai_thua.addItem("A - Đã cấp GCN, không có tài sản", "A")
        self.cmb_phan_loai_thua.addItem("B - Đã cấp GCN, có tài sản", "B")
        self.cmb_phan_loai_thua.addItem("C - Chưa cấp GCN", "C")
        self.cmb_phan_loai_thua.addItem("D - Đất công ích / UBND", "D")
        self.cmb_phan_loai_thua.addItem("E - Thửa đất khác", "E")
        self.cmb_phan_loai_thua.setCurrentText("A - Đã cấp GCN, không có tài sản")
        self._register_input(51, self.cmb_phan_loai_thua)

        self.txt_dt_bando = QLineEdit()
        self.txt_dt_bando.setPlaceholderText("Ví dụ: 120.5")
        self.txt_dt_bando.textChanged.connect(self._auto_sync_dt_phaply)
        self._register_input(52, self.txt_dt_bando)

        self.txt_dt_phaply = QLineEdit()
        self.txt_dt_phaply.setPlaceholderText("Ví dụ: 120.5")
        self._register_input(53, self.txt_dt_phaply)

        f_top.addRow("Số thửa (43):", self.txt_thua_so)
        f_top.addRow("Số tờ (44):", self.txt_to_so)
        f_top.addRow("Tỷ lệ BĐ (45):", self.txt_tyle)
        f_top.addRow("Loại BĐ (46):", self.cmb_loai_bando)
        f_top.addRow("Đơn vị đo (47):", self.cmb_don_vi_do)
        f_top.addRow("PP đo (48):", self.txt_phuong_phap_do)
        f_top.addRow("Mức độ chính xác (49):", self.txt_nguoi_kiem_tra)
        f_top.addRow("Ngày xong (50):", self.txt_ngay_hoan_thanh)
        f_top.addRow("Phân loại (51):", self.cmb_phan_loai_thua)
        f_top.addRow("DT bản đồ (52):", self.txt_dt_bando)
        f_top.addRow("DT pháp lý (53):", self.txt_dt_phaply)
        root_vbox.addLayout(f_top)

        # --- MĐSD 1 (Cols 54-61) ---
        grp1 = QGroupBox("Mục đích sử dụng 1 (Chính - Cols 54-61)")
        f1 = QFormLayout(grp1)
        self._setup_form_layout(f1)

        self.cmb_mdsd1 = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd1)
        self.cmb_mdsd1.currentIndexChanged.connect(self._on_mdsd1_changed)
        self._register_input(54, self.cmb_mdsd1)

        self.txt_mdsd1_kh = QLineEdit()
        self._register_input(55, self.txt_mdsd1_kh)

        self.txt_mdsd1_dt = QLineEdit()
        self._register_input(56, self.txt_mdsd1_dt)

        self.cmb_mdsd1_sdc = SearchableComboBox()
        self.cmb_mdsd1_sdc.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd1_sdc.addItem("1 - Sử dụng chung", "1")
        self.cmb_mdsd1_sdc.addItem("[Không chọn]", "")
        self.cmb_mdsd1_sdc.setCurrentText("0 - Sử dụng riêng")
        self._register_input(57, self.cmb_mdsd1_sdc)

        self.txt_mdsd1_thoi_han = QLineEdit("Lâu dài")
        self._register_input(58, self.txt_mdsd1_thoi_han)

        self.cmb_mdsd1_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd1_nguon_goc)
        self.cmb_mdsd1_nguon_goc.currentIndexChanged.connect(self._on_mdsd1_origin_changed)
        self._register_input(59, self.cmb_mdsd1_nguon_goc)

        self.cmb_mdsd1_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd1_ma_nguon_goc)
        self.cmb_mdsd1_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd1_origin_changed)
        self._register_input(60, self.cmb_mdsd1_ma_nguon_goc)

        self.txt_mdsd1_nguon_goc_ct = QLineEdit()
        self._register_input(61, self.txt_mdsd1_nguon_goc_ct)

        f1.addRow("Loại đất (54):", self.cmb_mdsd1)
        f1.addRow("Ký hiệu (55):", self.txt_mdsd1_kh)
        f1.addRow("Diện tích (56):", self.txt_mdsd1_dt)
        f1.addRow("Là SD chung (57):", self.cmb_mdsd1_sdc)
        f1.addRow("Thời hạn SD (58):", self.txt_mdsd1_thoi_han)
        f1.addRow("Nguồn gốc BĐ (59):", self.cmb_mdsd1_nguon_goc)
        f1.addRow("Mã N.gốc (60):", self.cmb_mdsd1_ma_nguon_goc)
        f1.addRow("N.gốc CT (61):", self.txt_mdsd1_nguon_goc_ct)
        root_vbox.addWidget(grp1)

        # --- MĐSD 2 (Cols 62-69) ---
        grp2 = QGroupBox("Mục đích sử dụng 2 (Phụ - Cols 62-69)")
        f2 = QFormLayout(grp2)
        self._setup_form_layout(f2)

        self.chk_has_mdsd2 = QCheckBox("Có Mục đích sử dụng 2")
        self.chk_has_mdsd2.setStyleSheet("font-weight: bold; color: #1976d2;")
        self.chk_has_mdsd2.toggled.connect(self._toggle_mdsd2_fields)
        f2.addRow(self.chk_has_mdsd2)

        self.cmb_mdsd2 = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd2)
        self.cmb_mdsd2.currentIndexChanged.connect(self._on_mdsd2_changed)
        self._register_input(62, self.cmb_mdsd2)

        self.txt_mdsd2_kh = QLineEdit()
        self._register_input(63, self.txt_mdsd2_kh)

        self.txt_mdsd2_dt = QLineEdit()
        self._register_input(64, self.txt_mdsd2_dt)

        self.cmb_mdsd2_sdc = SearchableComboBox()
        self.cmb_mdsd2_sdc.addItem("[Không chọn]", "")
        self.cmb_mdsd2_sdc.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd2_sdc.addItem("1 - Sử dụng chung", "1")
        self._register_input(65, self.cmb_mdsd2_sdc)

        self.txt_mdsd2_thoi_han = QLineEdit()
        self._register_input(66, self.txt_mdsd2_thoi_han)

        self.cmb_mdsd2_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd2_nguon_goc)
        self.cmb_mdsd2_nguon_goc.currentIndexChanged.connect(self._on_mdsd2_origin_changed)
        self._register_input(67, self.cmb_mdsd2_nguon_goc)

        self.cmb_mdsd2_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd2_ma_nguon_goc)
        self.cmb_mdsd2_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd2_origin_changed)
        self._register_input(68, self.cmb_mdsd2_ma_nguon_goc)

        self.txt_mdsd2_nguon_goc_ct = QLineEdit()
        self._register_input(69, self.txt_mdsd2_nguon_goc_ct)

        f2.addRow("Loại đất 2 (62):", self.cmb_mdsd2)
        f2.addRow("Ký hiệu 2 (63):", self.txt_mdsd2_kh)
        f2.addRow("Diện tích 2 (64):", self.txt_mdsd2_dt)
        f2.addRow("Là SD chung (65):", self.cmb_mdsd2_sdc)
        f2.addRow("Thời hạn 2 (66):", self.txt_mdsd2_thoi_han)
        f2.addRow("Nguồn gốc BĐ 2 (67):", self.cmb_mdsd2_nguon_goc)
        f2.addRow("Mã N.gốc 2 (68):", self.cmb_mdsd2_ma_nguon_goc)
        f2.addRow("N.gốc CT 2 (69):", self.txt_mdsd2_nguon_goc_ct)
        self._toggle_mdsd2_fields(False)
        root_vbox.addWidget(grp2)

        # --- MĐSD 3 (Cols 70-77) ---
        grp3 = QGroupBox("Mục đích sử dụng 3 (Cols 70-77)")
        f3 = QFormLayout(grp3)
        self._setup_form_layout(f3)

        self.chk_has_mdsd3 = QCheckBox("Có Mục đích sử dụng 3")
        self.chk_has_mdsd3.setStyleSheet("font-weight: bold; color: #1976d2;")
        self.chk_has_mdsd3.toggled.connect(self._toggle_mdsd3_fields)
        f3.addRow(self.chk_has_mdsd3)

        self.cmb_mdsd3 = SearchableComboBox()
        self._populate_land_types(self.cmb_mdsd3)
        self.cmb_mdsd3.currentIndexChanged.connect(self._on_mdsd3_changed)
        self._register_input(70, self.cmb_mdsd3)

        self.txt_mdsd3_kh = QLineEdit()
        self._register_input(71, self.txt_mdsd3_kh)

        self.txt_mdsd3_dt = QLineEdit()
        self._register_input(72, self.txt_mdsd3_dt)

        self.cmb_mdsd3_sdc = SearchableComboBox()
        self.cmb_mdsd3_sdc.addItem("[Không chọn]", "")
        self.cmb_mdsd3_sdc.addItem("0 - Sử dụng riêng", "0")
        self.cmb_mdsd3_sdc.addItem("1 - Sử dụng chung", "1")
        self._register_input(73, self.cmb_mdsd3_sdc)

        self.txt_mdsd3_thoi_han = QLineEdit()
        self._register_input(74, self.txt_mdsd3_thoi_han)

        self.cmb_mdsd3_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd3_nguon_goc)
        self.cmb_mdsd3_nguon_goc.currentIndexChanged.connect(self._on_mdsd3_origin_changed)
        self._register_input(75, self.cmb_mdsd3_nguon_goc)

        self.cmb_mdsd3_ma_nguon_goc = SearchableComboBox()
        self._populate_land_use_origins(self.cmb_mdsd3_ma_nguon_goc)
        self.cmb_mdsd3_ma_nguon_goc.currentIndexChanged.connect(self._on_mdsd3_origin_changed)
        self._register_input(76, self.cmb_mdsd3_ma_nguon_goc)

        self.txt_mdsd3_nguon_goc_ct = QLineEdit()
        self._register_input(77, self.txt_mdsd3_nguon_goc_ct)

        f3.addRow("Loại đất 3 (70):", self.cmb_mdsd3)
        f3.addRow("Ký hiệu 3 (71):", self.txt_mdsd3_kh)
        f3.addRow("Diện tích 3 (72):", self.txt_mdsd3_dt)
        f3.addRow("Là SD chung (73):", self.cmb_mdsd3_sdc)
        f3.addRow("Thời hạn 3 (74):", self.txt_mdsd3_thoi_han)
        f3.addRow("Nguồn gốc BĐ 3 (75):", self.cmb_mdsd3_nguon_goc)
        f3.addRow("Mã N.gốc 3 (76):", self.cmb_mdsd3_ma_nguon_goc)
        f3.addRow("N.gốc CT 3 (77):", self.txt_mdsd3_nguon_goc_ct)
        self._toggle_mdsd3_fields(False)
        root_vbox.addWidget(grp3)

        # --- Địa chỉ thửa đất & Quản lý (Cols 89-98) ---
        grp_addr = QGroupBox("Địa chỉ thửa đất & Đơn đăng ký (Cols 89-98)")
        f_addr = QFormLayout(grp_addr)
        self._setup_form_layout(f_addr)

        self.chk_same_chu_address = QCheckBox("Địa chỉ thửa đất cùng địa chỉ Chủ sử dụng")
        self.chk_same_chu_address.setChecked(True)
        self.chk_same_chu_address.toggled.connect(self._toggle_thua_addr_sync)
        f_addr.addRow(self.chk_same_chu_address)

        self.txt_thua_sonha = QLineEdit()
        self._register_input(89, self.txt_thua_sonha)

        self.txt_thua_to = QLineEdit()
        self.txt_thua_to.textChanged.connect(self._update_thua_full_address)
        self._register_input(90, self.txt_thua_to)

        self.cmb_thua_xa = SearchableComboBox()
        self._populate_communes(self.cmb_thua_xa)
        self.cmb_thua_xa.currentIndexChanged.connect(self._on_thua_commune_changed)
        self._register_input(91, self.cmb_thua_xa)

        self.txt_thua_xa_huyen_tinh = QLineEdit()
        self.txt_thua_xa_huyen_tinh.setPlaceholderText("Xã/Phường, Quận/Huyện, Tỉnh/TP")
        self.txt_thua_xa_huyen_tinh.textChanged.connect(self._update_thua_full_address)
        self._register_input(92, self.txt_thua_xa_huyen_tinh)

        self.txt_thua_full_addr = QLineEdit()
        self._register_input(94, self.txt_thua_full_addr)

        # Nhóm Đơn & Quản lý (Cols 95-98)
        self.chk_has_quan_ly = QCheckBox("Có thông tin Đơn & Quản lý (Cols 95-98)")
        self.chk_has_quan_ly.toggled.connect(self._toggle_quan_ly_fields)
        f_addr.addRow(self.chk_has_quan_ly)

        self.txt_thua_ma_don = QLineEdit()
        self._register_input(95, self.txt_thua_ma_don)

        self.txt_thua_ngay_dangky = QLineEdit()
        self._register_input(96, self.txt_thua_ngay_dangky)

        self.cmb_hinh_thuc_sd = SearchableComboBox()
        self.cmb_hinh_thuc_sd.addItem("[Không chọn]", "")
        self.cmb_hinh_thuc_sd.addItem("0 - Sử dụng riêng", "0")
        self.cmb_hinh_thuc_sd.addItem("1 - Sử dụng chung", "1")
        self.cmb_hinh_thuc_sd.addItem("2 - Cả riêng và chung", "2")
        self._register_input(97, self.cmb_hinh_thuc_sd)

        self.cmb_trang_thai_thua = SearchableComboBox()
        self.cmb_trang_thai_thua.addItem("[Không chọn]", "")
        if self.master_data.land_status_list:
            for code, name in self.master_data.land_status_list:
                self.cmb_trang_thai_thua.addItem(f"{code} - {name}", code)
        else:
            self.cmb_trang_thai_thua.addItem("5 - Đã cấp GCN", "5")
            self.cmb_trang_thai_thua.addItem("4 - Đã đăng ký, đủ điều kiện cấp GCN", "4")
        self._register_input(98, self.cmb_trang_thai_thua)

        f_addr.addRow("Số nhà (89):", self.txt_thua_sonha)
        f_addr.addRow("Tổ/Khu (90):", self.txt_thua_to)
        f_addr.addRow("Mã Xã (91):", self.cmb_thua_xa)
        f_addr.addRow("Xã/Huyện (92):", self.txt_thua_xa_huyen_tinh)
        f_addr.addRow("Đ/C đầy đủ (94):", self.txt_thua_full_addr)
        f_addr.addRow("Mã đơn (95):", self.txt_thua_ma_don)
        f_addr.addRow("Ngày ĐK (96):", self.txt_thua_ngay_dangky)
        f_addr.addRow("Hình thức (97):", self.cmb_hinh_thuc_sd)
        f_addr.addRow("Trạng thái (98):", self.cmb_trang_thai_thua)
        self._toggle_quan_ly_fields(False)
        root_vbox.addWidget(grp_addr)

        return self._create_scroll_area(container)

    def _auto_sync_dt_phaply(self, text: str):
        if not self.txt_dt_phaply.text() or self.txt_dt_phaply.text() == text[:-1]:
            self.txt_dt_phaply.setText(text)
        if not self.txt_mdsd1_dt.text():
            self.txt_mdsd1_dt.setText(text)

    def _on_mdsd1_changed(self, idx: int):
        code = self.cmb_mdsd1.currentData()
        if code:
            self.txt_mdsd1_kh.setText(str(code))

    def _on_mdsd2_changed(self, idx: int):
        code = self.cmb_mdsd2.currentData()
        if code:
            self.txt_mdsd2_kh.setText(str(code))

    def _on_mdsd3_changed(self, idx: int):
        code = self.cmb_mdsd3.currentData()
        if code:
            self.txt_mdsd3_kh.setText(str(code))

    def _on_mdsd1_origin_changed(self, *args):
        code59 = str(self.cmb_mdsd1_nguon_goc.currentData() or "")
        code60 = str(self.cmb_mdsd1_ma_nguon_goc.currentData() or "")
        name59 = self.master_data.land_use_origins_by_code.get(code59, "")
        name60 = self.master_data.land_use_origins_by_code.get(code60, "")
        parts = []
        if name59:
            parts.append(name59)
        if name60:
            parts.append(name60)
        self.txt_mdsd1_nguon_goc_ct.setText(" ".join(parts))

    def _on_mdsd2_origin_changed(self, *args):
        code67 = str(self.cmb_mdsd2_nguon_goc.currentData() or "")
        code68 = str(self.cmb_mdsd2_ma_nguon_goc.currentData() or "")
        name67 = self.master_data.land_use_origins_by_code.get(code67, "")
        name68 = self.master_data.land_use_origins_by_code.get(code68, "")
        parts = []
        if name67:
            parts.append(name67)
        if name68:
            parts.append(name68)
        self.txt_mdsd2_nguon_goc_ct.setText(" ".join(parts))

    def _on_mdsd3_origin_changed(self, *args):
        code75 = str(self.cmb_mdsd3_nguon_goc.currentData() or "")
        code76 = str(self.cmb_mdsd3_ma_nguon_goc.currentData() or "")
        name75 = self.master_data.land_use_origins_by_code.get(code75, "")
        name76 = self.master_data.land_use_origins_by_code.get(code76, "")
        parts = []
        if name75:
            parts.append(name75)
        if name76:
            parts.append(name76)
        self.txt_mdsd3_nguon_goc_ct.setText(" ".join(parts))

    def _toggle_mdsd2_fields(self, enabled: bool):
        for col in range(62, 70):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_mdsd3_fields(self, enabled: bool):
        for col in range(70, 78):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_quan_ly_fields(self, enabled: bool):
        for col in (95, 96, 97, 98):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)
        if enabled and not self.txt_thua_ma_don.text():
            self._auto_sync_ma_don(self.txt_serial.text())

    def _toggle_thua_addr_sync(self, checked: bool):
        for col in (89, 90, 91, 92, 94):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(not checked)
        if checked:
            self._sync_thua_addr_from_chu()

    def _sync_thua_addr_from_chu(self):
        if self.chk_same_chu_address.isChecked():
            self.txt_thua_sonha.setText(self.txt_chu_sonha.text())
            self.txt_thua_to.setText(self.txt_chu_to.text())
            self.cmb_thua_xa.setCurrentIndex(self.cmb_chu_xa.currentIndex())
            self.txt_thua_xa_huyen_tinh.setText(self.txt_chu_xa_huyen_tinh.text())
            self.txt_thua_full_addr.setText(self.txt_chu_full_addr.text())

    def _on_thua_commune_changed(self, idx: int):
        data = self.cmb_thua_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.txt_thua_xa_huyen_tinh.setText(data.full_location)
            self._update_thua_full_address()
            # Auto fill measuring unit & completion date from QNH_ThongTinDoDac.xlsx
            self._auto_fill_measurement(data.name_3cap, data.district)

    def _auto_fill_measurement(self, commune_name: str, district: str):
        meas = self.master_data.find_measurement(commune_name, district)
        if meas:
            if not self.cmb_don_vi_do.currentText():
                self.cmb_don_vi_do.setCurrentText(meas.measuring_unit)
            if not self.txt_ngay_hoan_thanh.text():
                self.txt_ngay_hoan_thanh.setText(meas.completion_date)

    def _update_thua_full_address(self):
        to = self.txt_thua_to.text().strip()
        location = self.txt_thua_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_thua_full_addr.setText(full)

    # -------------------------------------------------------------
    # TAB 5: NVTC & HẠN CHẾ (Cols 111-133)
    # -------------------------------------------------------------
    def _create_tab_nvtc(self) -> QWidget:
        container = QWidget()
        root_vbox = QVBoxLayout(container)
        root_vbox.setContentsMargins(2, 2, 2, 2)
        root_vbox.setSpacing(4)

        # Hạn chế quyền (Cols 111-117)
        grp_hc = QGroupBox("Hạn chế quyền sử dụng đất (Cols 111-117)")
        f_hc = QFormLayout(grp_hc)
        self._setup_form_layout(f_hc)

        self.chk_has_han_che = QCheckBox("Có Hạn chế quyền")
        self.chk_has_han_che.setStyleSheet("font-weight: bold; color: #e65100;")
        self.chk_has_han_che.toggled.connect(self._toggle_han_che_fields)
        f_hc.addRow(self.chk_has_han_che)

        self.txt_hc_dt = QLineEdit()
        self._register_input(111, self.txt_hc_dt)

        self.txt_hc_hinh_thuc = QLineEdit()
        self._register_input(112, self.txt_hc_hinh_thuc)

        self.txt_hc_so_vb = QLineEdit()
        self._register_input(113, self.txt_hc_so_vb)

        self.txt_hc_ngay_bh = QLineEdit()
        self._register_input(114, self.txt_hc_ngay_bh)

        self.txt_hc_cq_bh = QLineEdit()
        self._register_input(115, self.txt_hc_cq_bh)

        self.txt_hc_noi_dung = QPlainTextEdit()
        self.txt_hc_noi_dung.setMaximumHeight(50)
        self._register_input(116, self.txt_hc_noi_dung)

        self.cmb_hc_loai = SearchableComboBox()
        self.cmb_hc_loai.addItem("[Không chọn]", "")
        for r in self.master_data.restriction_types:
            self.cmb_hc_loai.addItem(r, r)
        self._register_input(117, self.cmb_hc_loai)

        f_hc.addRow("DT hạn chế (111):", self.txt_hc_dt)
        f_hc.addRow("Hình thức (112):", self.txt_hc_hinh_thuc)
        f_hc.addRow("Số văn bản (113):", self.txt_hc_so_vb)
        f_hc.addRow("Ngày BH (114):", self.txt_hc_ngay_bh)
        f_hc.addRow("Cơ quan BH (115):", self.txt_hc_cq_bh)
        f_hc.addRow("Nội dung (116):", self.txt_hc_noi_dung)
        f_hc.addRow("Loại HC (117):", self.cmb_hc_loai)
        self._toggle_han_che_fields(False)
        root_vbox.addWidget(grp_hc)

        # Nghĩa vụ tài chính (Cols 118-123)
        grp_nvtc = QGroupBox("Nghĩa vụ tài chính (Cols 118-123)")
        f_nvtc = QFormLayout(grp_nvtc)
        self._setup_form_layout(f_nvtc)

        self.chk_has_nvtc = QCheckBox("Có Nghĩa vụ tài chính")
        self.chk_has_nvtc.setStyleSheet("font-weight: bold; color: #1976d2;")
        self.chk_has_nvtc.toggled.connect(self._toggle_nvtc_fields)
        f_nvtc.addRow(self.chk_has_nvtc)

        self.cmb_nvtc_loai = SearchableComboBox()
        self.cmb_nvtc_loai.addItem("[Không chọn]", "")
        for n in self.master_data.nvtc_types:
            self.cmb_nvtc_loai.addItem(n, n)
        self.cmb_nvtc_loai.addItem("Lệ phí trước bạ;Thuế thu nhập từ chuyển nhượng bất động sản", "Lệ phí trước bạ;Thuế thu nhập từ chuyển nhượng bất động sản")
        self._register_input(118, self.cmb_nvtc_loai)

        self.txt_nvtc_tien = QLineEdit()
        self.txt_nvtc_tien.setPlaceholderText("Ví dụ: 6000000;24000000")
        self._register_input(119, self.txt_nvtc_tien)

        self.txt_nvtc_tien_mg = QLineEdit()
        self._register_input(120, self.txt_nvtc_tien_mg)

        self.txt_nvtc_tien_no = QLineEdit()
        self._register_input(121, self.txt_nvtc_tien_no)

        self.txt_nvtc_ngay_bd = QLineEdit()
        self._register_input(122, self.txt_nvtc_ngay_bd)

        self.txt_nvtc_ngay_ht = QLineEdit()
        self._register_input(123, self.txt_nvtc_ngay_ht)

        f_nvtc.addRow("Loại NVTC (118):", self.cmb_nvtc_loai)
        f_nvtc.addRow("Tổng tiền (119):", self.txt_nvtc_tien)
        f_nvtc.addRow("Tiền MG (120):", self.txt_nvtc_tien_mg)
        f_nvtc.addRow("Tiền nợ (121):", self.txt_nvtc_tien_no)
        f_nvtc.addRow("Ngày BĐ (122):", self.txt_nvtc_ngay_bd)
        f_nvtc.addRow("Ngày HT (123):", self.txt_nvtc_ngay_ht)
        self._toggle_nvtc_fields(False)
        root_vbox.addWidget(grp_nvtc)

        # Miễn giảm NVTC
        grp_mg = QGroupBox("Miễn giảm NVTC (Cols 124-128)")
        f_mg = QFormLayout(grp_mg)
        self._setup_form_layout(f_mg)
        self.chk_has_mg = QCheckBox("Có Miễn giảm NVTC")
        self.chk_has_mg.toggled.connect(self._toggle_mg_fields)
        f_mg.addRow(self.chk_has_mg)

        self.txt_mg_che_do = QLineEdit()
        self._register_input(124, self.txt_mg_che_do)
        self.txt_mg_tien = QLineEdit()
        self._register_input(125, self.txt_mg_tien)
        self.txt_mg_so_vb = QLineEdit()
        self._register_input(126, self.txt_mg_so_vb)
        self.txt_mg_ngay_bh = QLineEdit()
        self._register_input(127, self.txt_mg_ngay_bh)
        self.txt_mg_cq_bh = QLineEdit()
        self._register_input(128, self.txt_mg_cq_bh)

        f_mg.addRow("Chế độ MG (124):", self.txt_mg_che_do)
        f_mg.addRow("Số tiền MG (125):", self.txt_mg_tien)
        f_mg.addRow("Số văn bản (126):", self.txt_mg_so_vb)
        f_mg.addRow("Ngày BH (127):", self.txt_mg_ngay_bh)
        f_mg.addRow("Cơ quan BH (128):", self.txt_mg_cq_bh)
        self._toggle_mg_fields(False)
        root_vbox.addWidget(grp_mg)

        # Nợ NVTC
        grp_no = QGroupBox("Nợ NVTC (Cols 129-133)")
        f_no = QFormLayout(grp_no)
        self._setup_form_layout(f_no)
        self.chk_has_no = QCheckBox("Có Nợ NVTC")
        self.chk_has_no.toggled.connect(self._toggle_no_fields)
        f_no.addRow(self.chk_has_no)

        self.txt_no_loai = QLineEdit()
        self._register_input(129, self.txt_no_loai)
        self.txt_no_tien = QLineEdit()
        self._register_input(130, self.txt_no_tien)
        self.txt_no_so_vb = QLineEdit()
        self._register_input(131, self.txt_no_so_vb)
        self.txt_no_ngay_bh = QLineEdit()
        self._register_input(132, self.txt_no_ngay_bh)
        self.txt_no_cq_bh = QLineEdit()
        self._register_input(133, self.txt_no_cq_bh)

        f_no.addRow("Loại nợ (129):", self.txt_no_loai)
        f_no.addRow("Số tiền nợ (130):", self.txt_no_tien)
        f_no.addRow("Số văn bản (131):", self.txt_no_so_vb)
        f_no.addRow("Ngày BH (132):", self.txt_no_ngay_bh)
        f_no.addRow("Cơ quan BH (133):", self.txt_no_cq_bh)
        self._toggle_no_fields(False)
        root_vbox.addWidget(grp_no)

        return self._create_scroll_area(container)

    def _toggle_han_che_fields(self, enabled: bool):
        for col in range(111, 118):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_nvtc_fields(self, enabled: bool):
        for col in range(118, 124):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_mg_fields(self, enabled: bool):
        for col in range(124, 129):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_no_fields(self, enabled: bool):
        for col in range(129, 134):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    # -------------------------------------------------------------
    # TAB 6: TÀI SẢN & LƯU KHO (Cols 134-186)
    # -------------------------------------------------------------
    def _create_tab_tai_san_va_khac(self) -> QWidget:
        container = QWidget()
        root_vbox = QVBoxLayout(container)
        root_vbox.setContentsMargins(2, 2, 2, 2)
        root_vbox.setSpacing(4)

        # Nhà ở riêng lẻ (Cols 134-141)
        grp_nha = QGroupBox("Nhà ở riêng lẻ (Cols 134-141)")
        f_nha = QFormLayout(grp_nha)
        self._setup_form_layout(f_nha)
        self.chk_has_nha = QCheckBox("Có Nhà ở riêng lẻ")
        self.chk_has_nha.toggled.connect(self._toggle_nha_fields)
        f_nha.addRow(self.chk_has_nha)

        self.txt_nha_dt_xd = QLineEdit()
        self._register_input(134, self.txt_nha_dt_xd)
        self.txt_nha_dt_san = QLineEdit()
        self._register_input(135, self.txt_nha_dt_san)
        self.txt_nha_ket_cau = QLineEdit()
        self._register_input(136, self.txt_nha_ket_cau)
        self.txt_nha_so_tang = QLineEdit()
        self._register_input(137, self.txt_nha_so_tang)
        self.txt_nha_cap_hang = SearchableComboBox()
        self.txt_nha_cap_hang.addItem("[Không chọn]", "")
        for r in self.master_data.rank_types:
            self.txt_nha_cap_hang.addItem(r, r)
        self._register_input(138, self.txt_nha_cap_hang)
        self.txt_nha_ht_so_huu = QLineEdit()
        self._register_input(139, self.txt_nha_ht_so_huu)
        self.txt_nha_thoi_han = QLineEdit()
        self._register_input(140, self.txt_nha_thoi_han)
        self.txt_nha_dia_chi = QLineEdit()
        self._register_input(141, self.txt_nha_dia_chi)

        f_nha.addRow("DT xây dựng (134):", self.txt_nha_dt_xd)
        f_nha.addRow("DT sàn (135):", self.txt_nha_dt_san)
        f_nha.addRow("Kết cấu (136):", self.txt_nha_ket_cau)
        f_nha.addRow("Số tầng (137):", self.txt_nha_so_tang)
        f_nha.addRow("Cấp hạng (138):", self.txt_nha_cap_hang)
        f_nha.addRow("Hình thức SH (139):", self.txt_nha_ht_so_huu)
        f_nha.addRow("Thời hạn SH (140):", self.txt_nha_thoi_han)
        f_nha.addRow("Địa chỉ nhà (141):", self.txt_nha_dia_chi)
        self._toggle_nha_fields(False)
        root_vbox.addWidget(grp_nha)

        # Công trình xây dựng (Cols 142-154)
        grp_ct = QGroupBox("Công trình xây dựng khác (Cols 142-154)")
        f_ct = QFormLayout(grp_ct)
        self._setup_form_layout(f_ct)
        self.chk_has_ctxd = QCheckBox("Có Công trình xây dựng")
        self.chk_has_ctxd.toggled.connect(self._toggle_ctxd_fields)
        f_ct.addRow(self.chk_has_ctxd)

        self.txt_ct_ten = QLineEdit()
        self._register_input(142, self.txt_ct_ten)
        self.txt_ct_dt_xd = QLineEdit()
        self._register_input(143, self.txt_ct_dt_xd)
        self.txt_ct_dt_san = QLineEdit()
        self._register_input(144, self.txt_ct_dt_san)
        self.txt_ct_ket_cau = QLineEdit()
        self._register_input(145, self.txt_ct_ket_cau)
        self.txt_ct_cong_nang = QLineEdit()
        self._register_input(146, self.txt_ct_cong_nang)

        f_ct.addRow("Tên công trình (142):", self.txt_ct_ten)
        f_ct.addRow("DT xây dựng (143):", self.txt_ct_dt_xd)
        f_ct.addRow("DT sàn (144):", self.txt_ct_dt_san)
        f_ct.addRow("Kết cấu (145):", self.txt_ct_ket_cau)
        f_ct.addRow("Công năng (146):", self.txt_ct_cong_nang)
        self._toggle_ctxd_fields(False)
        root_vbox.addWidget(grp_ct)

        # Thửa đất cũ (Cols 169-178)
        grp_cu = QGroupBox("Thông tin thửa đất cũ (Cols 169-178)")
        f_cu = QFormLayout(grp_cu)
        self._setup_form_layout(f_cu)
        self.chk_has_thua_cu = QCheckBox("Có Thửa đất cũ")
        self.chk_has_thua_cu.toggled.connect(self._toggle_thua_cu_fields)
        f_cu.addRow(self.chk_has_thua_cu)

        self.txt_cu_so_thua = QLineEdit()
        self._register_input(169, self.txt_cu_so_thua)
        self.txt_cu_so_to = QLineEdit()
        self._register_input(170, self.txt_cu_so_to)
        self.txt_cu_dt = QLineEdit()
        self._register_input(171, self.txt_cu_dt)
        self.txt_cu_loai_dat = QLineEdit()
        self._register_input(172, self.txt_cu_loai_dat)

        f_cu.addRow("Số thửa cũ (169):", self.txt_cu_so_thua)
        f_cu.addRow("Số tờ cũ (170):", self.txt_cu_so_to)
        f_cu.addRow("Diện tích cũ (171):", self.txt_cu_dt)
        f_cu.addRow("Loại đất cũ (172):", self.txt_cu_loai_dat)
        self._toggle_thua_cu_fields(False)
        root_vbox.addWidget(grp_cu)

        # Vị trí lưu kho & Hồ sơ quét (Cols 179-186)
        grp_kho = QGroupBox("Vị trí lưu kho vật lý & HSQ (Cols 179-186)")
        f_kho = QFormLayout(grp_kho)
        self._setup_form_layout(f_kho)

        self.txt_kho = QLineEdit()
        self._register_input(179, self.txt_kho)
        self.txt_gia = QLineEdit()
        self._register_input(180, self.txt_gia)
        self.txt_ke = QLineEdit()
        self._register_input(181, self.txt_ke)
        self.txt_ngan = QLineEdit()
        self._register_input(182, self.txt_ngan)
        self.txt_thu_muc_hsq = QLineEdit()
        self._register_input(183, self.txt_thu_muc_hsq)
        self.txt_dot_giao_nop = QLineEdit()
        self._register_input(184, self.txt_dot_giao_nop)
        self.txt_tt_kiem_tra = QLineEdit()
        self._register_input(185, self.txt_tt_kiem_tra)
        self.txt_ghi_chu_giao_nop = QLineEdit()
        self._register_input(186, self.txt_ghi_chu_giao_nop)

        f_kho.addRow("Kho (179):", self.txt_kho)
        f_kho.addRow("Giá (180):", self.txt_gia)
        f_kho.addRow("Kệ (181):", self.txt_ke)
        f_kho.addRow("Ngăn (182):", self.txt_ngan)
        f_kho.addRow("Thư mục HSQ (183):", self.txt_thu_muc_hsq)
        f_kho.addRow("Đợt nộp (184):", self.txt_dot_giao_nop)
        f_kho.addRow("TT kiểm tra (185):", self.txt_tt_kiem_tra)
        f_kho.addRow("Ghi chú (186):", self.txt_ghi_chu_giao_nop)
        root_vbox.addWidget(grp_kho)

        return self._create_scroll_area(container)

    def _toggle_nha_fields(self, enabled: bool):
        for col in range(134, 142):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_ctxd_fields(self, enabled: bool):
        for col in range(142, 147):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    def _toggle_thua_cu_fields(self, enabled: bool):
        for col in range(169, 173):
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    # -------------------------------------------------------------
    # HELPER POPULATORS & COMMUNE ADDR UPDATERS
    # -------------------------------------------------------------
    def _populate_communes(self, combo: QComboBox):
        combo.clear()
        combo.addItem("[Không chọn]", None)
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

    def _on_chu_commune_changed(self, idx: int):
        data = self.cmb_chu_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.last_commune_code = data.code_3cap
            self.txt_chu_xa_huyen_tinh.setText(data.full_location)
            self._update_chu_full_address()
            if self.chk_has_spouse.isChecked() and not self.txt_vo_xa_huyen_tinh.text():
                self.cmb_vo_xa.setCurrentIndex(idx)
            if self.chk_same_chu_address.isChecked():
                self.cmb_thua_xa.setCurrentIndex(idx)

    def _update_chu_full_address(self):
        to = self.txt_chu_to.text().strip()
        location = self.txt_chu_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_chu_full_addr.setText(full)
        if self.chk_same_chu_address.isChecked():
            self._sync_thua_addr_from_chu()

    def _on_chu_full_addr_changed(self, text: str):
        if self.chk_same_chu_address.isChecked():
            self.txt_thua_full_addr.setText(text)

    def _on_vo_commune_changed(self, idx: int):
        data = self.cmb_vo_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.txt_vo_xa_huyen_tinh.setText(data.full_location)
            self._update_vo_full_address()

    def _update_vo_full_address(self):
        to = self.txt_vo_to.text().strip()
        location = self.txt_vo_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_vo_full_addr.setText(full)

    # -------------------------------------------------------------
    # READ / WRITE FORM DATA (Directly from visible inputs)
    # -------------------------------------------------------------
    def get_attr_dict(self) -> Dict[int, Any]:
        """Collects values directly from all visible inputs in the form."""
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

        # Gender conversion: Nam -> 1, Nữ -> 0
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

        # Specific field cleans
        if not self.chk_has_spouse.isChecked():
            for c in range(26, 43):
                data[c] = ""

        if not self.chk_has_mdsd2.isChecked():
            for c in range(62, 70):
                data[c] = ""

        if not self.chk_has_mdsd3.isChecked():
            for c in range(70, 78):
                data[c] = ""

        if not self.chk_has_quan_ly.isChecked():
            for c in (95, 96, 97, 98):
                data[c] = ""

        if not self.chk_has_han_che.isChecked():
            for c in range(111, 118):
                data[c] = ""

        if not self.chk_has_nvtc.isChecked():
            for c in range(118, 124):
                data[c] = ""

        if not self.chk_has_mg.isChecked():
            for c in range(124, 129):
                data[c] = ""

        if not self.chk_has_no.isChecked():
            for c in range(129, 134):
                data[c] = ""

        if not self.chk_has_nha.isChecked():
            for c in range(134, 142):
                data[c] = ""

        if not self.chk_has_ctxd.isChecked():
            for c in range(142, 155):
                data[c] = ""

        if not self.chk_has_thua_cu.isChecked():
            for c in range(169, 179):
                data[c] = ""

        return data

    def load_attr_dict(self, data: Dict[int, Any], serial: str):
        """Populates form directly from dictionary and serial name."""
        self.txt_serial.setText(serial)
        self.txt_thu_muc_hsq.setText(serial)

        for col, widget in self.field_inputs.items():
            val = str(data.get(col, "") or "")

            if isinstance(widget, QLineEdit):
                if not val:
                    if col == 48:
                        widget.setText("Toàn đạc điện tử")
                    elif col == 49:
                        widget.setText("Cao")
                    elif col == 45:
                        widget.setText("500")
                    elif col == 58:
                        widget.setText("Lâu dài")
                    else:
                        widget.setText("")
                else:
                    widget.setText(val)
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(val)
            elif isinstance(widget, QComboBox):
                if not val:
                    if col in (25, 42):
                        widget.setCurrentText("Viet Nam")
                    elif col == 41:
                        widget.setCurrentText("Không rõ")
                    elif col == 24:
                        widget.setCurrentText("Kinh")
                    elif col == 46:
                        widget.setCurrentText("1 - Bản đồ địa chính (VN2000)")
                    elif col == 51:
                        widget.setCurrentText("A - Đã cấp GCN, không có tài sản")
                    elif col == 57:
                        widget.setCurrentText("0 - Sử dụng riêng")
                    elif col == 99:
                        widget.setCurrentText("Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP")
                    else:
                        widget.setCurrentIndex(0)
                    continue

                if col in (25, 42) and val.lower() in ("viet nam", "việt nam", "vietnam"):
                    widget.setCurrentText("Viet Nam")
                    continue

                if col in [20, 37, 91]:
                    matched = False
                    for i in range(widget.count()):
                        c_info = widget.itemData(i)
                        if isinstance(c_info, CommuneInfo) and c_info.code_3cap == val:
                            widget.setCurrentIndex(i)
                            matched = True
                            break
                    if not matched:
                        widget.setCurrentText(val)
                elif col in [6, 7, 8, 10, 13, 27, 30, 46, 51, 54, 57, 59, 60, 62, 65, 67, 68, 70, 73, 75, 76, 97, 98, 104, 105, 117]:
                    # Normalize ID type abbreviations
                    if col in (13, 30):
                        if "chứng minh" in val.lower():
                            val = "CMND"
                        elif "căn cước" in val.lower():
                            val = "CCCD"
                    matched = False
                    for i in range(widget.count()):
                        item_d = str(widget.itemData(i) or "")
                        if item_d.lower() == val.lower():
                            widget.setCurrentIndex(i)
                            matched = True
                            break
                    if not matched:
                        widget.setCurrentText(val)
                else:
                    widget.setCurrentText(val)

        # Spouse toggle
        if data.get(26):
            self.chk_has_spouse.setChecked(True)
            self._toggle_spouse_fields(True)
        else:
            self.chk_has_spouse.setChecked(False)
            self._toggle_spouse_fields(False)

        # MĐSD 2 toggle
        if data.get(62) or data.get(64):
            self.chk_has_mdsd2.setChecked(True)
            self._toggle_mdsd2_fields(True)
        else:
            self.chk_has_mdsd2.setChecked(False)
            self._toggle_mdsd2_fields(False)

        # MĐSD 3 toggle
        if data.get(70) or data.get(72):
            self.chk_has_mdsd3.setChecked(True)
            self._toggle_mdsd3_fields(True)
        else:
            self.chk_has_mdsd3.setChecked(False)
            self._toggle_mdsd3_fields(False)

        # Quản lý toggle
        if data.get(95) or data.get(96) or data.get(97) or data.get(98):
            self.chk_has_quan_ly.setChecked(True)
            self._toggle_quan_ly_fields(True)
        else:
            self.chk_has_quan_ly.setChecked(False)
            self._toggle_quan_ly_fields(False)

        # Hạn chế toggle
        if data.get(111) or data.get(116) or data.get(117):
            self.chk_has_han_che.setChecked(True)
            self._toggle_han_che_fields(True)
        else:
            self.chk_has_han_che.setChecked(False)
            self._toggle_han_che_fields(False)

        # NVTC toggle
        if data.get(118) or data.get(119):
            self.chk_has_nvtc.setChecked(True)
            self._toggle_nvtc_fields(True)
        else:
            self.chk_has_nvtc.setChecked(False)
            self._toggle_nvtc_fields(False)

        # MG toggle
        if data.get(124) or data.get(125):
            self.chk_has_mg.setChecked(True)
            self._toggle_mg_fields(True)
        else:
            self.chk_has_mg.setChecked(False)
            self._toggle_mg_fields(False)

        # Nợ toggle
        if data.get(129) or data.get(130):
            self.chk_has_no.setChecked(True)
            self._toggle_no_fields(True)
        else:
            self.chk_has_no.setChecked(False)
            self._toggle_no_fields(False)

        # Nhà toggle
        if data.get(134) or data.get(135):
            self.chk_has_nha.setChecked(True)
            self._toggle_nha_fields(True)
        else:
            self.chk_has_nha.setChecked(False)
            self._toggle_nha_fields(False)

        # CTXD toggle
        if data.get(142) or data.get(143):
            self.chk_has_ctxd.setChecked(True)
            self._toggle_ctxd_fields(True)
        else:
            self.chk_has_ctxd.setChecked(False)
            self._toggle_ctxd_fields(False)

        # Thửa cũ toggle
        if data.get(169) or data.get(170):
            self.chk_has_thua_cu.setChecked(True)
            self._toggle_thua_cu_fields(True)
        else:
            self.chk_has_thua_cu.setChecked(False)
            self._toggle_thua_cu_fields(False)
