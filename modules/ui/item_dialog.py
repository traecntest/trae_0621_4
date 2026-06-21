import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QDateEdit, QComboBox,
                             QFormLayout, QFrame, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import CATEGORIES


class ItemDialog(QDialog):
    item_saved = pyqtSignal(dict)

    def __init__(self, parent=None, item_data=None):
        super().__init__(parent)
        self.item_data = item_data
        if item_data and 'id' in item_data and item_data['id'] and item_data['id'] > 0:
            self.is_edit = True
        else:
            self.is_edit = False
        self._setup_ui()
        if self.is_edit:
            self._populate_data()
        elif item_data:
            self._prefill_data()

    def _setup_ui(self):
        self.setWindowTitle("编辑物品" if self.is_edit else "添加物品")
        self.setMinimumWidth(460)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        title_label = QLabel("📝 " + ("编辑物品信息" if self.is_edit else "录入新物品"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #111827;")
        main_layout.addWidget(title_label)

        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 12px;
            }
        """)
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(16)

        label_font = QFont()
        label_font.setPointSize(10)
        label_font.setBold(True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入物品名称，如：牛奶、面包...")
        self.name_edit.setFixedHeight(40)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 2px solid #6366F1;
            }
        """)
        name_label = QLabel("物品名称 *")
        name_label.setFont(label_font)
        name_label.setStyleSheet("color: #374151;")
        form_layout.addRow(name_label, self.name_edit)

        self.expiry_date = QDateEdit()
        self.expiry_date.setCalendarPopup(True)
        self.expiry_date.setDisplayFormat("yyyy-MM-dd")
        self.expiry_date.setMinimumDate(QDate.currentDate())
        self.expiry_date.setDate(QDate.currentDate().addDays(7))
        self.expiry_date.setFixedHeight(40)
        self.expiry_date.setStyleSheet("""
            QDateEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11pt;
            }
            QDateEdit:focus {
                border: 2px solid #6366F1;
            }
        """)
        expiry_label = QLabel("到期日期 *")
        expiry_label.setFont(label_font)
        expiry_label.setStyleSheet("color: #374151;")
        form_layout.addRow(expiry_label, self.expiry_date)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("如：冰箱、厨房橱柜、卧室抽屉...")
        self.location_edit.setFixedHeight(40)
        self.location_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 2px solid #6366F1;
            }
        """)
        location_label = QLabel("存放位置")
        location_label.setFont(label_font)
        location_label.setStyleSheet("color: #374151;")
        form_layout.addRow(location_label, self.location_edit)

        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(40)
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11pt;
            }
            QComboBox:focus {
                border: 2px solid #6366F1;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: #EEF2FF;
                selection-color: #4338CA;
            }
        """)
        for category, info in CATEGORIES.items():
            if category != '全部':
                self.category_combo.addItem(f"{info['icon']}  {category}", category)
        category_label = QLabel("分类")
        category_label.setFont(label_font)
        category_label.setStyleSheet("color: #374151;")
        form_layout.addRow(category_label, self.category_combo)

        main_layout.addWidget(form_container)

        if not self.is_edit:
            tip_label = QLabel("💡 小提示：OCR识别后可在此处修改信息，确保准确无误")
            tip_font = QFont()
            tip_font.setPointSize(9)
            tip_label.setFont(tip_font)
            tip_label.setStyleSheet("color: #6B7280; padding: 0 4px;")
            main_layout.addWidget(tip_label)

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
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_font = QFont()
        save_font.setPointSize(11)
        save_font.setBold(True)
        save_btn.setFont(save_font)
        save_btn.setFixedHeight(44)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 32px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

    def _populate_data(self):
        self.name_edit.setText(self.item_data['name'])
        self.location_edit.setText(self.item_data.get('location', ''))
        try:
            date_parts = self.item_data['expiry_date'].split('-')
            if len(date_parts) == 3:
                d = QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                self.expiry_date.setDate(d)
                if d < QDate.currentDate():
                    self.expiry_date.setMinimumDate(d)
        except (ValueError, IndexError):
            pass
        category = self.item_data.get('category', '其他')
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == category:
                self.category_combo.setCurrentIndex(i)
                break

    def _prefill_data(self):
        if 'name' in self.item_data and self.item_data['name']:
            self.name_edit.setText(self.item_data['name'])
        if 'location' in self.item_data and self.item_data['location']:
            self.location_edit.setText(self.item_data['location'])
        if 'expiry_date' in self.item_data and self.item_data['expiry_date']:
            try:
                date_parts = self.item_data['expiry_date'].split('-')
                if len(date_parts) == 3:
                    d = QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                    if d >= QDate.currentDate():
                        self.expiry_date.setDate(d)
            except (ValueError, IndexError):
                pass
        if 'category' in self.item_data and self.item_data['category']:
            category = self.item_data['category']
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == category:
                    self.category_combo.setCurrentIndex(i)
                    break

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入物品名称")
            self.name_edit.setFocus()
            return
        expiry = self.expiry_date.date().toString("yyyy-MM-dd")
        location = self.location_edit.text().strip()
        category = self.category_combo.currentData()

        result = {
            'name': name,
            'expiry_date': expiry,
            'location': location,
            'category': category
        }
        if self.is_edit:
            result['id'] = self.item_data['id']
        self.item_saved.emit(result)
        self.accept()
