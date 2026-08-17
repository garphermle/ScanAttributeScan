"""
Unit tests for ScanAttribute core modules (Excel Import Validation & Data Models).
"""

import pytest
import os
from scan_attribute.core.data_models import parse_date_flexible, MasterDataManager
from scan_attribute.core.excel_engine import ExcelEngine
from scan_attribute.core.master_data import get_default_excel_path

def test_flexible_date_parsing():
    assert parse_date_flexible("1/5/2026") == "01/05/2026"
    assert parse_date_flexible("01/05/2026") == "01/05/2026"
    assert parse_date_flexible("31/7/2024") == "31/07/2024"
    assert parse_date_flexible("2026-08-09") == "09/08/2026"

def test_excel_template_columns():
    excel_path = get_default_excel_path()
    assert os.path.exists(excel_path)

    engine = ExcelEngine(excel_path)
    engine.initialize()
    assert engine.ws is not None

    # Flexible column structure test (Rule 4: check >= 8 columns instead of exact)
    assert engine.ws.max_column >= 8
    assert engine.ws.max_column >= 180  # Standard template has 186 columns

def test_excel_read_row_sample():
    excel_path = get_default_excel_path()
    engine = ExcelEngine(excel_path)
    engine.initialize()

    row_idx = engine.find_row_by_serial("CU 491118")
    assert row_idx is not None
    data = engine.read_row_data(row_idx)

    assert data.get(2) == "CU 491118"
    assert data.get(9) == "Nguyễn Anh Tuấn"
    assert str(data.get(43)) == "124"
    assert str(data.get(44)) == "71"


def test_queue_widget_2_view_modes(qapp, tmp_path):
    from scan_attribute.gui.queue_widget import QueueWidget, ROLE_ITEM_TYPE, ROLE_FILE_NAME
    
    # Create fake directory structure with PDFs
    folder_a = tmp_path / "CU 491118"
    folder_a.mkdir()
    (folder_a / "CU 491118-GCN.pdf").write_bytes(b"%PDF-1.4 test")
    (folder_a / "CU 491118-GT.pdf").write_bytes(b"%PDF-1.4 test")

    qw = QueueWidget()
    
    # Mode 1: Folder only
    qw.view_mode = "folder"
    qw.load_folders(str(tmp_path), {})
    assert len(qw.folder_items) == 1
    assert len(qw.file_items) == 0

    # Mode 2: Files view
    qw.view_mode = "files"
    qw.load_folders(str(tmp_path), {})
    assert len(qw.folder_items) == 1
    assert len(qw.file_items) == 2
    
    filenames = [f.data(0, ROLE_FILE_NAME) for f in qw.file_items]
    assert "CU 491118-GCN.pdf" in filenames
    assert "CU 491118-GT.pdf" in filenames


def test_form_widget_186_columns_defaults(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    fw = AttributeFormWidget(md)

    fw.txt_serial.setText("CU 491118")
    fw.txt_chu_name.setText("Nguyễn Anh Tuấn")
    fw.txt_chu_to.setText("Khu 5")
    fw.txt_chu_full_addr.setText("Khu 5, Phường Quảng Yên, Thị xã Quảng Yên, Tỉnh Quảng Ninh")
    fw.txt_ngay_ky.setText("31/07/2024")

    attr = fw.get_attr_dict()
    assert attr.get(2) == "CU 491118"
    assert attr.get(6) == "CNV"
    assert attr.get(7) == "0"
    assert attr.get(8) == "0"
    assert attr.get(9) == "Nguyễn Anh Tuấn"
    assert attr.get(57) == "0"
    assert attr.get(65) == ""  # MDSD 2 is optional/unchecked -> empty
    assert attr.get(90) == "Khu 5"
    assert attr.get(94) == "Khu 5, Phường Quảng Yên, Thị xã Quảng Yên, Tỉnh Quảng Ninh"
    assert attr.get(97) == ""  # Quan ly is optional/unchecked -> empty
    assert attr.get(102) == "31/07/2024"
    assert attr.get(106) == "31/07/2024"  # Auto synced from Ngày ký


def test_form_widget_interactive_editing(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    excel_path = get_default_excel_path()
    md.load_from_excel(excel_path)
    fw = AttributeFormWidget(md)

    # User modifies values directly on UI controls
    fw.txt_serial.setText("BT 123456")
    fw.cmb_chu_dtsd.setCurrentText("TCC - Tổ chức trong nước")
    fw.cmb_chu_hgd.setCurrentIndex(1)  # "1 - Là Hộ gia đình"
    fw.cmb_chu_daidien.setCurrentIndex(1)  # "1 - Là người đại diện"
    fw.cmb_uy_quyen_ky.setCurrentIndex(1)  # "1 - Có ủy quyền"
    fw.cmb_ky_thay.setCurrentIndex(1)  # "0 - Ký trực tiếp"
    fw.cmb_phan_loai_thua.setCurrentText("B - Đã cấp GCN, có tài sản")
    
    fw.chk_has_quan_ly.setChecked(True)
    fw.cmb_hinh_thuc_sd.setCurrentText("1 - Sử dụng chung")
    fw.cmb_trang_thai_thua.setCurrentText("4 - Đã đăng ký, đủ điều kiện cấp GCN")
    fw.txt_thu_muc_hsq.setText("BT 123456")

    attr = fw.get_attr_dict()
    assert attr.get(2) == "BT 123456"
    assert attr.get(6) == "TCC"
    assert attr.get(7) == "1"
    assert attr.get(8) == "1"
    assert attr.get(104) == "1"
    assert attr.get(51) == "B"
    assert attr.get(97) == "1"
    assert attr.get(98) == "4"
    assert attr.get(183) == "BT 123456"


def test_pdf_selection_and_tab_navigation(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    fw = AttributeFormWidget(md)

    # GCN PDF -> Tab 0
    fw.navigate_to_pdf_type("CU 491118-GCN.pdf")
    assert fw.tab_widget.currentIndex() == 0
    assert fw.active_input_widget == fw.txt_barcode

    # GT / CCCD PDF -> Tab 1
    fw.navigate_to_pdf_type("CU 491118-GT.pdf")
    assert fw.tab_widget.currentIndex() == 1
    assert fw.active_input_widget == fw.txt_chu_name

    # Vợ chồng PDF -> Tab 2
    fw.navigate_to_pdf_type("CU 491118-VO.pdf")
    assert fw.tab_widget.currentIndex() == 2
    assert fw.chk_has_spouse.isChecked()
    assert fw.active_input_widget == fw.txt_vo_name

    # Bản đồ / GTK PDF -> Tab 3
    fw.navigate_to_pdf_type("CU 491118-GTK.pdf")
    assert fw.tab_widget.currentIndex() == 3
    assert fw.active_input_widget == fw.txt_thua_so

    # NVTC PDF -> Tab 4
    fw.navigate_to_pdf_type("CU 491118-NVTC.pdf")
    assert fw.tab_widget.currentIndex() == 4
    assert fw.active_input_widget == fw.cmb_nvtc_loai

    # Tài sản PDF -> Tab 5
    fw.navigate_to_pdf_type("CU 491118-TS.pdf")
    assert fw.tab_widget.currentIndex() == 5
    assert fw.active_input_widget == fw.txt_nha_dt_xd


def test_queue_child_pdf_shows_excel_row(qapp, tmp_path):
    from scan_attribute.gui.queue_widget import QueueWidget
    folder_a = tmp_path / "CU 491118"
    folder_a.mkdir()
    f1 = folder_a / "CU 491118-GCN.pdf"
    f2 = folder_a / "CU 491118-GT.pdf"
    f1.write_bytes(b"%PDF-1.4 test")
    f2.write_bytes(b"%PDF-1.4 test")

    qw = QueueWidget()
    qw.view_mode = "files"
    
    # 1. Load with independent file mapping
    file_map = {
        str(f1).lower(): {"row": 5, "stt": 1},
        str(f2).lower(): {"row": 6, "stt": 2}
    }
    qw.load_folders(str(tmp_path), {}, file_map)

    assert len(qw.file_items) == 2
    assert "Dòng 5 (STT 1)" in qw.file_items[0].text(1)
    assert "Dòng 6 (STT 2)" in qw.file_items[1].text(1)


def test_file_tracker_persistence(tmp_path):
    from scan_attribute.core.file_tracker import FileTracker
    tracker = FileTracker(str(tmp_path), "test.xlsx")

    file_a = str(tmp_path / "folder1" / "doc1.pdf")
    file_b = str(tmp_path / "folder1" / "doc2.pdf")

    tracker.record_file_saved(file_a, row=5, stt=1, serial="DOC1")
    tracker.record_file_saved(file_b, row=6, stt=2, serial="DOC2")

    # Reload from disk
    tracker2 = FileTracker(str(tmp_path), "test.xlsx")
    info_a = tracker2.get_file_info(file_a)
    info_b = tracker2.get_file_info(file_b)

    assert info_a is not None and info_a["row"] == 5 and info_a["stt"] == 1
    assert info_b is not None and info_b["row"] == 6 and info_b["stt"] == 2


def test_file_level_independent_rows(tmp_path):
    excel_path = str(tmp_path / "test_out.xlsx")
    template_path = get_default_excel_path()
    engine = ExcelEngine(template_path, excel_path)
    engine.switch_target_file(excel_path, copy_template_if_new=True)

    # Save File 1 -> Row 5
    r1 = engine.save_row_data("CU 491118-GCN", {2: "CU 491118-GCN", 9: "Chủ Đất A"})
    assert r1 == 5

    # Save File 2 in same folder -> Row 6 (Different row!)
    r2 = engine.save_row_data("CU 491118-GT", {2: "CU 491118-GT", 9: "Chủ Đất B"})
    assert r2 == 6

    # Update File 1 -> Updates Row 5 without touching Row 6
    r1_updated = engine.save_row_data("CU 491118-GCN", {2: "CU 491118-GCN", 9: "Chủ Đất A Mới"}, target_row=5)
    assert r1_updated == 5

    d1 = engine.read_row_data(5)
    d2 = engine.read_row_data(6)
    assert d1.get(9) == "Chủ Đất A Mới"
    assert d2.get(9) == "Chủ Đất B"


def test_id_type_map_types_and_defaults(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    # 1. Check Col 48 & 49 defaults
    assert fw.txt_phuong_phap_do.text() == "Toàn đạc điện tử"
    assert fw.txt_nguoi_kiem_tra.text() == "Cao"

    # 2. Check ID type abbreviation
    fw.cmb_chu_id_type.setCurrentText("CMND - Chứng minh nhân dân")
    attrs = fw.get_attr_dict()
    assert attrs.get(13) == "CMND"

    fw.cmb_chu_id_type.setCurrentText("CCCD - Căn cước công dân")
    attrs = fw.get_attr_dict()
    assert attrs.get(13) == "CCCD"

    # 3. Check Map type value is 1, 2, 3, 4, 5
    fw.cmb_loai_bando.setCurrentText("2 - Bản đồ địa chính (HN72)")
    attrs = fw.get_attr_dict()
    assert attrs.get(46) == "2"

    fw.cmb_loai_bando.setCurrentText("1 - Bản đồ địa chính (VN2000)")
    attrs = fw.get_attr_dict()
    assert attrs.get(46) == "1"


def test_nguon_goc_chi_tiet_auto_sync(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    # Select CNQ-CTT in Col 60
    idx = fw.cmb_mdsd1_ma_nguon_goc.findData("CNQ-CTT")
    assert idx >= 0
    fw.cmb_mdsd1_ma_nguon_goc.setCurrentIndex(idx)
    assert "Công nhận QSDĐ như giao đất có thu tiền sử dụng đất" in fw.txt_mdsd1_nguon_goc_ct.text()

    attrs = fw.get_attr_dict()
    assert attrs.get(60) == "CNQ-CTT"
    assert attrs.get(61) == "Công nhận QSDĐ như giao đất có thu tiền sử dụng đất"


def test_measurement_data_lookup_col_47_50(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    # Find measurement directly
    meas = md.find_measurement("Phường Hà Khánh", "Thành phố Hạ Long")
    assert meas is not None
    assert "Xí nghiệp tài nguyên và môi trường 3" in meas.measuring_unit
    assert "21/12/2017" in meas.completion_date


def test_optional_fields_empty_when_unchecked(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    # By default, MDSD 2, Quan ly, Han che are unchecked
    attrs = fw.get_attr_dict()
    assert attrs.get(65) == ""  # Là SD chung 2 is empty!
    assert attrs.get(62) == ""  # MDSD 2 is empty!
    assert attrs.get(111) == "" # Han che is empty!
    assert attrs.get(117) == "" # Loai han che is empty!


def test_spouse_defaults_and_manual_address(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    fw.chk_has_spouse.setChecked(True)
    # Check default Col 41 & 42
    assert fw.cmb_vo_dantoc.currentText() == "Không rõ"
    assert fw.cmb_vo_quoctich.currentText() == "Việt Nam"

    # Check manual address entry without picking commune
    fw.txt_vo_to.setText("Khu 3")
    fw.txt_vo_xa_huyen_tinh.setText("Phường Hồng Hải, Thành phố Hạ Long, Tỉnh Quảng Ninh")

    assert fw.txt_vo_full_addr.text() == "Khu 3, Phường Hồng Hải, Thành phố Hạ Long, Tỉnh Quảng Ninh"

    attrs = fw.get_attr_dict()
    assert attrs.get(41) == "Không rõ"
    assert attrs.get(42) == "Việt Nam"
    assert attrs.get(38) == "Phường Hồng Hải, Thành phố Hạ Long, Tỉnh Quảng Ninh"
    assert attrs.get(39) == "Khu 3, Phường Hồng Hải, Thành phố Hạ Long, Tỉnh Quảng Ninh"


def test_ma_hs_goc_auto_sync_from_barcode(qapp):
    from scan_attribute.gui.form_widget import AttributeFormWidget
    md = MasterDataManager()
    template_path = get_default_excel_path()
    md.load_from_excel(template_path)
    fw = AttributeFormWidget(md)

    # Set barcode with 13 digits
    fw.txt_barcode.setText("0667320081887")
    assert fw.txt_ma_hs.text() == "081887"

    attrs = fw.get_attr_dict()
    assert attrs.get(3) == "081887"
    assert attrs.get(4) == "0667320081887"
