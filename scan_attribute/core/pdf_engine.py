"""
PDF Engine for rendering pages using pypdfium2 and PySide6 QImage.
"""

import os
from typing import List, Optional, Tuple
import pypdfium2 as pdfium
from PySide6.QtGui import QImage, QPixmap
import numpy as np

class PDFEngine:
    def __init__(self):
        self.doc: Optional[pdfium.PdfDocument] = None
        self.filepath: Optional[str] = None
        self.page_count: int = 0

    def load_file(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        try:
            if self.doc:
                self.doc.close()
            self.filepath = filepath
            self.doc = pdfium.PdfDocument(filepath)
            self.page_count = len(self.doc)
            return True
        except Exception as e:
            print(f"Error loading PDF {filepath}: {e}")
            self.doc = None
            self.page_count = 0
            return False

    def render_page_qpixmap(self, page_index: int, scale: float = 2.0, rotation: int = 0) -> Tuple[Optional[QPixmap], Optional[np.ndarray]]:
        if not self.doc or not (0 <= page_index < self.page_count):
            return None, None
        try:
            page = self.doc[page_index]
            bitmap = page.render(scale=scale, rotation=rotation)
            pil_image = bitmap.to_pil()
            img_np = np.array(pil_image)
            
            # Convert RGBA or RGB to QImage
            height, width, channel = img_np.shape
            bytes_per_line = channel * width
            
            if channel == 4:
                qimg = QImage(img_np.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
            else:
                qimg = QImage(img_np.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                
            pixmap = QPixmap.fromImage(qimg)
            return pixmap, img_np
        except Exception as e:
            print(f"Error rendering PDF page {page_index}: {e}")
            return None, None

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
            self.page_count = 0
