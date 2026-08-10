"""
Form Widget hosting 5 tabbed sections mapping fields to 186 columns.
Supports keyboard navigation, auto-defaults, sticky addresses, persistent crop OCR field memory, and highlighting.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout, 
    QLineEdit, QComboBox, QCheckBox, QLabel, QGroupBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from scan_attribute.core.data_models import MasterDataManager, CommuneInfo


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
        layout.setContentsMargins(5, 5, 5, 5)

        self.tab_widget = QTabWidget()

        # Tab 1: GCN & Chung
        self.tab_widget.addTab(self._create_tab_gcn(), "1. GCN & Chung")
        # Tab 2: Chủ sử dụng
        self.tab_widget.addTab(self._create_tab_chu(), "2. Chủ Sử Dụng")
        # Tab 3: Vợ (Chồng)
        self.tab_widget.addTab(self._create_tab_vo_chong(), "3. Vợ / Chồng")
        # Tab 4: Thửa đất & MĐSD
        self.tab_widget.addTab(self._create_tab_thua_dat(), "4. Thửa Đất & MĐSD")
        # Tab 5: Ghi chú & NVTC
        self.tab_widget.addTab(self._create_tab_ghi_chu(), "5. Ghi Chú & NVTC")

        layout.addWidget(self.tab_widget)

        # Bottom Action Row
        btn_row = QHBoxLayout()
        self.lbl_status = QLabel("📍 Đang nhắm ô nhập liệu: Mã vạch")
        self.lbl_status.setStyleSheet("color: #1565c0; font-weight: bold; font-size: 12px;")
        
        self.btn_save = QPushButton("💾 Lưu & Tiếp Theo (Ctrl+Enter)")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 6px 16px;
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
            # Check if watched is one of our input fields
            target = watched
            for col, w in self.field_inputs.items():
                if w == watched or (isinstance(w, QComboBox) and w.lineEdit() == watched):
                    self.active_input_widget = w
                    self._highlight_active_field(w, col)
                    break
        return super().eventFilter(watched, event)

    def _highlight_active_field(self, target_widget, col_idx: int):
        field_names = {
            2: "Số Serial", 3: "Mã HS Gốc", 4: "Mã vạch",
            9: "Họ tên Chủ đất", 14: "CCCD/Số GT Chủ", 19: "Tổ/Khu", 20: "Mã Xã",
            26: "Họ tên Vợ/Chồng", 31: "CCCD Vợ/Chồng", 36: "Tổ/Khu Vợ/Chồng",
            43: "Số thửa", 44: "Số tờ", 52: "Diện tích bản đồ", 54: "MĐSD 1", 56: "Diện tích 1",
            62: "MĐSD 2", 64: "Diện tích 2", 100: "Số vào sổ", 102: "Ngày ký", 110: "Ghi chú T2"
        }
        name = field_names.get(col_idx, f"Cột {col_idx}")
        self.lbl_status.setText(f"📍 Đang nhắm ô nhập liệu: [{name}] (Kéo chuột bên PDF sẽ tự dán vào ô này)")

        for w in self.field_inputs.values():
            if isinstance(w, QLineEdit):
                if w == target_widget:
                    w.setStyleSheet("border: 2px solid #1565c0; background-color: #e3f2fd; font-weight: bold;")
                else:
                    w.setStyleSheet("")
            elif isinstance(w, QPlainTextEdit):
                if w == target_widget:
                    w.setStyleSheet("border: 2px solid #1565c0; background-color: #e3f2fd; font-weight: bold;")
                else:
                    w.setStyleSheet("")

    def set_ocr_text_to_active_field(self, text: str):
        """Pastes OCR text into active focused input widget and updates clipboard."""
        if not text:
            return
        clean_text = text.strip()

        # 1. ALWAYS copy to System Clipboard
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_text)

        # 2. Pick target widget (use persistent active_input_widget or fallback to txt_barcode)
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
        return widget

    # -------------------------------------------------------------
    # TAB 1: GCN & CHUNG
    # -------------------------------------------------------------
    def _create_tab_gcn(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)

        self.txt_serial = QLineEdit()
        self._register_input(2, self.txt_serial)

        self.txt_ma_hs = QLineEdit()
        self._register_input(3, self.txt_ma_hs)

        self.txt_barcode = QLineEdit()
        self.txt_barcode.setPlaceholderText("Ví dụ: 0667320081887")
        self._register_input(4, self.txt_barcode)

        # Set barcode as initial default active field
        self.active_input_widget = self.txt_barcode

        form.addRow("Số Serial (Col 2):", self.txt_serial)
        form.addRow("Mã HS Gốc (Col 3):", self.txt_ma_hs)
        form.addRow("Mã vạch (Col 4):", self.txt_barcode)

        scroll.setWidget(container)
        return scroll

    # -------------------------------------------------------------
    # TAB 2: CHỦ SỬ DỤNG
    # -------------------------------------------------------------
    def _create_tab_chu(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)

        self.txt_chu_name = QLineEdit()
        self._register_input(9, self.txt_chu_name)

        self.cmb_chu_gender = QComboBox()
        self.cmb_chu_gender.addItems(["Nam", "Nữ"])
        self._register_input(10, self.cmb_chu_gender)

        self.txt_chu_dob = QLineEdit()
        self.txt_chu_dob.setPlaceholderText("Năm sinh (Ví dụ: 1975)")
        self._register_input(12, self.txt_chu_dob)

        self.cmb_chu_id_type = QComboBox()
        self.cmb_chu_id_type.addItems(self.master_data.id_types)
        self._register_input(13, self.cmb_chu_id_type)

        self.txt_chu_id_num = QLineEdit()
        self.txt_chu_id_num.setPlaceholderText("Số CCCD/CMND 12 số")
        self._register_input(14, self.txt_chu_id_num)

        self.txt_chu_to = QLineEdit()
        self.txt_chu_to.setPlaceholderText("Tổ / Khu dân phố (Ví dụ: Khu 5)")
        self.txt_chu_to.textChanged.connect(self._update_chu_full_address)
        self._register_input(19, self.txt_chu_to)

        # Commune dropdown
        self.cmb_chu_xa = QComboBox()
        self.cmb_chu_xa.setEditable(True)
        self._populate_communes(self.cmb_chu_xa)
        self.cmb_chu_xa.currentIndexChanged.connect(self._on_chu_commune_changed)
        self._register_input(20, self.cmb_chu_xa)

        self.txt_chu_xa_huyen_tinh = QLineEdit()
        self.txt_chu_xa_huyen_tinh.setReadOnly(True)
        self._register_input(21, self.txt_chu_xa_huyen_tinh)

        self.txt_chu_full_addr = QLineEdit()
        self._register_input(22, self.txt_chu_full_addr)

        self.cmb_chu_dantoc = QComboBox()
        self.cmb_chu_dantoc.setEditable(True)
        self.cmb_chu_dantoc.addItems(self.master_data.ethnicities)
        self.cmb_chu_dantoc.setCurrentText("Kinh")
        self._register_input(24, self.cmb_chu_dantoc)

        self.cmb_chu_quoctich = QComboBox()
        self.cmb_chu_quoctich.setEditable(True)
        self.cmb_chu_quoctich.addItems(self.master_data.nationalities)
        self.cmb_chu_quoctich.setCurrentText("Việt Nam")
        self._register_input(25, self.cmb_chu_quoctich)

        form.addRow("Họ và tên chủ đất (Col 9):", self.txt_chu_name)
        form.addRow("Giới tính (Col 10):", self.cmb_chu_gender)
        form.addRow("Năm sinh (Col 12):", self.txt_chu_dob)
        form.addRow("Loại giấy tờ (Col 13):", self.cmb_chu_id_type)
        form.addRow("Số giấy tờ (Col 14):", self.txt_chu_id_num)
        form.addRow("Tổ / Khu dân phố (Col 19):", self.txt_chu_to)
        form.addRow("Mã Xã / Phường (Col 20):", self.cmb_chu_xa)
        form.addRow("Xã, Huyện, Tỉnh (Col 21):", self.txt_chu_xa_huyen_tinh)
        form.addRow("Địa chỉ đầy đủ (Col 22):", self.txt_chu_full_addr)
        form.addRow("Dân tộc (Col 24):", self.cmb_chu_dantoc)
        form.addRow("Quốc tịch (Col 25):", self.cmb_chu_quoctich)

        scroll.setWidget(container)
        return scroll

    # -------------------------------------------------------------
    # TAB 3: VỢ (CHỒNG)
    # -------------------------------------------------------------
    def _create_tab_vo_chong(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)

        self.chk_has_spouse = QCheckBox("Có thông tin Vợ / Chồng")
        self.chk_has_spouse.toggled.connect(self._toggle_spouse_fields)
        form.addRow(self.chk_has_spouse)

        self.txt_vo_name = QLineEdit()
        self._register_input(26, self.txt_vo_name)

        self.cmb_vo_gender = QComboBox()
        self.cmb_vo_gender.addItems(["Nữ", "Nam"])
        self._register_input(27, self.cmb_vo_gender)

        self.txt_vo_dob = QLineEdit()
        self._register_input(29, self.txt_vo_dob)

        self.cmb_vo_id_type = QComboBox()
        self.cmb_vo_id_type.addItems(self.master_data.id_types)
        self._register_input(30, self.cmb_vo_id_type)

        self.txt_vo_id_num = QLineEdit()
        self._register_input(31, self.txt_vo_id_num)

        self.txt_vo_to = QLineEdit()
        self.txt_vo_to.textChanged.connect(self._update_vo_full_address)
        self._register_input(36, self.txt_vo_to)

        self.cmb_vo_xa = QComboBox()
        self.cmb_vo_xa.setEditable(True)
        self._populate_communes(self.cmb_vo_xa)
        self.cmb_vo_xa.currentIndexChanged.connect(self._on_vo_commune_changed)
        self._register_input(37, self.cmb_vo_xa)

        self.txt_vo_xa_huyen_tinh = QLineEdit()
        self.txt_vo_xa_huyen_tinh.setReadOnly(True)
        self._register_input(38, self.txt_vo_xa_huyen_tinh)

        self.txt_vo_full_addr = QLineEdit()
        self._register_input(39, self.txt_vo_full_addr)

        self.cmb_vo_dantoc = QComboBox()
        self.cmb_vo_dantoc.setEditable(True)
        self.cmb_vo_dantoc.addItems(self.master_data.ethnicities)
        self.cmb_vo_dantoc.setCurrentText("Kinh")
        self._register_input(41, self.cmb_vo_dantoc)

        self.cmb_vo_quoctich = QComboBox()
        self.cmb_vo_quoctich.setEditable(True)
        self.cmb_vo_quoctich.addItems(self.master_data.nationalities)
        self.cmb_vo_quoctich.setCurrentText("Việt Nam")
        self._register_input(42, self.cmb_vo_quoctich)

        form.addRow("Họ và tên Vợ/Chồng (Col 26):", self.txt_vo_name)
        form.addRow("Giới tính (Col 27):", self.cmb_vo_gender)
        form.addRow("Năm sinh (Col 29):", self.txt_vo_dob)
        form.addRow("Loại giấy tờ (Col 30):", self.cmb_vo_id_type)
        form.addRow("Số giấy tờ (Col 31):", self.txt_vo_id_num)
        form.addRow("Tổ / Khu dân phố (Col 36):", self.txt_vo_to)
        form.addRow("Mã Xã / Phường (Col 37):", self.cmb_vo_xa)
        form.addRow("Xã, Huyện, Tỉnh (Col 38):", self.txt_vo_xa_huyen_tinh)
        form.addRow("Địa chỉ đầy đủ (Col 39):", self.txt_vo_full_addr)
        form.addRow("Dân tộc (Col 41):", self.cmb_vo_dantoc)
        form.addRow("Quốc tịch (Col 42):", self.cmb_vo_quoctich)

        self._toggle_spouse_fields(False)
        scroll.setWidget(container)
        return scroll

    def _toggle_spouse_fields(self, enabled: bool):
        for col in [26, 27, 29, 30, 31, 36, 37, 38, 39, 41, 42]:
            if col in self.field_inputs:
                self.field_inputs[col].setEnabled(enabled)

    # -------------------------------------------------------------
    # TAB 4: THỬA ĐẤT & MĐSD
    # -------------------------------------------------------------
    def _create_tab_thua_dat(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)

        self.txt_thua_so = QLineEdit()
        self.txt_thua_so.setPlaceholderText("Ví dụ: 124")
        self._register_input(43, self.txt_thua_so)

        self.txt_to_so = QLineEdit()
        self.txt_to_so.setPlaceholderText("Ví dụ: 71")
        self._register_input(44, self.txt_to_so)

        self.txt_tyle = QLineEdit("500")
        self._register_input(45, self.txt_tyle)

        self.txt_loai_bando = QLineEdit("Bản đồ địa chính (VN2000)")
        self._register_input(46, self.txt_loai_bando)

        self.txt_dt_bando = QLineEdit()
        self.txt_dt_bando.setPlaceholderText("Ví dụ: 254.1")
        self.txt_dt_bando.textChanged.connect(self._auto_sync_dt_phaply)
        self._register_input(52, self.txt_dt_bando)

        self.txt_dt_phaply = QLineEdit()
        self._register_input(53, self.txt_dt_phaply)

        # MĐSD 1 Group
        grp1 = QGroupBox("Mục đích sử dụng 1 (Chính)")
        f1 = QFormLayout(grp1)
        self.cmb_mdsd1 = QComboBox()
        self.cmb_mdsd1.setEditable(True)
        self._populate_land_types(self.cmb_mdsd1)
        self._register_input(54, self.cmb_mdsd1)

        self.txt_dt_mdsd1 = QLineEdit()
        self.txt_dt_mdsd1.setPlaceholderText("Ví dụ: 120")
        self._register_input(56, self.txt_dt_mdsd1)

        self.txt_thoihan1 = QLineEdit("Lâu dài")
        self._register_input(58, self.txt_thoihan1)

        self.cmb_nguongoc1 = QComboBox()
        self.cmb_nguongoc1.setEditable(True)
        self.cmb_nguongoc1.addItems(self.master_data.land_use_origins)
        self.cmb_nguongoc1.setCurrentText("CNQ-CTT")
        self._register_input(60, self.cmb_nguongoc1)

        f1.addRow("Mã MĐSD 1 (Col 54):", self.cmb_mdsd1)
        f1.addRow("Diện tích 1 (Col 56):", self.txt_dt_mdsd1)
        f1.addRow("Thời hạn SD 1 (Col 58):", self.txt_thoihan1)
        f1.addRow("Nguồn gốc cấp (Col 60):", self.cmb_nguongoc1)

        # MĐSD 2 Group
        grp2 = QGroupBox("Mục đích sử dụng 2 (Phụ / Trồng cây / Nông nghiệp)")
        f2 = QFormLayout(grp2)
        self.cmb_mdsd2 = QComboBox()
        self.cmb_mdsd2.setEditable(True)
        self._populate_land_types(self.cmb_mdsd2)
        self._register_input(62, self.cmb_mdsd2)

        self.txt_dt_mdsd2 = QLineEdit()
        self.txt_dt_mdsd2.setPlaceholderText("Ví dụ: 134.1")
        self._register_input(64, self.txt_dt_mdsd2)

        self.txt_thoihan2 = QLineEdit()
        self.txt_thoihan2.setPlaceholderText("Ví dụ: Đến tháng 12/2055")
        self._register_input(66, self.txt_thoihan2)

        self.cmb_nguongoc2 = QComboBox()
        self.cmb_nguongoc2.setEditable(True)
        self.cmb_nguongoc2.addItems(self.master_data.land_use_origins)
        self.cmb_nguongoc2.setCurrentText("CNQ-CTT")
        self._register_input(68, self.cmb_nguongoc2)

        f2.addRow("Mã MĐSD 2 (Col 62):", self.cmb_mdsd2)
        f2.addRow("Diện tích 2 (Col 64):", self.txt_dt_mdsd2)
        f2.addRow("Thời hạn SD 2 (Col 66):", self.txt_thoihan2)
        f2.addRow("Nguồn gốc cấp (Col 68):", self.cmb_nguongoc2)

        form.addRow("Số thửa (Col 43):", self.txt_thua_so)
        form.addRow("Số tờ (Col 44):", self.txt_to_so)
        form.addRow("Tỷ lệ (Col 45):", self.txt_tyle)
        form.addRow("Loại bản đồ (Col 46):", self.txt_loai_bando)
        form.addRow("Diện tích bản đồ (Col 52):", self.txt_dt_bando)
        form.addRow("Diện tích pháp lý (Col 53):", self.txt_dt_phaply)
        form.addRow(grp1)
        form.addRow(grp2)

        scroll.setWidget(container)
        return scroll

    def _auto_sync_dt_phaply(self, text: str):
        if not self.txt_dt_phaply.text():
            self.txt_dt_phaply.setText(text)

    # -------------------------------------------------------------
    # TAB 5: GHI CHÚ & KÝ GCN
    # -------------------------------------------------------------
    def _create_tab_ghi_chu(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)

        self.txt_loai_gcn = QLineEdit("Giấy chứng nhận QSDĐ & QSHNƠ và TSKGLVĐ theo NĐ 43/NĐ-CP")
        self._register_input(99, self.txt_loai_gcn)

        self.txt_so_vao_so = QLineEdit()
        self.txt_so_vao_so.setPlaceholderText("Ví dụ: CH89147")
        self._register_input(100, self.txt_so_vao_so)

        self.txt_ngay_ky = QLineEdit()
        self.txt_ngay_ky.setPlaceholderText("Ví dụ: 31/07/2024")
        self._register_input(102, self.txt_ngay_ky)

        self.txt_nguoi_ky = QLineEdit()
        self.txt_nguoi_ky.setPlaceholderText("Ví dụ: Vũ Ngọc Lâm")
        self._register_input(103, self.txt_nguoi_ky)

        self.txt_ghi_chu_t2 = QPlainTextEdit()
        self.txt_ghi_chu_t2.setPlaceholderText("Ghi chú trang 2...")
        self._register_input(110, self.txt_ghi_chu_t2)

        self.txt_nvtc_loai = QLineEdit("Lệ phí trước bạ;Thuế thu nhập từ chuyển nhượng bất động sản")
        self._register_input(118, self.txt_nvtc_loai)

        self.txt_nvtc_tien = QLineEdit()
        self.txt_nvtc_tien.setPlaceholderText("Ví dụ: 6000000;24000000")
        self._register_input(119, self.txt_nvtc_tien)

        form.addRow("Loại GCN (Col 99):", self.txt_loai_gcn)
        form.addRow("Số vào sổ (Col 100):", self.txt_so_vao_so)
        form.addRow("Ngày ký (Col 102):", self.txt_ngay_ky)
        form.addRow("Người ký (Col 103):", self.txt_nguoi_ky)
        form.addRow("Ghi chú trang 2 (Col 110):", self.txt_ghi_chu_t2)
        form.addRow("Loại NVTC (Col 118):", self.txt_nvtc_loai)
        form.addRow("Số tiền NVTC (Col 119):", self.txt_nvtc_tien)

        scroll.setWidget(container)
        return scroll

    # -------------------------------------------------------------
    # HELPER POPULATORS & COMMUNE ADDR UPDATERS
    # -------------------------------------------------------------
    def _populate_communes(self, combo: QComboBox):
        combo.clear()
        combo.addItem("", None)
        for c in self.master_data.communes:
            disp_text = f"{c.code_3cap} - {c.name_3cap}, {c.district}, {c.province}"
            combo.addItem(disp_text, c)

    def _populate_land_types(self, combo: QComboBox):
        combo.clear()
        combo.addItem("", None)
        for lt in self.master_data.land_types:
            disp_text = f"{lt.code} - {lt.name}"
            combo.addItem(disp_text, lt.code)

    def _on_chu_commune_changed(self, idx: int):
        data = self.cmb_chu_xa.currentData()
        if isinstance(data, CommuneInfo):
            self.last_commune_code = data.code_3cap
            self.txt_chu_xa_huyen_tinh.setText(data.full_location)
            self._update_chu_full_address()
            if self.chk_has_spouse.isChecked() and not self.txt_vo_xa_huyen_tinh.text():
                self.cmb_vo_xa.setCurrentIndex(idx)

    def _update_chu_full_address(self):
        to = self.txt_chu_to.text().strip()
        location = self.txt_chu_xa_huyen_tinh.text().strip()
        full = f"{to}, {location}".strip(", ") if to else location
        self.txt_chu_full_addr.setText(full)

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
    # READ / WRITE FORM DATA
    # -------------------------------------------------------------
    def get_attr_dict(self) -> Dict[int, Any]:
        """Collects values from form inputs mapped to column indices."""
        data: Dict[int, Any] = {}

        data[6] = "CNV"  # ĐTSD
        data[7] = "0"    # HGD
        data[8] = "0"    # Người đại diện
        data[104] = "0"  # Ủy quyền ký
        data[105] = "1"  # Ký thay

        for col, widget in self.field_inputs.items():
            if isinstance(widget, QLineEdit):
                data[col] = widget.text().strip()
            elif isinstance(widget, QPlainTextEdit):
                data[col] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                val = widget.currentData()
                if isinstance(val, CommuneInfo):
                    data[col] = val.code_3cap
                elif val is not None:
                    data[col] = val
                else:
                    text = widget.currentText().strip()
                    if " - " in text:
                        data[col] = text.split(" - ")[0].strip()
                    else:
                        data[col] = text
            elif isinstance(widget, QCheckBox):
                data[col] = "1" if widget.isChecked() else "0"

        if 10 in data:
            data[10] = "1" if data[10] == "Nam" else "0"
        if 27 in data:
            data[27] = "1" if data[27] == "Nam" else "0"

        return data

    def load_attr_dict(self, data: Dict[int, Any], serial: str):
        """Populates form from existing dictionary."""
        self.txt_serial.setText(serial)

        for col, widget in self.field_inputs.items():
            val = str(data.get(col, "") or "")

            if isinstance(widget, QLineEdit):
                widget.setText(val)
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(val)
            elif isinstance(widget, QComboBox):
                if col in [20, 37]:
                    for i in range(widget.count()):
                        c_info = widget.itemData(i)
                        if isinstance(c_info, CommuneInfo) and c_info.code_3cap == val:
                            widget.setCurrentIndex(i)
                            break
                else:
                    widget.setCurrentText(val)

        if data.get(26):
            self.chk_has_spouse.setChecked(True)
            self._toggle_spouse_fields(True)
        else:
            self.chk_has_spouse.setChecked(False)
            self._toggle_spouse_fields(False)
