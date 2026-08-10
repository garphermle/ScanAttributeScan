"""
Resource locator for embedded template Excel file.
"""

import os
import sys

def get_default_excel_path() -> str:
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    resource_path = os.path.join(base_dir, "resources", "Excel_FormMau.xlsx")
    if os.path.exists(resource_path):
        return resource_path
    
    # Fallback to current working directory resources
    cwd_path = os.path.join(os.getcwd(), "resources", "Excel_FormMau.xlsx")
    if os.path.exists(cwd_path):
        return cwd_path

    # Fallback to hardcoded source root path if present
    fallback = "/home/garpherm/VNPT/Source/Excel_FormMau_v5_04082026.xlsx"
    if os.path.exists(fallback):
        return fallback
        
    return resource_path

