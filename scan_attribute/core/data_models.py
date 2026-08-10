"""
Data models and Master Data Loader for ScanAttribute.
Maps to Excel_FormMau_v5_04082026.xlsx (186 columns).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import datetime
import openpyxl


def parse_date_flexible(date_str: str) -> str:
    """Supports flexible date format like 1/5/2026 or 01/05/2026."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%Y"):
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return date_str


@dataclass
class CommuneInfo:
    code_3cap: str
    name_3cap: str
    district: str
    province: str
    code_2cap: str = ""
    name_2cap: str = ""

    @property
    def full_location(self) -> str:
        parts = [self.name_3cap, self.district, self.province]
        return ", ".join(p for p in parts if p)


@dataclass
class LandTypeInfo:
    code: str
    name: str
    note: str = ""


class MasterDataManager:
    def __init__(self):
        self.communes: List[CommuneInfo] = []
        self.communes_by_code: Dict[str, CommuneInfo] = {}
        self.land_types: List[LandTypeInfo] = []
        self.land_types_by_code: Dict[str, LandTypeInfo] = {}
        self.ethnicities: List[str] = ["Kinh"]
        self.nationalities: List[str] = ["Việt Nam"]
        self.id_types: List[str] = ["CCCD", "CMND", "Hộ chiếu"]
        self.land_use_origins: List[str] = []

    def load_from_excel(self, excel_path: str):
        try:
            wb = openpyxl.load_workbook(excel_path, data_only=True)
            
            # Load Communes (MaXa_3cap_2cap)
            if 'MaXa_3cap_2cap' in wb.sheetnames:
                ws = wb['MaXa_3cap_2cap']
                self.communes.clear()
                self.communes_by_code.clear()
                for r in range(2, ws.max_row + 1):
                    code_3 = str(ws.cell(r, 2).value or '').strip()
                    name_3 = str(ws.cell(r, 3).value or '').strip()
                    dist = str(ws.cell(r, 4).value or '').strip()
                    prov = str(ws.cell(r, 5).value or '').strip()
                    code_2 = str(ws.cell(r, 6).value or '').strip()
                    name_2 = str(ws.cell(r, 7).value or '').strip()
                    if name_3:
                        c_info = CommuneInfo(
                            code_3cap=code_3,
                            name_3cap=name_3,
                            district=dist,
                            province=prov,
                            code_2cap=code_2,
                            name_2cap=name_2
                        )
                        self.communes.append(c_info)
                        if code_3:
                            self.communes_by_code[code_3] = c_info

            # Load Land Types (DM_LoaiDat)
            if 'DM_LoaiDat' in wb.sheetnames:
                ws = wb['DM_LoaiDat']
                self.land_types.clear()
                self.land_types_by_code.clear()
                for r in range(2, ws.max_row + 1):
                    code = str(ws.cell(r, 1).value or '').strip()
                    name = str(ws.cell(r, 2).value or '').strip()
                    note = str(ws.cell(r, 3).value or '').strip()
                    if code and name:
                        lt = LandTypeInfo(code=code, name=name, note=note)
                        self.land_types.append(lt)
                        self.land_types_by_code[code] = lt

            # Load Ethnicities
            if 'DM_DanToc' in wb.sheetnames:
                ws = wb['DM_DanToc']
                eth = [str(ws.cell(r, 2).value or '').strip() for r in range(2, ws.max_row + 1)]
                self.ethnicities = [e for e in eth if e]

            # Load Nationalities
            if 'DM_QuocTich' in wb.sheetnames:
                ws = wb['DM_QuocTich']
                nats = [str(ws.cell(r, 2).value or '').strip() for r in range(2, ws.max_row + 1)]
                self.nationalities = [n for n in nats if n]

            # Load Land Use Origins
            if 'DM_NguonGocSuDungDat' in wb.sheetnames:
                ws = wb['DM_NguonGocSuDungDat']
                origins = [str(ws.cell(r, 1).value or '').strip() for r in range(2, ws.max_row + 1)]
                self.land_use_origins = [o for o in origins if o]

        except Exception as e:
            print(f"Error loading master data from {excel_path}: {e}")
