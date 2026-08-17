"""
Excel Engine for loading, updating, appending, and clearing sample data (186 columns).
"""

import os
import shutil
from typing import Dict, Any, Optional, List
import openpyxl


class ExcelEngine:
    def __init__(self, template_path: str, output_path: Optional[str] = None):
        self.template_path = template_path
        self.output_path = output_path or template_path
        self.wb: Optional[openpyxl.Workbook] = None
        self.ws = None

    def initialize(self, force_reload: bool = False):
        """Ensures output file exists by copying template if necessary, then loads workbook."""
        if not os.path.exists(self.output_path):
            os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
            shutil.copy(self.template_path, self.output_path)
            
        if self.wb is None or force_reload:
            self.wb = openpyxl.load_workbook(self.output_path)
            if 'Data' in self.wb.sheetnames:
                self.ws = self.wb['Data']
            else:
                self.ws = self.wb.active

    def switch_target_file(self, target_path: str, copy_template_if_new: bool = True):
        """Switches target Excel file to a new or existing working file."""
        is_new = not os.path.exists(target_path)
        if copy_template_if_new and is_new:
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            shutil.copy(self.template_path, target_path)

        self.output_path = target_path
        self.initialize(force_reload=True)

        if is_new and copy_template_if_new and self.ws:
            # Clear sample row 5 when creating a new file so data starts at Row 5 (STT 1)
            for c in range(1, 187):
                self.ws.cell(5, c).value = None
            self.wb.save(self.output_path)
            self.initialize(force_reload=True)

    def find_row_by_serial(self, serial: str) -> Optional[int]:
        """Finds row index (1-based) matching Serial (Col 2), File Ref (Col 3), or Folder Name (Col 183)."""
        if not self.ws:
            self.initialize()
            
        serial_clean = serial.strip().lower()
        if not serial_clean:
            return None

        for r in range(5, self.ws.max_row + 1):
            val_col2 = str(self.ws.cell(r, 2).value or '').strip().lower()
            val_col3 = str(self.ws.cell(r, 3).value or '').strip().lower()
            val_col183 = str(self.ws.cell(r, 183).value or '').strip().lower()
            if val_col2 == serial_clean or val_col3 == serial_clean or val_col183 == serial_clean:
                return r
        return None

    def find_first_empty_row(self) -> int:
        """Finds the first completely empty data row starting from row 5."""
        if not self.ws:
            self.initialize()

        for r in range(5, self.ws.max_row + 2):
            col2 = self.ws.cell(r, 2).value
            col3 = self.ws.cell(r, 3).value
            col9 = self.ws.cell(r, 9).value
            if (col2 is None or str(col2).strip() == '') and \
               (col3 is None or str(col3).strip() == '') and \
               (col9 is None or str(col9).strip() == ''):
                return r
        return max(5, self.ws.max_row + 1)

    def get_processed_serials_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary mapping serial_lowercase to info:
        { "serial": "AE 345823", "row": 5, "stt": 1 }
        """
        if not self.ws:
            self.initialize()

        info_map = {}
        for r in range(5, self.ws.max_row + 1):
            col1 = self.ws.cell(r, 1).value
            val_col2 = str(self.ws.cell(r, 2).value or '').strip()
            val_col3 = str(self.ws.cell(r, 3).value or '').strip()
            val_col183 = str(self.ws.cell(r, 183).value or '').strip()

            serial = val_col2 or val_col3 or val_col183
            if serial:
                stt_val = col1 if (col1 is not None and str(col1).strip() != "") else (r - 4)
                info_map[serial.lower()] = {
                    "serial": serial,
                    "row": r,
                    "stt": stt_val
                }
        return info_map

    def get_processed_serials(self) -> List[str]:
        """Returns list of serials already present in Excel."""
        return list(self.get_processed_serials_info().keys())

    def get_data_rows_count(self) -> int:
        """Returns count of valid data rows in Excel."""
        return len(self.get_processed_serials_info())

    def read_row_data(self, row_idx: int) -> Dict[int, Any]:
        """Reads all 186 column values for a given row index."""
        if not self.ws:
            self.initialize()
            
        data = {}
        for c in range(1, 187):
            val = self.ws.cell(row_idx, c).value
            data[c] = "" if val is None else val
        return data

    def save_row_data(self, serial: str, attr_dict: Dict[int, Any], target_row: Optional[int] = None) -> int:
        """
        Saves row for serial or file. If target_row is provided or serial exists, updates that row.
        If serial is new, appends a NEW ROW directly below existing rows.
        """
        if not self.ws:
            self.initialize()
            
        row_idx = target_row
        if not row_idx:
            row_idx = self.find_row_by_serial(serial)
        if not row_idx:
            row_idx = self.find_first_empty_row()
        
        # Set STT (Col 1) automatically (Row 5 -> STT 1, Row 6 -> STT 2)
        stt_val = row_idx - 4
        self.ws.cell(row_idx, 1, value=stt_val)
        
        if 2 not in attr_dict or not attr_dict[2]:
            attr_dict[2] = serial
        if 183 not in attr_dict or not attr_dict[183]:
            attr_dict[183] = serial

        for c, val in attr_dict.items():
            if 1 <= c <= 186:
                self.ws.cell(row_idx, c, value=val)

        self.wb.save(self.output_path)
        return row_idx
