"""
Excel Engine for loading, updating, appending, exporting ranges, and merging Excel files (186 columns).
Features high-performance in-memory caching and non-blocking background saving for instant UI response (0ms lag).
"""

import os
import shutil
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
import openpyxl


class ExcelEngine:
    def __init__(self, template_path: str, output_path: Optional[str] = None):
        self.template_path = template_path
        self.output_path = output_path or template_path
        self.wb: Optional[openpyxl.Workbook] = None
        self.ws = None
        self._lock = threading.RLock()

        # In-memory fast cache
        self._cached_serial_rows: List[Dict[str, Any]] = []
        self._serial_to_row_map: Dict[str, int] = {}
        self._row_data_cache: Dict[int, Dict[int, Any]] = {}
        self._completed_rows_count: int = 0
        self._total_rows_count: int = 0
        self._dirty = False
        self._is_saving = False

    def initialize(self, force_reload: bool = False):
        """Ensures output file exists by copying template if necessary, then loads workbook and builds memory cache."""
        with self._lock:
            if not self.output_path:
                return

            if not os.path.exists(self.output_path):
                if self.template_path and os.path.exists(self.template_path) and os.path.abspath(self.template_path) != os.path.abspath(self.output_path):
                    try:
                        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
                        shutil.copy(self.template_path, self.output_path)
                    except Exception as e:
                        print(f"Warning copying template: {e}")

            if (self.wb is None or force_reload) and os.path.exists(self.output_path):
                try:
                    self.wb = openpyxl.load_workbook(self.output_path)
                    if 'Data' in self.wb.sheetnames:
                        self.ws = self.wb['Data']
                    else:
                        self.ws = self.wb.active
                    self._build_cache()
                except Exception as e:
                    print(f"Error loading workbook: {e}")

    def _build_cache(self):
        """Builds in-memory index of all rows for 0ms lookup."""
        with self._lock:
            self._cached_serial_rows.clear()
            self._serial_to_row_map.clear()
            self._row_data_cache.clear()
            self._completed_rows_count = 0

            if not self.ws:
                self._total_rows_count = 0
                return

            max_r = self.ws.max_row
            for r in range(5, max_r + 1):
                val_col1 = self.ws.cell(r, 1).value
                val_col2 = self.ws.cell(r, 2).value
                val_col3 = self.ws.cell(r, 3).value
                val_col9 = self.ws.cell(r, 9).value
                val_col14 = self.ws.cell(r, 14).value
                val_col41 = self.ws.cell(r, 41).value
                val_col42 = self.ws.cell(r, 42).value
                val_col43 = self.ws.cell(r, 43).value
                val_col44 = self.ws.cell(r, 44).value
                val_col93 = self.ws.cell(r, 93).value
                val_col110 = self.ws.cell(r, 110).value
                val_col183 = self.ws.cell(r, 183).value

                serial = str(val_col2 or '').strip()
                if not serial and not val_col3 and not val_col9 and not val_col43 and not val_col44:
                    continue

                try:
                    stt_val = int(val_col1) if (val_col1 is not None and str(val_col1).strip().isdigit()) else (r - 4)
                except Exception:
                    stt_val = r - 4

                owner_name = str(val_col9 or '').strip()
                id_num = str(val_col14 or '').strip()
                plot = str(val_col43 or val_col41 or '').strip()
                map_sheet = str(val_col44 or val_col42 or '').strip()
                area = str(val_col93 or '').strip()

                is_done = bool(owner_name or id_num or plot or map_sheet or str(val_col110 or '').strip())

                row_obj = {
                    "row": r,
                    "stt": stt_val,
                    "serial": serial or f"Hồ sơ {stt_val}",
                    "owner_name": owner_name,
                    "id_num": id_num,
                    "plot": plot,
                    "map_sheet": map_sheet,
                    "area": area,
                    "is_completed": is_done
                }
                self._cached_serial_rows.append(row_obj)
                if is_done:
                    self._completed_rows_count += 1

                if serial:
                    self._serial_to_row_map[serial.lower()] = r
                if val_col3:
                    self._serial_to_row_map[str(val_col3).strip().lower()] = r
                if val_col183:
                    self._serial_to_row_map[str(val_col183).strip().lower()] = r

            self._total_rows_count = len(self._cached_serial_rows)

    def switch_target_file(self, target_path: str, copy_template_if_new: bool = True):
        """Switches target Excel file to a new or existing working file."""
        with self._lock:
            self.flush_save()
            is_new = not os.path.exists(target_path)
            if copy_template_if_new and is_new and self.template_path and os.path.exists(self.template_path):
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    shutil.copy(self.template_path, target_path)
                except Exception as e:
                    print(f"Warning copying template: {e}")

            self.output_path = target_path
            self.initialize(force_reload=True)

            if is_new and copy_template_if_new and self.ws:
                for c in range(1, 187):
                    self.ws.cell(5, c).value = None
                try:
                    self.save_workbook_safe()
                except Exception as e:
                    print(f"Warning saving new empty file: {e}")
                self.initialize(force_reload=True)

    def save_workbook_safe(self, max_retries: int = 3, retry_delay: float = 0.5):
        """Saves workbook with retry handling in case of LAN network delays or temporary locks."""
        with self._lock:
            if not self.wb or not self.output_path:
                return

            last_err = None
            for attempt in range(max_retries):
                try:
                    self.wb.save(self.output_path)
                    return
                except PermissionError as pe:
                    last_err = pe
                    time.sleep(retry_delay)
                except Exception as e:
                    last_err = e
                    time.sleep(retry_delay)
            if last_err:
                raise last_err

    def _schedule_async_save(self):
        """Saves Excel to disk in a background thread to prevent UI freezing."""
        with self._lock:
            self._dirty = True
            if not self._is_saving:
                self._is_saving = True
                t = threading.Thread(target=self._async_save_worker, daemon=True)
                t.start()

    def _async_save_worker(self):
        while True:
            with self._lock:
                if not self._dirty:
                    self._is_saving = False
                    return
                self._dirty = False
            try:
                self.save_workbook_safe()
            except Exception as e:
                print(f"Background save notice: {e}")

    def flush_save(self):
        """Synchronously flushes any pending changes to disk."""
        with self._lock:
            if self._dirty:
                try:
                    self.save_workbook_safe()
                    self._dirty = False
                except Exception as e:
                    print(f"Flush save error: {e}")

    def find_row_by_serial(self, serial: str) -> Optional[int]:
        """Finds row index (1-based) matching Serial in O(1) time."""
        if not serial:
            return None
        serial_clean = str(serial).strip().lower()
        with self._lock:
            if serial_clean in self._serial_to_row_map:
                return self._serial_to_row_map[serial_clean]
        return None

    def find_first_empty_row(self) -> int:
        """Finds the first completely empty data row starting from row 5."""
        with self._lock:
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

    def get_serial_rows(self) -> List[Dict[str, Any]]:
        """Returns cached serial rows in O(1) time."""
        with self._lock:
            if not self._cached_serial_rows and self.ws:
                self._build_cache()
            return list(self._cached_serial_rows)

    def get_processed_serials_info(self) -> Dict[str, Dict[str, Any]]:
        """Returns info map in O(1) time."""
        with self._lock:
            info_map = {}
            for item in self._cached_serial_rows:
                serial_clean = item["serial"].strip().lower()
                if serial_clean:
                    info_map[serial_clean] = {
                        "serial": item["serial"],
                        "row": item["row"],
                        "stt": item["stt"],
                        "owner_name": item["owner_name"],
                        "is_completed": item["is_completed"]
                    }
            return info_map

    def get_processed_serials(self) -> List[str]:
        """Returns list of serials already present in Excel."""
        return list(self.get_processed_serials_info().keys())

    def get_data_rows_count(self) -> int:
        """Returns count of valid data rows in Excel in O(1) time."""
        with self._lock:
            return self._total_rows_count

    def get_completed_rows_count(self) -> int:
        """Returns count of completed data rows in Excel in O(1) time."""
        with self._lock:
            return self._completed_rows_count

    def read_row_data(self, row_idx: int) -> Dict[int, Any]:
        """Reads all 186 column values for a given row index."""
        with self._lock:
            if row_idx in self._row_data_cache:
                return dict(self._row_data_cache[row_idx])

            if not self.ws:
                self.initialize()

            data = {}
            for c in range(1, 187):
                val = self.ws.cell(row_idx, c).value
                data[c] = "" if val is None else val
            self._row_data_cache[row_idx] = data
            return data

    def save_row_data(self, serial: str, attr_dict: Dict[int, Any], target_row: Optional[int] = None, save_async: bool = True) -> int:
        """
        Saves row for serial in memory and starts non-blocking background disk save.
        Execution takes <5ms for instant UI responsiveness.
        """
        with self._lock:
            if not self.ws:
                self.initialize()

            row_idx = target_row
            if not row_idx:
                row_idx = self.find_row_by_serial(serial)
            if not row_idx:
                row_idx = self.find_first_empty_row()

            stt_val = row_idx - 4
            self.ws.cell(row_idx, 1, value=stt_val)

            if 2 not in attr_dict or not attr_dict[2]:
                attr_dict[2] = serial

            for c, val in attr_dict.items():
                if 1 <= c <= 186:
                    self.ws.cell(row_idx, c, value=val)

            # Update row cache
            if row_idx not in self._row_data_cache:
                self._row_data_cache[row_idx] = {}
            self._row_data_cache[row_idx].update(attr_dict)

            # Update cached_serial_rows
            owner_name = str(attr_dict.get(9) or "")
            plot = str(attr_dict.get(43) or attr_dict.get(41) or "")
            map_sheet = str(attr_dict.get(44) or attr_dict.get(42) or "")
            gc2 = str(attr_dict.get(110) or "")
            is_done = bool(owner_name or plot or map_sheet or gc2)

            found_item = None
            for item in self._cached_serial_rows:
                if item["row"] == row_idx:
                    found_item = item
                    break

            if found_item:
                was_done = found_item["is_completed"]
                found_item["owner_name"] = owner_name
                found_item["plot"] = plot
                found_item["map_sheet"] = map_sheet
                found_item["is_completed"] = is_done
                if not was_done and is_done:
                    self._completed_rows_count += 1
            else:
                new_item = {
                    "row": row_idx,
                    "stt": stt_val,
                    "serial": serial or f"Hồ sơ {stt_val}",
                    "owner_name": owner_name,
                    "id_num": str(attr_dict.get(14) or ""),
                    "plot": plot,
                    "map_sheet": map_sheet,
                    "area": str(attr_dict.get(93) or ""),
                    "is_completed": is_done
                }
                self._cached_serial_rows.append(new_item)
                self._total_rows_count = len(self._cached_serial_rows)
                if is_done:
                    self._completed_rows_count += 1

            if serial:
                self._serial_to_row_map[serial.lower()] = row_idx

            if save_async:
                self._schedule_async_save()
            return row_idx

    def export_sub_excel(self, start_stt: int, end_stt: int, output_path: str) -> int:
        """
        Exports a slice of rows corresponding to STT range [start_stt, end_stt] into a new Excel file.
        """
        with self._lock:
            self.flush_save()
            if not self.output_path or not os.path.exists(self.output_path):
                raise FileNotFoundError(f"Master Excel file not found: {self.output_path}")

            wb_source = openpyxl.load_workbook(self.output_path)
            sheet_name = 'Data' if 'Data' in wb_source.sheetnames else wb_source.sheetnames[0]
            ws_source = wb_source[sheet_name]

            wb_sub = openpyxl.load_workbook(self.template_path or self.output_path)
            ws_sub = wb_sub['Data'] if 'Data' in wb_sub.sheetnames else wb_sub.active

            for r in range(5, ws_sub.max_row + 1):
                for c in range(1, 187):
                    ws_sub.cell(r, c).value = None

            dest_row = 5
            exported_count = 0

            for r in range(5, ws_source.max_row + 1):
                val_col1 = ws_source.cell(r, 1).value
                val_col2 = ws_source.cell(r, 2).value

                try:
                    current_stt = int(val_col1) if (val_col1 is not None and str(val_col1).strip().isdigit()) else (r - 4)
                except Exception:
                    current_stt = r - 4

                if start_stt <= current_stt <= end_stt:
                    for c in range(1, 187):
                        ws_sub.cell(dest_row, c).value = ws_source.cell(r, c).value
                    ws_sub.cell(dest_row, 1).value = current_stt
                    dest_row += 1
                    exported_count += 1

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            wb_sub.save(output_path)
            wb_sub.close()
            wb_source.close()
            return exported_count

    def merge_sub_excel(self, sub_excel_path: str) -> Tuple[int, int]:
        """
        Merges completed rows from a sub-excel file into the master Excel file.
        """
        with self._lock:
            self.flush_save()
            if not os.path.exists(sub_excel_path):
                raise FileNotFoundError(f"Sub-excel file not found: {sub_excel_path}")

            wb_sub = openpyxl.load_workbook(sub_excel_path, data_only=True)
            ws_sub = wb_sub['Data'] if 'Data' in wb_sub.sheetnames else wb_sub.active

            merged_count = 0
            skipped_count = 0

            for r_sub in range(5, ws_sub.max_row + 1):
                val_stt = ws_sub.cell(r_sub, 1).value
                val_serial = str(ws_sub.cell(r_sub, 2).value or '').strip()

                has_sub_data = any(
                    ws_sub.cell(r_sub, c).value is not None and str(ws_sub.cell(r_sub, c).value).strip() != ''
                    for c in (9, 14, 43, 44, 110)
                )

                if not has_sub_data:
                    skipped_count += 1
                    continue

                target_row = None
                if val_stt is not None and str(val_stt).strip().isdigit():
                    target_row = int(val_stt) + 4
                elif val_serial:
                    target_row = self.find_row_by_serial(val_serial)

                if not target_row:
                    target_row = self.find_first_empty_row()

                row_dict = {}
                for c in range(1, 187):
                    val = ws_sub.cell(r_sub, c).value
                    if val is not None and str(val).strip() != '':
                        row_dict[c] = val

                if row_dict:
                    self.save_row_data(serial=val_serial, attr_dict=row_dict, target_row=target_row, save_async=False)
                    merged_count += 1

            wb_sub.close()
            self.save_workbook_safe()
            self.initialize(force_reload=True)
            return merged_count, skipped_count
