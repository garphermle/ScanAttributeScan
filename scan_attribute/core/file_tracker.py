"""
File Tracker module for persisting and retrieving Excel row mappings for individual PDF files and folders.
Saves mapping locally on disk so users can easily revisit and edit exact rows across sessions.
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime


class FileTracker:
    def __init__(self, root_dir: str = "", excel_path: str = ""):
        self.root_dir = root_dir
        self.excel_path = excel_path
        self.mapping_file = ""
        self.data: Dict[str, Any] = {
            "excel_path": excel_path,
            "files": {},   # normalized_path -> { "row": 5, "stt": 1, "serial": "...", "updated_at": "..." }
            "folders": {}  # normalized_path -> { "row": 5, "stt": 1, "serial": "...", "updated_at": "..." }
        }
        if root_dir:
            self.load(root_dir, excel_path)

    def _get_mapping_file_path(self, root_dir: str) -> str:
        if root_dir and os.path.exists(root_dir):
            return os.path.join(root_dir, ".scan_attribute_history.json")
        home_dir = os.path.expanduser("~/.config/scan_attribute")
        os.makedirs(home_dir, exist_ok=True)
        return os.path.join(home_dir, "scan_history.json")

    def load(self, root_dir: str, excel_path: str = ""):
        """Loads persistent file history from JSON on disk."""
        self.root_dir = root_dir
        self.excel_path = excel_path or self.excel_path
        self.mapping_file = self._get_mapping_file_path(root_dir)

        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data["files"] = loaded.get("files", {})
                        self.data["folders"] = loaded.get("folders", {})
            except Exception:
                pass

    def save_to_disk(self):
        """Persists current mappings to disk."""
        if not self.mapping_file:
            self.mapping_file = self._get_mapping_file_path(self.root_dir)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _normalize_key(self, path: str) -> str:
        return os.path.abspath(path).lower() if path else ""

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieves row info for a specific PDF file."""
        key = self._normalize_key(file_path)
        if key in self.data["files"]:
            return self.data["files"][key]
        # Fallback to matching basename
        base = os.path.basename(file_path).lower()
        for k, v in self.data["files"].items():
            if os.path.basename(k).lower() == base:
                return v
        return None

    def get_folder_info(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """Retrieves row info for a folder."""
        key = self._normalize_key(folder_path)
        if key in self.data["folders"]:
            return self.data["folders"][key]
        base = os.path.basename(folder_path).lower()
        for k, v in self.data["folders"].items():
            if os.path.basename(k).lower() == base:
                return v
        return None

    def record_file_saved(self, file_path: str, row: int, stt: int, serial: str):
        """Records that a specific PDF file was saved to a specific Excel row."""
        key = self._normalize_key(file_path)
        self.data["files"][key] = {
            "row": row,
            "stt": stt,
            "serial": serial,
            "file_name": os.path.basename(file_path),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_to_disk()

    def record_folder_saved(self, folder_path: str, row: int, stt: int, serial: str):
        """Records that a folder was saved to a specific Excel row."""
        key = self._normalize_key(folder_path)
        self.data["folders"][key] = {
            "row": row,
            "stt": stt,
            "serial": serial,
            "folder_name": os.path.basename(folder_path),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_to_disk()

    def get_all_file_mappings(self) -> Dict[str, Dict[str, Any]]:
        return self.data["files"]

    def get_all_folder_mappings(self) -> Dict[str, Dict[str, Any]]:
        return self.data["folders"]
