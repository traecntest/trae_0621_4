import os
import sys
import numpy as np
from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QDesktopWidget)
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QBrush, QFont, QScreen
from PIL import Image

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class ScreenshotSelector(QWidget):
    screenshot_taken = pyqtSignal(np.ndarray)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.screen_pixmap = None
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self._capture_fullscreen()
        self._setup_ui()
        self.showFullScreen()

    def _capture_fullscreen(self):
        screen = QApplication.primaryScreen()
        if screen:
            self.screen_pixmap = screen.grabWindow(0)
        else:
            desktop = QApplication.desktop()
            self.screen_pixmap = QPixmap.grabWindow(desktop.winId())

    def _setup_ui(self):
        self.setCursor(Qt.CrossCursor)
        hint = QLabel(self)
        hint.setText("🖱️  拖动鼠标选择截图区域 | 按 ESC 取消 | 按 ENTER 全屏截图")
        hint_font = QFont()
        hint_font.setPointSize(11)
        hint.setFont(hint_font)
        hint.setStyleSheet("""
            QLabel {
                background-color: rgba(99, 102, 241, 0.95);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
            }
        """)
        hint.adjustSize()
        screen_geom = QApplication.desktop().screenGeometry()
        hint.move(screen_geom.center().x() - hint.width() // 2, 40)
        hint.show()
        self.hint_label = hint

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.screen_pixmap:
            painter.drawPixmap(0, 0, self.screen_pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if self.start_pos and self.end_pos:
            select_rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.drawPixmap(select_rect.topLeft(), self.screen_pixmap.copy(select_rect))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(99, 102, 241), 3, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(select_rect)
            pen2 = QPen(QColor(255, 255, 255), 1, Qt.DashLine)
            painter.setPen(pen2)
            painter.drawRect(select_rect)
            size_text = f"{select_rect.width()} x {select_rect.height()}"
            info_rect = QRect(select_rect.left(), select_rect.top() - 32, 120, 28)
            painter.fillRect(info_rect, QColor(99, 102, 241, 230))
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.drawText(info_rect, Qt.AlignCenter, size_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.hint_label.hide()
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.end_pos = event.pos()
            self.is_selecting = False
            self.update()
            QApplication.processEvents()
            self._take_selected_screenshot()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.start_pos = self.rect().topLeft()
            self.end_pos = self.rect().bottomRight()
            self._take_selected_screenshot()

    def _take_selected_screenshot(self):
        if not self.start_pos or not self.end_pos:
            self.cancelled.emit()
            self.close()
            return
        select_rect = QRect(self.start_pos, self.end_pos).normalized()
        if select_rect.width() < 10 or select_rect.height() < 10:
            self.cancelled.emit()
            self.close()
            return
        cropped = self.screen_pixmap.copy(select_rect)
        image = cropped.toImage()
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)
        arr = arr[:, :, [2, 1, 0, 3]].copy()
        self.screenshot_taken.emit(arr)
        self.close()
