"""
PDF Viewer Widget based on QGraphicsView / QGraphicsScene architecture (matching pdfsplit_ai).
Features normal mouse panning, Shift+Drag Crop OCR selection mode, and Ctrl+MouseWheel zooming under mouse cursor.
"""

import os
import re
from typing import Optional, List
import numpy as np
import cv2

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QRubberBand, QTabWidget, QToolBar, QToolTip, QFileDialog, QFrame, QApplication,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, Signal, QRect, QRectF, QPoint, QSize, QBuffer, QIODevice


class PDFPageCanvas(QGraphicsView):
    area_crop_selected = Signal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

        self._pixmap_items: List[QGraphicsPixmapItem] = []
        self.ocr_crop_mode = False
        self._is_selecting = False
        self._origin_point = QPoint()
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())

    def set_ocr_crop_mode(self, enabled: bool):
        self.ocr_crop_mode = enabled
        if enabled:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def set_pages(self, pixmaps: List[QPixmap]):
        self._scene.clear()
        self._pixmap_items.clear()

        current_y = 0
        gap = 4  # Minimal gap so pages are attached continuously right beneath each other
        max_width = 0

        for pixmap in pixmaps:
            if pixmap.isNull():
                continue
            item = QGraphicsPixmapItem(pixmap)
            item.setPos(0, current_y)
            self._scene.addItem(item)
            self._pixmap_items.append(item)
            current_y += pixmap.height() + gap
            if pixmap.width() > max_width:
                max_width = pixmap.width()

        self._scene.setSceneRect(-10, -10, max_width + 20, max(current_y + 10, 200))

    def mousePressEvent(self, event):
        # Trigger Crop OCR only if ocr_crop_mode is ON or Shift key is held!
        if event.button() == Qt.MouseButton.LeftButton and (self.ocr_crop_mode or (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self._is_selecting = True
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            pos = event.position().toPoint()
            self._origin_point = pos
            self._rubber_band.setGeometry(QRect(pos, QSize()))
            self._rubber_band.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, "_is_selecting", False):
            pos = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._origin_point, pos).normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "_is_selecting", False):
            self._is_selecting = False
            self._rubber_band.hide()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            rect = self._rubber_band.geometry()

            if rect.width() > 5 and rect.height() > 5 and self._pixmap_items:
                scene_rect = self.mapToScene(rect).boundingRect()

                for item in self._pixmap_items:
                    item_scene_rect = item.sceneBoundingRect()
                    intersected = scene_rect.intersected(item_scene_rect)
                    if not intersected.isEmpty() and intersected.width() > 3 and intersected.height() > 3:
                        local_rect = QRectF(
                            intersected.x() - item.x(),
                            intersected.y() - item.y(),
                            intersected.width(),
                            intersected.height()
                        ).toRect()

                        cropped_pixmap = item.pixmap().copy(local_rect)
                        if not cropped_pixmap.isNull():
                            qimg = cropped_pixmap.toImage()
                            buffer = QBuffer()
                            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                            qimg.save(buffer, "PNG")
                            image_bytes = bytes(buffer.data())
                            buffer.close()

                            arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                            if arr is not None:
                                self.area_crop_selected.emit(arr)
                                break
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
            self.scale(factor, factor)
            event.accept()
        else:
            # Smooth mouse wheel scrolling continuously up/down attached pages
            delta = event.angleDelta().y()
            if delta != 0:
                v_bar = self.verticalScrollBar()
                v_bar.setValue(v_bar.value() - delta)
                event.accept()
            else:
                super().wheelEvent(event)


class PDFViewerWidget(QWidget):
    ocr_text_captured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_engine = PDFEngine()
        self.ocr_engine = OCREngine()
        self.current_folder = ""
        self.current_pdf_path = ""
        self.current_page = 0
        self.scale_factor = 2.0
        self.rotation = 0
        self.pdf_file_map = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Tab bar for switching files: GCN, GT, GTK
        self.tab_bar = QTabWidget()
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        # Compact controls bar
        controls_bar = QFrame()
        controls_bar.setStyleSheet("""
            QFrame {
                background-color: #eef2f5;
                border-bottom: 1px solid #cfd8dc;
                padding: 2px;
            }
            QPushButton {
                padding: 3px 8px;
                font-size: 12px;
            }
        """)
        toolbar = QHBoxLayout(controls_bar)
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        # File status label
        self.lbl_current_file = QLabel("📄 PDF: Chưa mở file")
        self.lbl_current_file.setStyleSheet("font-weight: bold; color: #0d47a1; font-size: 12px;")
        toolbar.addWidget(self.lbl_current_file)

        toolbar.addStretch()

        # Crop OCR Mode Toggle Button
        self.btn_ocr_mode = QPushButton("🔍 Quét vùng (Shift+Kéo)")
        self.btn_ocr_mode.setCheckable(True)
        self.btn_ocr_mode.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: #333; font-weight: bold; }
            QPushButton:checked { background-color: #e65100; color: white; }
        """)
        self.btn_ocr_mode.toggled.connect(self._toggle_ocr_mode)
        toolbar.addWidget(self.btn_ocr_mode)

        # Controls: Open external, Page nav, Zoom, Rotate
        self.btn_open_external = QPushButton("📂 Mở PDF")
        self.btn_open_external.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold;")
        self.btn_open_external.clicked.connect(self.select_external_pdf)

        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.lbl_page = QLabel("0/0")
        self.lbl_page.setStyleSheet("font-weight: bold; font-size: 12px; padding: 0 4px;")

        self.btn_zoom_in = QPushButton("🔍 +")
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_rotate_l = QPushButton("↶ Trái")
        self.btn_rotate_r = QPushButton("↷ Phải")

        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_rotate_l.clicked.connect(self.rotate_left)
        self.btn_rotate_r.clicked.connect(self.rotate_right)

        toolbar.addWidget(self.btn_open_external)
        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(self.btn_next)
        toolbar.addWidget(self.btn_zoom_in)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_rotate_l)
        toolbar.addWidget(self.btn_rotate_r)

        layout.addWidget(controls_bar)

        # High Performance QGraphicsView Canvas (matching pdfsplit_ai)
        self.canvas = PDFPageCanvas()
        self.canvas.area_crop_selected.connect(self._handle_crop_ocr)
        self.canvas.verticalScrollBar().valueChanged.connect(self._on_scroll)

        layout.addWidget(self.canvas, stretch=1)

    def _toggle_ocr_mode(self, checked: bool):
        self.canvas.set_ocr_crop_mode(checked)
        if checked:
            self.btn_ocr_mode.setText("🔍 ĐANG QUÉT VÙNG (Kéo chuột)")
        else:
            self.btn_ocr_mode.setText("🔍 Quét vùng (Shift+Kéo)")

    def select_external_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file PDF bên ngoài để xem và OCR", "", "File PDF (*.pdf)"
        )
        if file_path:
            self.load_single_pdf(file_path)

    def load_single_pdf(self, pdf_path: str):
        self.tab_bar.blockSignals(True)
        self.tab_bar.clear()
        self.pdf_file_map.clear()

        filename = os.path.basename(pdf_path)
        self.tab_bar.addTab(QWidget(), f"📄 {filename}")
        self.tab_bar.tabBar().setTabData(0, pdf_path)
        self.pdf_file_map[0] = pdf_path

        self.tab_bar.blockSignals(False)
        self.tab_bar.setCurrentIndex(0)
        self._load_current_tab_pdf()

    def load_folder_pdfs(self, folder_path: str):
        self.current_folder = folder_path
        self.tab_bar.blockSignals(True)
        self.tab_bar.clear()
        self.pdf_file_map.clear()

        if not os.path.exists(folder_path):
            self.tab_bar.blockSignals(False)
            self.lbl_current_file.setText(f"📄 PDF: Thư mục không tồn tại")
            return

        files = sorted(os.listdir(folder_path))
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]

        if not pdf_files:
            self.tab_bar.blockSignals(False)
            self.lbl_current_file.setText(f"📄 PDF: Không thấy PDF trong {os.path.basename(folder_path)}")
            return

        # Priority order: GCN -> GT -> GTK -> others
        gcn_files = [f for f in pdf_files if 'gcn' in f.lower()]
        gt_files = [f for f in pdf_files if 'gt' in f.lower() and 'gcn' not in f.lower() and 'gtk' not in f.lower()]
        gtk_files = [f for f in pdf_files if 'gtk' in f.lower()]
        other_files = [f for f in pdf_files if f not in gcn_files and f not in gt_files and f not in gtk_files]

        ordered_pdfs = gcn_files + gt_files + gtk_files + other_files

        for idx, f in enumerate(ordered_pdfs):
            full_path = os.path.join(folder_path, f)
            tab_title = f
            if 'gcn' in f.lower():
                tab_title = f"📜 {f}"
            elif 'gtk' in f.lower():
                tab_title = f"📐 {f}"
            elif 'gt' in f.lower():
                tab_title = f"📑 {f}"
            
            self.tab_bar.addTab(QWidget(), tab_title)
            self.tab_bar.tabBar().setTabData(idx, full_path)
            self.pdf_file_map[idx] = full_path

        self.tab_bar.blockSignals(False)

        if self.tab_bar.count() > 0:
            self.tab_bar.setCurrentIndex(0)
            self._load_current_tab_pdf()

    def _on_tab_changed(self, index: int):
        if index >= 0:
            self._load_current_tab_pdf()

    def _load_current_tab_pdf(self):
        idx = self.tab_bar.currentIndex()
        if idx < 0:
            return
        
        pdf_path = self.pdf_file_map.get(idx) or self.tab_bar.tabBar().tabData(idx)
        if pdf_path and self.pdf_engine.load_file(pdf_path):
            self.current_pdf_path = pdf_path
            self.current_page = 0
            self.rotation = 0
            self.lbl_current_file.setText(f"📄 {os.path.basename(pdf_path)}")
            self._render_all_pages()
        else:
            self.lbl_current_file.setText("⚠️ Không nạp được PDF")

    def _render_all_pages(self):
        pixmaps = []
        for i in range(self.pdf_engine.page_count):
            pixmap, _ = self.pdf_engine.render_page_qpixmap(
                i, scale=self.scale_factor, rotation=self.rotation
            )
            if pixmap and not pixmap.isNull():
                pixmaps.append(pixmap)
        
        self.canvas.set_pages(pixmaps)
        self._update_page_label()

    def _update_page_label(self):
        if self.pdf_engine.page_count > 0:
            self.lbl_page.setText(f"Trang {self.current_page + 1}/{self.pdf_engine.page_count} (Cuộn liên tục)")
        else:
            self.lbl_page.setText("0/0")

    def _on_scroll(self):
        if not self.canvas._pixmap_items:
            return
        viewport_center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        for idx, item in enumerate(self.canvas._pixmap_items):
            if item.sceneBoundingRect().contains(viewport_center):
                if self.current_page != idx:
                    self.current_page = idx
                    self._update_page_label()
                break

    def goto_page(self, page_index: int):
        if 0 <= page_index < len(self.canvas._pixmap_items):
            item = self.canvas._pixmap_items[page_index]
            self.canvas.ensureVisible(item, 50, 50)
            self.current_page = page_index
            self._update_page_label()

    def prev_page(self):
        if self.current_page > 0:
            self.goto_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.pdf_engine.page_count - 1:
            self.goto_page(self.current_page + 1)

    def zoom_in(self):
        self.canvas.scale(1.25, 1.25)

    def zoom_out(self):
        self.canvas.scale(0.8, 0.8)

    def rotate_left(self):
        self.rotation = (self.rotation - 90) % 360
        self._render_all_pages()

    def rotate_right(self):
        self.rotation = (self.rotation + 90) % 360
        self._render_all_pages()

    def _handle_crop_ocr(self, crop_bgr: np.ndarray):
        text = self.ocr_engine.ocr_crop(crop_bgr)
        if text:
            clipboard = QGuiApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
                
            QToolTip.showText(QCursor.pos(), f"📋 Đã OCR & Copy: {text}", self, QRect(), 3500)
            self.ocr_text_captured.emit(text)
        else:
            QToolTip.showText(QCursor.pos(), "⚠️ Không nhận diện được chữ", self, QRect(), 2000)

