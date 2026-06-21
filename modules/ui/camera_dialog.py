import os
import sys
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class CameraDialog(QDialog):
    capture_taken = pyqtSignal(np.ndarray)

    def __init__(self, parent=None, camera_index: int = 0):
        super().__init__(parent)
        self.camera_index = camera_index
        self.capture = None
        self.timer = None
        self.current_frame = None
        self._setup_ui()
        self._init_camera()

    def _setup_ui(self):
        self.setWindowTitle("📷 摄像头拍摄")
        self.setFixedSize(720, 620)
        self.setStyleSheet("""
            QDialog {
                background-color: #F9FAFB;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        title_label = QLabel("📷 对准物品的生产日期/保质期")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #111827;")
        main_layout.addWidget(title_label)

        self.video_frame = QFrame()
        self.video_frame.setFixedSize(680, 480)
        self.video_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px solid #6366F1;
                border-radius: 12px;
            }
        """)

        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("color: #FFFFFF; font-size: 12pt;")
        self.video_label.setText("🎥 正在启动摄像头...")
        video_layout.addWidget(self.video_label)

        main_layout.addWidget(self.video_frame, alignment=Qt.AlignCenter)

        hint_label = QLabel("💡 提示：确保文字清晰对焦，光线充足")
        hint_font = QFont()
        hint_font.setPointSize(9)
        hint_label.setFont(hint_font)
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #6B7280;")
        main_layout.addWidget(hint_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_font = QFont()
        cancel_font.setPointSize(11)
        cancel_btn.setFont(cancel_font)
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 12px;
                padding: 0 28px;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        self.capture_btn = QPushButton("  📸  拍照识别  ")
        capture_font = QFont()
        capture_font.setPointSize(12)
        capture_font.setBold(True)
        self.capture_btn.setFont(capture_font)
        self.capture_btn.setFixedHeight(48)
        self.capture_btn.setCursor(Qt.PointingHandCursor)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 36px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
        """)
        self.capture_btn.clicked.connect(self._capture_frame)
        self.capture_btn.setEnabled(False)
        btn_layout.addWidget(self.capture_btn)

        main_layout.addLayout(btn_layout)

    def _init_camera(self):
        if not CV2_AVAILABLE:
            QMessageBox.critical(
                self, "错误",
                "OpenCV 未安装，无法使用摄像头功能。\n\n"
                "请运行: pip install opencv-python"
            )
            QTimer.singleShot(100, self.reject)
            return

        try:
            self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.capture.isOpened():
                self.capture = cv2.VideoCapture(self.camera_index)

            if not self.capture.isOpened():
                raise Exception("无法打开摄像头设备")

            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._update_frame)
            self.timer.start(30)

            self.capture_btn.setEnabled(True)
            self.video_label.setText("")

        except Exception as e:
            self.video_label.setText(
                f"❌ 无法打开摄像头\n\n"
                f"可能原因：\n"
                f"1. 摄像头被其他程序占用\n"
                f"2. 没有摄像头设备\n"
                f"3. 摄像头驱动异常\n\n"
                f"错误信息: {str(e)}\n\n"
                f"💡 可以使用「截图识别」或「导入图片」功能替代"
            )
            self.capture_btn.setEnabled(False)

    def _update_frame(self):
        if self.capture is None:
            return

        ret, frame = self.capture.read()
        if not ret:
            return

        self.current_frame = frame.copy()

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def _capture_frame(self):
        if self.current_frame is None:
            QMessageBox.warning(self, "提示", "未获取到画面，请稍候...")
            return

        self.timer.stop()

        height, width = self.current_frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        crop_width = min(width, 900)
        crop_height = min(height, 500)

        x1 = max(0, center_x - crop_width // 2)
        y1 = max(0, center_y - crop_height // 2)
        x2 = min(width, center_x + crop_width // 2)
        y2 = min(height, center_y + crop_height // 2)

        cropped = self.current_frame[y1:y2, x1:x2]

        self.capture_taken.emit(cropped)
        self.accept()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()

    def _cleanup(self):
        if self.timer:
            self.timer.stop()
            self.timer = None
        if self.capture:
            self.capture.release()
            self.capture = None
