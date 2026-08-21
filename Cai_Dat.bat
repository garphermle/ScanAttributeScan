@echo off
chcp 65001 >nul
title Cai dat moi truong ScanAttribute
echo =======================================================
echo     DANG CAI DAT MOI TRUONG VA THU VIEN SCANATTRIBUTE
echo =======================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] May tinh cua ban chua cai dat Python!
    echo Vui long tai va cai dat Python 3.10+ tu: https://www.python.org/downloads/
    echo (Nho tich vao o 'Add Python to PATH' khi cai dat).
    pause
    exit /b 1
)

echo [1/2] Dang nang cap trinh quan ly goi pip...
python -m pip install --upgrade pip

echo.
echo [2/2] Dang cai dat cac thu vien can thiet (PySide6, openpyxl, pypdfium2...)...
pip install PySide6 pypdfium2 openpyxl Pillow opencv-python-headless pyzbar rapidocr-onnxruntime PyMuPDF numpy

echo.
echo =======================================================
echo     CAI DAT HOAN TAT! 
echo     Ban co the chay chuong trinh bang file: Chay_ScanAttribute.bat
echo =======================================================
pause
