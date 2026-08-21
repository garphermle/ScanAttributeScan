@echo off
chcp 65001 >nul
title ScanAttribute - Tool Nhap Thuoc Tinh Ho So Quet
echo Dang khoi dong ScanAttribute...
python -m scan_attribute.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo =======================================================
    echo [THONG BAO] Gap loi khi khoi dong ung dung.
    echo Neu chua cai thu vien, vui long chay file: Cai_Dat.bat
    echo =======================================================
    pause
)
