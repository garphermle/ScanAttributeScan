"""
High-performance PDF Indexer for local and LAN network shared folders.
Handles fast indexing and flexible serial-to-filename matching for 22,000+ files with caching.
"""

import os
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple


def normalize_serial_token(s: str) -> str:
    """
    Normalizes a serial or filename string to a canonical alphanumeric token:
    - Lowercase
    - Removes whitespace, dashes, underscores, dots, and common suffixes/prefixes
    Example: 'A 03835490' -> 'a03835490'
             'A0 248729-GCN.pdf' -> 'a0248729'
             'AA 03835094' -> 'aa03835094'
    """
    if not s:
        return ""
    
    # Strip extension if present
    base = os.path.splitext(s)[0]
    base = unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode('utf-8')
    base = base.lower()

    # Remove known tag words if separated by delimiter
    base = re.sub(r'[\s_\-]+(gcn|gtk|gt|so|bia|trang[\d]+|scan|doc|phuluc).*$', '', base, flags=re.IGNORECASE)
    # Remove all non-alphanumeric characters
    cleaned = re.sub(r'[^a-z0-9]', '', base)
    return cleaned


def extract_raw_tokens(s: str) -> List[str]:
    """Extracts alphanumeric chunks from a string."""
    if not s:
        return []
    base = os.path.splitext(s)[0]
    base = unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode('utf-8').lower()
    tokens = [re.sub(r'[^a-z0-9]', '', part) for part in re.split(r'[\s_\-]+', base) if part.strip()]
    return [t for t in tokens if t]


class PDFIndexer:
    def __init__(self, root_dir: str = ""):
        self.root_dir = root_dir
        self.all_pdf_paths: List[str] = []
        # Normalized key -> list of full file paths
        self.token_to_paths: Dict[str, List[str]] = {}
        # Raw basename lowercase -> full path
        self.basename_to_path: Dict[str, str] = {}
        # List of (normalized_base, full_path) for fallback search
        self.file_entries: List[Tuple[str, str]] = []
        # Lookup cache for instant 0ms responses
        self._lookup_cache: Dict[str, List[str]] = {}
        self._is_indexed = False

        if root_dir and os.path.exists(root_dir):
            self.index_directory(root_dir)

    def index_directory(self, root_dir: str, recursive: bool = True):
        """
        Scans root_dir and builds fast lookup indices.
        Optimized with os.scandir to process 22,000+ files in milliseconds.
        """
        self.root_dir = root_dir
        self.all_pdf_paths.clear()
        self.token_to_paths.clear()
        self.basename_to_path.clear()
        self.file_entries.clear()
        self._lookup_cache.clear()

        if not root_dir or not os.path.exists(root_dir):
            self._is_indexed = True
            return

        def _scan_dir(path: str):
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            if not entry.name.startswith('.') and not entry.name.startswith('_') and entry.name != '__pycache__':
                                if recursive:
                                    _scan_dir(entry.path)
                        elif entry.is_file(follow_symlinks=False) and entry.name.lower().endswith('.pdf'):
                            self._add_pdf(entry.path, entry.name)
            except Exception:
                pass

        _scan_dir(root_dir)
        self._is_indexed = True

    def _add_pdf(self, full_path: str, filename: str):
        self.all_pdf_paths.append(full_path)
        fn_lower = filename.lower()
        self.basename_to_path[fn_lower] = full_path

        norm_token = normalize_serial_token(filename)
        if norm_token:
            if norm_token not in self.token_to_paths:
                self.token_to_paths[norm_token] = []
            if full_path not in self.token_to_paths[norm_token]:
                self.token_to_paths[norm_token].append(full_path)

        # Also index combined raw tokens
        raw_chunks = extract_raw_tokens(filename)
        combined_chunks = "".join(raw_chunks)
        if combined_chunks and combined_chunks != norm_token:
            if combined_chunks not in self.token_to_paths:
                self.token_to_paths[combined_chunks] = []
            if full_path not in self.token_to_paths[combined_chunks]:
                self.token_to_paths[combined_chunks].append(full_path)

        self.file_entries.append((norm_token, full_path))

    def find_pdfs_for_serial(self, serial: str) -> List[str]:
        """
        Finds matching PDF file(s) for a given serial in O(1) time.
        Returns list of full paths, ordered with GCN first, then GT, GTK, others.
        """
        if not serial or not str(serial).strip():
            return []

        clean_serial = str(serial).strip()
        if clean_serial in self._lookup_cache:
            return list(self._lookup_cache[clean_serial])

        norm_serial = normalize_serial_token(clean_serial)
        results: List[str] = []
        seen_paths: Set[str] = set()

        # 1. Exact normalized token match (O(1))
        if norm_serial and norm_serial in self.token_to_paths:
            for p in self.token_to_paths[norm_serial]:
                if p not in seen_paths:
                    results.append(p)
                    seen_paths.add(p)

        # 2. Check direct basename with .pdf (O(1))
        direct_name = f"{clean_serial.lower()}.pdf"
        if direct_name in self.basename_to_path:
            p = self.basename_to_path[direct_name]
            if p not in seen_paths:
                results.append(p)
                seen_paths.add(p)

        # 3. Only if no exact matches found, check prefix match
        if not results and norm_serial and len(norm_serial) >= 3:
            for norm_base, full_path in self.file_entries:
                if full_path in seen_paths:
                    continue
                if norm_base.startswith(norm_serial) or norm_serial.startswith(norm_base) or norm_serial in norm_base:
                    results.append(full_path)
                    seen_paths.add(full_path)

        # Sort results: GCN -> GT -> GTK -> others
        def _sort_key(p: str) -> int:
            fn = os.path.basename(p).lower()
            if 'gcn' in fn:
                return 0
            if 'gtk' in fn:
                return 2
            if 'gt' in fn:
                return 1
            return 3

        results.sort(key=_sort_key)
        self._lookup_cache[clean_serial] = results
        return list(results)

    @property
    def total_indexed_count(self) -> int:
        return len(self.all_pdf_paths)
