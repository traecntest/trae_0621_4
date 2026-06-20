import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QFrame, QPushButton, QSizePolicy,
                             QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import CATEGORIES
from modules.reminder import calculate_days_remaining
from modules.database import Database


class Sidebar(QFrame):
    category_changed = pyqtSignal(str)
    add_item_requested = pyqtSignal()
    take_photo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self._current_category = '全部'
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(240)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            Sidebar {
                background-color: #F9FAFB;
                border-right: 1px solid #E5E7EB;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 24, 20, 16)
        header_layout.setSpacing(8)

        title_label = QLabel("📦 过期物品管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #111827;")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("守护每一份新鲜")
        sub_font = QFont()
        sub_font.setPointSize(10)
        subtitle_label.setFont(sub_font)
        subtitle_label.setStyleSheet("color: #9CA3AF;")
        header_layout.addWidget(subtitle_label)

        main_layout.addLayout(header_layout)

        btn_container = QVBoxLayout()
        btn_container.setContentsMargins(16, 0, 16, 16)
        btn_container.setSpacing(8)

        self.add_btn = QPushButton("  📷  拍照录入")
        add_font = QFont()
        add_font.setPointSize(11)
        add_font.setBold(True)
        self.add_btn.setFont(add_font)
        self.add_btn.setFixedHeight(48)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        self.add_btn.clicked.connect(self.take_photo_requested.emit)
        btn_container.addWidget(self.add_btn)

        self.manual_btn = QPushButton("  ✏️  手动添加")
        manual_font = QFont()
        manual_font.setPointSize(10)
        self.manual_btn.setFont(manual_font)
        self.manual_btn.setFixedHeight(40)
        self.manual_btn.setCursor(Qt.PointingHandCursor)
        self.manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
                border-color: #9CA3AF;
            }
        """)
        self.manual_btn.clicked.connect(self.add_item_requested.emit)
        btn_container.addWidget(self.manual_btn)

        main_layout.addLayout(btn_container)

        stats_container = QFrame()
        stats_container.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E5E7EB;
                border-bottom: 1px solid #E5E7EB;
            }
        """)
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(12)

        self._update_stats(stats_layout)

        main_layout.addWidget(stats_container)

        cat_label = QLabel("分类导航")
        cat_font = QFont()
        cat_font.setPointSize(10)
        cat_font.setBold(True)
        cat_label.setFont(cat_font)
        cat_label.setStyleSheet("color: #6B7280; padding: 16px 20px 8px;")
        main_layout.addWidget(cat_label)

        self.category_list = QListWidget()
        self.category_list.setFrameShape(QListWidget.NoFrame)
        self.category_list.setFocusPolicy(Qt.NoFocus)
        self.category_list.setSpacing(2)
        self.category_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                padding: 0 12px;
            }
            QListWidget::item {
                border-radius: 8px;
                padding: 10px 8px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #E5E7EB;
            }
            QListWidget::item:selected {
                background-color: #EEF2FF;
                color: #4338CA;
            }
        """)

        self._populate_categories()
        self.category_list.currentRowChanged.connect(self._on_category_selected)

        main_layout.addWidget(self.category_list, 1)

        footer_label = QLabel("")
        footer_label.setFixedHeight(20)
        main_layout.addWidget(footer_label)

    def _populate_categories(self):
        self.category_list.clear()
        for category, info in CATEGORIES.items():
            count = self._get_category_count(category)
            display_text = f"{info['icon']}  {category}"
            if count > 0:
                display_text += f"  ({count})"
            item = QListWidgetItem(display_text)
            item_font = QFont()
            item_font.setPointSize(11)
            item.setFont(item_font)
            item.setData(Qt.UserRole, category)
            self.category_list.addItem(item)
            if category == self._current_category:
                self.category_list.setCurrentRow(self.category_list.count() - 1)

    def _get_category_count(self, category: str) -> int:
        if category == '全部':
            stats = self.db.get_stats()
            return stats['total']
        items = self.db.get_all_items(category=category)
        return len(items)

    def _update_stats(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = self.db.get_stats()

        total_layout = QHBoxLayout()
        total_layout.setSpacing(8)
        total_icon = QLabel("📦")
        total_icon_font = QFont()
        total_icon_font.setPointSize(14)
        total_icon.setFont(total_icon_font)
        total_layout.addWidget(total_icon)
        total_text = QLabel("物品总数")
        total_text.setStyleSheet("color: #6B7280; font-size: 10pt;")
        total_layout.addWidget(total_text, 1)
        total_num = QLabel(str(stats['total']))
        total_num.setStyleSheet("color: #111827; font-size: 11pt; font-weight: bold;")
        total_layout.addWidget(total_num)
        layout.addLayout(total_layout)

        row1 = QHBoxLayout()
        row1.setSpacing(12)

        exp_layout = QHBoxLayout()
        exp_layout.setSpacing(6)
        exp_icon = QLabel("⚠️")
        exp_icon_font = QFont()
        exp_icon_font.setPointSize(13)
        exp_icon.setFont(exp_icon_font)
        exp_layout.addWidget(exp_icon)
        exp_text = QLabel("已过期")
        exp_text.setStyleSheet("color: #DC2626; font-size: 9pt;")
        exp_layout.addWidget(exp_text, 1)
        exp_num = QLabel(str(stats['expired']))
        exp_num.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        exp_layout.addWidget(exp_num)
        row1.addLayout(exp_layout, 1)

        soon_layout = QHBoxLayout()
        soon_layout.setSpacing(6)
        soon_icon = QLabel("⏰")
        soon_icon_font = QFont()
        soon_icon_font.setPointSize(13)
        soon_icon.setFont(soon_icon_font)
        soon_layout.addWidget(soon_icon)
        soon_text = QLabel("3天内到期")
        soon_text.setStyleSheet("color: #F59E0B; font-size: 9pt;")
        soon_layout.addWidget(soon_text, 1)
        soon_num = QLabel(str(stats['expiring_3d']))
        soon_num.setStyleSheet("color: #F59E0B; font-size: 10pt; font-weight: bold;")
        soon_layout.addWidget(soon_num)
        row1.addLayout(soon_layout, 1)

        layout.addLayout(row1)

    def refresh(self):
        self._populate_categories()
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            if item.data(Qt.UserRole) == self._current_category:
                self.category_list.setCurrentRow(i)
                break

        stats_container = self.findChild(QFrame)
        if stats_container:
            stats_layout = stats_container.layout()
            if stats_layout:
                self._update_stats(stats_layout)

    def _on_category_selected(self, row):
        item = self.category_list.item(row)
        if item:
            category = item.data(Qt.UserRole)
            if category != self._current_category:
                self._current_category = category
                self.category_changed.emit(category)

    def get_current_category(self):
        return self._current_category
