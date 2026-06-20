import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QFrame, QSizePolicy, QPushButton,
                             QToolButton, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import APP_DISPLAY_NAME


class NotificationCard(QFrame):
    dismissed = pyqtSignal(object)

    def __init__(self, reminder_data, parent=None):
        super().__init__(parent)
        self.reminder_data = reminder_data
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self):
        self.setFixedSize(360, 160)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_container = QFrame(self)
        main_container.setGeometry(8, 8, 344, 144)
        main_container.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(main_container)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 4)
        main_container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon = self.reminder_data.get('icon', '📦')
        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_label.setFont(icon_font)
        header.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        name = self.reminder_data.get('item', {}).get('name', '物品')
        name_label = QLabel(name)
        name_font = QFont()
        name_font.setPointSize(13)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #111827;")
        name_label.setWordWrap(True)
        title_layout.addWidget(name_label)

        days_text = self.reminder_data.get('formatted_days', '')
        days_label = QLabel(days_text)
        days_font = QFont()
        days_font.setPointSize(10)
        days_font.setBold(True)
        days_label.setFont(days_font)
        status = self.reminder_data.get('status', 'warning')
        if status == 'expired' or status == 'critical':
            days_label.setStyleSheet("color: #DC2626;")
        elif status == 'warning':
            days_label.setStyleSheet("color: #F59E0B;")
        else:
            days_label.setStyleSheet("color: #3B82F6;")
        title_layout.addWidget(days_label)

        header.addLayout(title_layout, 1)

        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: transparent;
                border-radius: 14px;
                font-size: 20px;
                color: #9CA3AF;
            }
            QToolButton:hover {
                background-color: #F3F4F6;
                color: #374151;
            }
        """)
        close_btn.clicked.connect(self._dismiss)
        header.addWidget(close_btn)

        layout.addLayout(header)

        suggestion = self.reminder_data.get('suggestion', '')
        suggestion_label = QLabel(suggestion)
        sug_font = QFont()
        sug_font.setPointSize(10)
        suggestion_label.setFont(sug_font)
        suggestion_label.setStyleSheet("color: #4B5563;")
        suggestion_label.setWordWrap(True)
        layout.addWidget(suggestion_label, 1)

        expiry_date = self.reminder_data.get('item', {}).get('expiry_date', '')
        if expiry_date:
            date_label = QLabel(f"📅 到期日期: {expiry_date}")
            date_font = QFont()
            date_font.setPointSize(9)
            date_label.setFont(date_font)
            date_label.setStyleSheet("color: #9CA3AF;")
            layout.addWidget(date_label)

    def _setup_animation(self):
        self._opacity = QPropertyAnimation(self, b"windowOpacity")
        self._pos_anim = QPropertyAnimation(self, b"geometry")

    def show_with_animation(self, x, y):
        self.setWindowOpacity(0)
        start_geom = self.geometry()
        start_geom.moveTopLeft(x, y + 30)
        self.setGeometry(start_geom)
        self.show()

        self._opacity.setDuration(300)
        self._opacity.setStartValue(0)
        self._opacity.setEndValue(1)
        self._opacity.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity.start()

        end_geom = self.geometry()
        end_geom.moveTopLeft(x, y)
        self._pos_anim.setDuration(300)
        self._pos_anim.setStartValue(start_geom)
        self._pos_anim.setEndValue(end_geom)
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim.start()

        QTimer.singleShot(10000, self._auto_dismiss)

    def _dismiss(self):
        self._opacity.setDuration(200)
        self._opacity.setStartValue(1)
        self._opacity.setEndValue(0)
        self._opacity.setEasingCurve(QEasingCurve.InCubic)
        self._opacity.finished.connect(self.close)
        self._opacity.start()
        self.dismissed.emit(self)

    def _auto_dismiss(self):
        if self.isVisible():
            self._dismiss()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dismiss()


class NotificationManager:
    def __init__(self, screen_geometry):
        self.screen_geometry = screen_geometry
        self.notifications = []
        self.max_notifications = 4
        self.card_height = 176
        self.spacing = 12
        self.base_y = self.screen_geometry.bottom() - 80

    def _get_position(self):
        x = self.screen_geometry.right() - 380
        count = len(self.notifications)
        y = self.base_y - (count * (self.card_height + self.spacing))
        return x, y

    def show_notification(self, reminder_data):
        if len(self.notifications) >= self.max_notifications:
            self.notifications[0]._dismiss()
        card = NotificationCard(reminder_data)
        card.dismissed.connect(self._on_dismissed)
        self.notifications.append(card)
        self._rearrange()
        x, y = self._get_position()
        card.show_with_animation(x, y)

    def show_notifications(self, reminders):
        for reminder in reminders:
            self.show_notification(reminder)

    def _on_dismissed(self, card):
        if card in self.notifications:
            self.notifications.remove(card)
            self._rearrange()

    def _rearrange(self):
        pass

    def close_all(self):
        for card in list(self.notifications):
            card.close()
        self.notifications.clear()
