import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSizePolicy, QMenu, QAction, QToolButton)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor, QIcon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.reminder import calculate_days_remaining, format_days_remaining, get_category_icon


class ItemCard(QFrame):
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    card_clicked = pyqtSignal(int)

    STATUS_STYLES = {
        'expired': ('#DC2626', '#FEE2E2'),
        'critical': ('#EF4444', '#FEE2E2'),
        'warning': ('#F59E0B', '#FEF3C7'),
        'notice': ('#3B82F6', '#DBEAFE'),
        'normal': ('#6B7280', '#F3F4F6'),
        'safe': ('#10B981', '#D1FAE5')
    }

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.item_id = item_data['id']
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        icon_label = QLabel(get_category_icon(self.item_data.get('category', '其他')))
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_label.setFont(icon_font)
        icon_label.setFixedWidth(60)
        icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        name_label = QLabel(self.item_data['name'])
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #1F2937;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        details_layout = QHBoxLayout()
        details_layout.setSpacing(12)

        expiry_label = QLabel(f"📅 {self.item_data['expiry_date']}")
        expiry_font = QFont()
        expiry_font.setPointSize(10)
        expiry_label.setFont(expiry_font)
        expiry_label.setStyleSheet("color: #6B7280;")
        details_layout.addWidget(expiry_label)

        if self.item_data.get('location'):
            location_label = QLabel(f"📍 {self.item_data['location']}")
            location_font = QFont()
            location_font.setPointSize(10)
            location_label.setFont(location_font)
            location_label.setStyleSheet("color: #6B7280;")
            details_layout.addWidget(location_label)

        details_layout.addStretch()
        info_layout.addLayout(details_layout)

        category_label = QLabel(f"分类: {self.item_data.get('category', '其他')}")
        cat_font = QFont()
        cat_font.setPointSize(9)
        category_label.setFont(cat_font)
        category_label.setStyleSheet("color: #9CA3AF;")
        info_layout.addWidget(category_label)

        main_layout.addLayout(info_layout, 1)

        days_remaining = calculate_days_remaining(self.item_data['expiry_date'])
        formatted_days, status = format_days_remaining(days_remaining)

        self.days_badge = QLabel(formatted_days)
        badge_font = QFont()
        badge_font.setPointSize(12)
        badge_font.setBold(True)
        self.days_badge.setFont(badge_font)
        self.days_badge.setAlignment(Qt.AlignCenter)
        self.days_badge.setFixedSize(110, 48)

        text_color, bg_color = self.STATUS_STYLES.get(status, self.STATUS_STYLES['normal'])
        self.days_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 24px;
                padding: 8px 16px;
            }}
        """)
        main_layout.addWidget(self.days_badge)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(4)

        edit_btn = QToolButton()
        edit_btn.setText("✏️")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: transparent;
                border-radius: 16px;
                font-size: 16px;
            }
            QToolButton:hover {
                background-color: #E5E7EB;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.item_id))
        actions_layout.addWidget(edit_btn)

        delete_btn = QToolButton()
        delete_btn.setText("🗑️")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: transparent;
                border-radius: 16px;
                font-size: 16px;
            }
            QToolButton:hover {
                background-color: #FEE2E2;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.item_id))
        actions_layout.addWidget(delete_btn)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

    def _apply_style(self):
        self.setStyleSheet("""
            ItemCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
            ItemCard:hover {
                border: 1px solid #D1D5DB;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.item_id)
        super().mousePressEvent(event)

    def update_data(self, item_data):
        self.item_data = item_data
        self._setup_ui()
