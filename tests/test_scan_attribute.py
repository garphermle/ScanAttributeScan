"""
Unit tests for ScanAttribute core modules (Excel Import Validation & Data Models).
"""

import pytest
import os
from scan_attribute.core.data_models import parse_date_flexible, MasterDataManager
from scan_attribute.core.excel_engine import ExcelEngine

def test_flexible_date_parsing():
    assert parse_date_flexible("1/5/2026") == "01/05/2026"
    assert parse_date_flexible("01/05/2026") == "01/05/2026"
    assert parse_date_flexible("31/7/2024") == "31/07/2024"
    assert parse_date_flexible("2026-08-09") == "09/08/2026"

def test_excel_template_columns():
    excel_path = "/home/garpherm/VNPT/Source/Excel_FormMau_v5_04082026.xlsx"
    assert os.path.exists(excel_path)

    engine = ExcelEngine(excel_path)
    engine.initialize()
    assert engine.ws is not None

    # Flexible column structure test (Rule 4: check >= 8 columns instead of exact)
    assert engine.ws.max_column >= 8
    assert engine.ws.max_column >= 180  # Standard template has 186 columns

def test_excel_read_row_sample():
    excel_path = "/home/garpherm/VNPT/Source/Excel_FormMau_v5_04082026.xlsx"
    engine = ExcelEngine(excel_path)
    engine.initialize()

    row_idx = engine.find_row_by_serial("CU 491118")
    assert row_idx is not None
    data = engine.read_row_data(row_idx)

    assert data.get(2) == "CU 491118"
    assert data.get(9) == "Nguyễn Anh Tuấn"
    assert str(data.get(43)) == "124"
    assert str(data.get(44)) == "71"
