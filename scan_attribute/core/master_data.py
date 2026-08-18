"""
Resource locator for embedded template Excel files and auxiliary datasets.
"""

import os
import sys


def get_resource_file_path(filename: str) -> str:
    """
    Locates a resource file across:
    1. PyInstaller frozen environment (_MEIPASS, _internal, or exe dir).
    2. Package resources directory.
    3. Source tree / development directory.
    4. Current Working Directory.
    """
    candidates = []

    # 1. PyInstaller Frozen Environment
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(os.path.join(meipass, "scan_attribute", "resources", filename))
            candidates.append(os.path.join(meipass, "resources", filename))
            candidates.append(os.path.join(meipass, filename))

        # PyInstaller 6+ onedir directory structure (_internal folder)
        internal_dir = os.path.join(exe_dir, "_internal")
        candidates.append(os.path.join(internal_dir, "scan_attribute", "resources", filename))
        candidates.append(os.path.join(internal_dir, "resources", filename))
        candidates.append(os.path.join(internal_dir, filename))

        # Direct executable folder
        candidates.append(os.path.join(exe_dir, "scan_attribute", "resources", filename))
        candidates.append(os.path.join(exe_dir, "resources", filename))
        candidates.append(os.path.join(exe_dir, filename))

    # 2. Source Tree / Installed Package directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(base_dir, "resources", filename))
    candidates.append(os.path.join(os.path.dirname(base_dir), "scan_attribute", "resources", filename))
    candidates.append(os.path.join(base_dir, filename))

    # 3. Current Working Directory
    candidates.append(os.path.join(os.getcwd(), "scan_attribute", "resources", filename))
    candidates.append(os.path.join(os.getcwd(), "resources", filename))
    candidates.append(os.path.join(os.getcwd(), filename))

    # 4. Known development paths
    if filename == "Excel_FormMau.xlsx":
        candidates.append("/home/garpherm/VNPT/Source/Excel_FormMau_v5_04082026.xlsx")
        candidates.append("/home/garpherm/VNPT/Source/scan_attribute/scan_attribute/resources/Excel_FormMau.xlsx")
    elif filename == "QNH_ThongTinDoDac.xlsx":
        candidates.append("/home/garpherm/VNPT/Source/scan_attribute/Copy of QNH_ThongTinDoDac.xlsx")
        candidates.append("/home/garpherm/VNPT/Source/scan_attribute/scan_attribute/resources/QNH_ThongTinDoDac.xlsx")

    for p in candidates:
        if p and os.path.exists(p):
            return p

    # Fallback to plausible location
    if getattr(sys, 'frozen', False):
        internal_dir = os.path.join(os.path.dirname(sys.executable), "_internal")
        if os.path.isdir(internal_dir):
            return os.path.join(internal_dir, "scan_attribute", "resources", filename)
    return os.path.join(base_dir, "resources", filename)


def get_default_excel_path() -> str:
    """Returns absolute path to Excel_FormMau.xlsx."""
    return get_resource_file_path("Excel_FormMau.xlsx")


def get_measurement_excel_path() -> str:
    """Returns absolute path to QNH_ThongTinDoDac.xlsx."""
    return get_resource_file_path("QNH_ThongTinDoDac.xlsx")


