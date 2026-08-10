# ScanAttribute — Tool Nhập Liệu Thuộc Tính Đất Đai Siêu Tốc Cho Con Người

Ứng dụng Desktop Windows / Linux hỗ trợ con người nhập dữ liệu thuộc tính đất đai từ bộ hồ sơ PDF scan thô (`GCN.pdf`, `GT.pdf`, `GTK.pdf`) vào file Excel mẫu 186 cột [`Excel_FormMau_v5_04082026.xlsx`](../Excel_FormMau_v5_04082026.xlsx).

---

## 🎯 Triết lý thiết kế (Zero-AI Delay, Maximum Human Speed)

1. **Tốc độ phản hồi tức thì (0.05s)**: Không bắt AI quét ngầm toàn bộ file PDF. Mở file PDF tức thì bằng engine `pypdfium2`.
2. **Loại bỏ 100% thao tác Alt-Tab**: Giao diện Split-Screen 3 cột song song (Cột danh mục hồ sơ -> Trình xem PDF -> Form nhập liệu 5 tab).
3. **Kéo-thả Crop OCR (Instant Snippet OCR)**: Khi gặp mã vạch, CCCD hoặc đoạn ghi chú dài, chỉ cần **kéo giữ chuột khoanh vùng** trên PDF, chữ tự động dán vào ô nhập liệu đang chọn trong 0.05s.
4. **Auto-Default & Sticky Address (Điền sẵn & Ghi nhớ)**: Tự điền Dân tộc (Kinh), Quốc tịch (Việt Nam), Tỷ lệ (500)... Tự nhớ địa chỉ Tỉnh/Huyện/Xã của hồ sơ trước.
5. **Tra cứu danh mục 2 chiều**: Nhập tên xã -> Tự ra mã xã và tự tạo chuỗi Địa chỉ đầy đủ.
6. **Thao tác 100% bằng bàn phím**: Phím `Tab` để di chuyển, `Ctrl+Enter` để lưu Excel và chuyển sang hồ sơ tiếp theo.

---

## 📁 Cấu trúc thư mục ứng dụng

```text
/home/garpherm/VNPT/Source/scan_attribute/
├── scan_attribute/
│   ├── main.py                  # Entry point PySide6
│   ├── core/
│   │   ├── data_models.py       # Dataclass & Master Data Loader
│   │   ├── excel_engine.py      # openpyxl Read/Write 186 cột Excel
│   │   ├── pdf_engine.py        # High-speed PDF renderer (pypdfium2)
│   │   ├── ocr_engine.py        # Crop Snippet RapidOCR engine
│   │   └── master_data.py       # Path locator
│   ├── gui/
│   │   ├── main_window.py       # Cửa sổ chính Splitter UI
│   │   ├── pdf_viewer.py        # PDF Viewer + Crop OCR RubberBand
│   │   ├── queue_widget.py      # Danh sách hàng đợi hồ sơ
│   │   ├── form_widget.py       # Form 5 Tab ánh xạ 186 cột
│   │   └── components/
│   │       └── search_combo.py  # Dropdown tìm kiếm thông minh
│   └── resources/
│       └── Excel_FormMau.xlsx  # Mẫu Excel chuẩn kèm theo
├── tests/
│   └── test_scan_attribute.py   # Unit tests kiểm thử
├── run.sh                       # Script khởi chạy nhanh
├── pyproject.toml
└── README.md
```

---

## 🚀 Cách chạy ứng dụng

### 1. Khởi chạy bằng script
```bash
cd /home/garpherm/VNPT/Source/scan_attribute
./run.sh
```

### 2. Chạy từ mã nguồn Python
```bash
PYTHONPATH=/home/garpherm/VNPT/Source/scan_attribute /home/garpherm/VNPT/Source/pdfsplit/.venv/bin/python -m scan_attribute.main
```

### 3. Chạy Unit Tests
```bash
PYTHONPATH=/home/garpherm/VNPT/Source/scan_attribute /home/garpherm/VNPT/Source/pdfsplit/.venv/bin/pytest /home/garpherm/VNPT/Source/scan_attribute/tests -v
```

### 4. Tự động Build Windows App qua GitHub Actions
- Mỗi khi **Push** code lên nhánh `main` hoặc tạo **Release Tag** (ví dụ `v1.0.0`), GitHub Actions sẽ tự động thực hiện quy trình kiểm thử và đóng gói ứng dụng cho Windows:
  - **`ScanAttribute-Windows-x64.zip`**: Bản cài đặt dạng thư mục đóng gói (Tốc độ khởi chạy tức thì, khuyến nghị).
  - **`ScanAttribute-Standalone.exe`**: Bản file `.exe` đơn duy nhất dạng Portable (Tiện lợi di động).
- File thực thi sau khi build hoàn tất có thể được tải về trực tiếp từ tab **Actions** hoặc phần **Releases** trên GitHub.

---

## ⌨️ Phím tắt thao tác nhanh

| Phím tắt | Hành động |
|---|---|
| `Ctrl + Enter` | **Lưu dòng vào Excel & Tự chuyển hồ sơ tiếp theo** |
| `Ctrl + O` | Chọn thư mục chứa các hồ sơ (`CU 491118`, `CU 491119`...) |
| `F5` | Quét lại danh sách hồ sơ |
| `Tab` / `Shift+Tab` | Chuyển ô nhập liệu tiếp theo / lùi lại |
| `Kéo chuột trên PDF` | Khoanh vùng OCR dán chữ tức thời vào ô hiện tại |
| `◀` `▶` | Xem trang PDF trước / sau |
| `🔍 Zoom +` / `Zoom -` | Phóng to / Thu nhỏ trang PDF |
| `↶` `↷` | Xoay trang PDF trái / phải |

---

## 📋 Luồng làm việc siêu tốc (45s/Hồ sơ)

1. Mở app -> Chọn thư mục gốc (nơi chứa các folder bóc tách từ `pdfsplit`).
2. App liệt kê toàn bộ các folder (`CU 491118`...).
3. Nhấn vào hồ sơ:
   - PDF bên trái mở tức thì `GCN.pdf`.
   - Tool tự nạp mã `CU 491118` và kiểm tra nếu đã có trong Excel.
4. Mắt lướt PDF bên trái, tay gõ/Tab hoặc kéo chuột OCR bên phải.
5. Nhấn `Ctrl+Enter` -> Excel ghi nhận dòng mới -> App tự nảy sang hồ sơ kế tiếp!
