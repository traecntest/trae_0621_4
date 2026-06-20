import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QProgressBar, QFrame, QPushButton, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.ocr_engine import OCREngine


class OCRWorker(QThread):
    progress = pyqtSignal(str, int)
    finished_ok = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_input):
        super().__init__()
        self.image_input = image_input
        self.ocr = OCREngine()

    def run(self):
        try:
            self.progress.emit("正在加载OCR模型...", 10)
            self.ocr._get_reader()
            self.progress.emit("正在预处理图片...", 30)
            self.progress.emit("正在识别文字内容...", 60)
            result = self.ocr.parse_product_info(self.image_input)
            self.progress.emit("正在解析日期信息...", 85)
            self.progress.emit("识别完成！", 100)
            self.finished_ok.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OCRProgressDialog(QDialog):
    def __init__(self, parent=None, image_path=None, image_array=None):
        super().__init__(parent)
        self.image_path = image_path
        self.image_array = image_array
        self.result = None
        self._setup_ui()
        self._start_ocr()

    def _setup_ui(self):
        self.setWindowTitle("OCR识别中")
        self.setFixedSize(500, 420)
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title_label = QLabel("🔍 正在识别物品信息")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #111827;")
        main_layout.addWidget(title_label)

        preview_frame = QFrame()
        preview_frame.setFixedHeight(180)
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 2px dashed #D1D5DB;
                border-radius: 12px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #9CA3AF; font-size: 10pt;")
        self._load_preview()
        preview_layout.addWidget(self.preview_label)

        main_layout.addWidget(preview_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E5E7EB;
                border: none;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
                border-radius: 6px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("准备开始...")
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #6B7280;")
        main_layout.addWidget(self.status_label)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                padding: 0 24px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def _load_preview(self):
        pixmap = None
        try:
            if self.image_path and os.path.exists(self.image_path):
                pixmap = QPixmap(self.image_path)
            elif self.image_array is not None:
                from PIL import Image
                import io
                img = Image.fromarray(self.image_array)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
            if pixmap and not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.preview_label.width(), self.preview_label.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText("📷 图片预览")
        except Exception:
            self.preview_label.setText("📷 图片预览")

    def _start_ocr(self):
        image_input = self.image_path if self.image_path else self.image_array
        if image_input is None:
            self.reject()
            return
        self.worker = OCRWorker(image_input)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message, value):
        self.status_label.setText(message)
        self.progress_bar.setValue(value)

    def _on_finished(self, result):
        self.result = result
        self.accept()

    def _on_error(self, error_msg):
        self.status_label.setText(f"❌ 识别失败: {error_msg}")
        self.status_label.setStyleSheet("color: #DC2626;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E5E7EB;
                border: none;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #DC2626;
                border-radius: 6px;
            }
        """)
        self.cancel_btn.setText("关闭")
