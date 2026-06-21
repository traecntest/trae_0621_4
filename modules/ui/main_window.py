import os
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QScrollArea, QFrame, QLineEdit, QPushButton,
                             QMessageBox, QFileDialog, QShortcut, QDesktopWidget,
                             QMenu, QAction, QSystemTrayIcon, QApplication, QToolButton,
                             QDialog)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QPalette, QColor, QPixmap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import APP_DISPLAY_NAME, APP_NAME, DB_PATH, APP_DATA_DIR, SCREENSHOT_SHORTCUT, CATEGORIES
from modules.database import Database
from modules.reminder import ReminderEngine, calculate_days_remaining, format_days_remaining, get_category_icon
from modules.ocr_engine import OCREngine
from modules.ui.sidebar import Sidebar
from modules.ui.item_card import ItemCard
from modules.ui.item_dialog import ItemDialog
from modules.ui.ocr_dialog import OCRProgressDialog
from modules.ui.notification import NotificationManager
from modules.ui.screenshot import ScreenshotSelector
from modules.ui.camera_dialog import CameraDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.reminder_engine = ReminderEngine(self)
        self.current_category = '全部'
        self.items = []
        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_signals()
        self._init_notification_manager()
        self.refresh_items()
        self.reminder_engine.start()

    def _setup_window(self):
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setMinimumSize(1080, 720)
        self.resize(1200, 780)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F3F4F6;
            }
        """)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(72)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E5E7EB;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(32, 16, 32, 16)
        top_layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.page_title = QLabel("全部物品")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.page_title.setFont(title_font)
        self.page_title.setStyleSheet("color: #111827;")
        title_layout.addWidget(self.page_title)

        self.subtitle_label = QLabel("共 0 件物品")
        sub_font = QFont()
        sub_font.setPointSize(10)
        self.subtitle_label.setFont(sub_font)
        self.subtitle_label.setStyleSheet("color: #9CA3AF;")
        title_layout.addWidget(self.subtitle_label)
        top_layout.addLayout(title_layout)

        top_layout.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  搜索物品名称或位置...")
        self.search_edit.setFixedSize(320, 42)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 21px;
                padding: 0 20px;
                font-size: 10pt;
                color: #374151;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 2px solid #6366F1;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_edit)

        refresh_btn = QToolButton()
        refresh_btn.setText("🔄")
        refresh_btn.setFixedSize(42, 42)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.setStyleSheet("""
            QToolButton {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 21px;
                font-size: 18px;
            }
            QToolButton:hover {
                background-color: #F3F4F6;
                border-color: #D1D5DB;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_items)
        top_layout.addWidget(refresh_btn)

        content_layout.addWidget(top_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #D1D5DB;
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9CA3AF;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)

        self.items_layout = QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(32, 24, 32, 32)
        self.items_layout.setSpacing(12)
        self.items_layout.addStretch()

        content_layout.addWidget(self.scroll_area, 1)

        self.drop_hint = QLabel(content_widget)
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setText("📷  松开鼠标，识别图片中的物品信息")
        drop_font = QFont()
        drop_font.setPointSize(14)
        drop_font.setBold(True)
        self.drop_hint.setFont(drop_font)
        self.drop_hint.setStyleSheet("""
            QLabel {
                background-color: rgba(99, 102, 241, 0.12);
                color: #4338CA;
                border: 3px dashed #6366F1;
                border-radius: 16px;
                margin: 40px;
            }
        """)
        self.drop_hint.hide()

        main_layout.addWidget(content_widget, 1)

    def _setup_shortcuts(self):
        self.screenshot_shortcut = QShortcut(QKeySequence(SCREENSHOT_SHORTCUT), self)
        self.screenshot_shortcut.activated.connect(self._take_screenshot)

        self.add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.add_shortcut.activated.connect(self._add_manual_item)

        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(lambda: self.search_edit.setFocus())

    def _setup_signals(self):
        self.sidebar.category_changed.connect(self._on_category_changed)
        self.sidebar.add_item_requested.connect(self._add_manual_item)
        self.sidebar.take_photo_requested.connect(self._show_photo_menu)
        self.reminder_engine.reminder_triggered.connect(self._on_reminder)
        self.reminder_engine.check_completed.connect(self._on_reminder_check_complete)

    def _init_notification_manager(self):
        screen_geom = QDesktopWidget().screenGeometry()
        self.notification_manager = NotificationManager(screen_geom)

    def refresh_items(self, keyword: str = ''):
        for i in reversed(range(self.items_layout.count() - 1)):
            item = self.items_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if keyword:
            self.items = self.db.search_items(keyword)
        else:
            self.items = self.db.get_all_items(category=self.current_category)

        self._update_subtitle()

        if not self.items:
            self._show_empty_state()
            return

        expired_items = []
        warning_items = []
        normal_items = []

        for item in self.items:
            days = calculate_days_remaining(item['expiry_date'])
            if days < 0:
                expired_items.append((item, days))
            elif days <= 3:
                warning_items.append((item, days))
            else:
                normal_items.append((item, days))

        all_sorted = sorted(expired_items, key=lambda x: x[1])
        all_sorted.extend(sorted(warning_items, key=lambda x: x[1]))
        all_sorted.extend(sorted(normal_items, key=lambda x: x[1]))

        for item_data, _ in all_sorted:
            card = ItemCard(item_data)
            card.edit_clicked.connect(self._on_edit_item)
            card.delete_clicked.connect(self._on_delete_item)
            card.card_clicked.connect(self._on_card_clicked)
            self.items_layout.insertWidget(self.items_layout.count() - 1, card)

    def _show_empty_state(self):
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(20)

        icon_label = QLabel(CATEGORIES.get(self.current_category, {}).get('icon', '📦'))
        icon_font = QFont()
        icon_font.setPointSize(72)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)

        title_label = QLabel("还没有物品记录")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #374151;")
        empty_layout.addWidget(title_label)

        desc_label = QLabel("点击左上角「拍照录入」按钮，或直接拖拽图片到窗口\n快速添加你的第一件物品吧！")
        desc_font = QFont()
        desc_font.setPointSize(11)
        desc_label.setFont(desc_font)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #9CA3AF; line-height: 1.8;")
        empty_layout.addWidget(desc_label)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(12)

        photo_btn = QPushButton("  📷  开始识别  ")
        photo_font = QFont()
        photo_font.setPointSize(11)
        photo_font.setBold(True)
        photo_btn.setFont(photo_font)
        photo_btn.setFixedHeight(48)
        photo_btn.setCursor(Qt.PointingHandCursor)
        photo_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 28px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        photo_btn.clicked.connect(self._show_photo_menu)
        btn_layout.addWidget(photo_btn)

        add_btn = QPushButton("  ✏️  手动添加  ")
        add_font = QFont()
        add_font.setPointSize(11)
        add_btn.setFont(add_font)
        add_btn.setFixedHeight(48)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
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
        add_btn.clicked.connect(self._add_manual_item)
        btn_layout.addWidget(add_btn)

        empty_layout.addLayout(btn_layout)
        empty_layout.addStretch()

        self.items_layout.insertWidget(self.items_layout.count() - 1, empty_widget)

    def _update_subtitle(self):
        count = len(self.items)
        if self.current_category == '全部':
            self.subtitle_label.setText(f"共 {count} 件物品")
        else:
            self.subtitle_label.setText(f"{self.current_category}分类 · 共 {count} 件")
        self.page_title.setText(self.current_category + ("物品" if self.current_category != '全部' else ""))

    def _on_category_changed(self, category):
        self.current_category = category
        self.search_edit.clear()
        self.refresh_items()

    def _on_search(self, keyword):
        self.refresh_items(keyword.strip())

    def _on_edit_item(self, item_id):
        item_data = self.db.get_item(item_id)
        if item_data:
            dialog = ItemDialog(self, item_data)
            dialog.item_saved.connect(self._on_item_saved)
            dialog.exec_()

    def _on_delete_item(self, item_id):
        item_data = self.db.get_item(item_id)
        if item_data:
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除「{item_data['name']}」吗？\n此操作不可恢复。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.db.delete_item(item_id)
                self.refresh_items()
                self.sidebar.refresh()

    def _on_card_clicked(self, item_id):
        item_data = self.db.get_item(item_id)
        if item_data:
            suggestion = self.reminder_engine.get_item_suggestion(item_data)
            days = calculate_days_remaining(item_data['expiry_date'])
            formatted, _ = format_days_remaining(days)
            category_icon = get_category_icon(item_data.get('category', '其他'))

            info_text = (
                f"{category_icon}  {item_data['name']}\n"
                f"📅 到期日期: {item_data['expiry_date']}  ({formatted})\n"
                f"📍 存放位置: {item_data.get('location', '未记录')}\n"
                f"📂 分类: {item_data.get('category', '其他')}\n\n"
                f"💡 建议: {suggestion}"
            )
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("物品详情")
            msg_box.setText(info_text)
            msg_box.setIcon(QMessageBox.Information)
            edit_btn = msg_box.addButton("编辑", QMessageBox.AcceptRole)
            delete_btn = msg_box.addButton("删除", QMessageBox.DestructiveRole)
            close_btn = msg_box.addButton("关闭", QMessageBox.RejectRole)
            msg_box.exec_()
            if msg_box.clickedButton() == edit_btn:
                self._on_edit_item(item_id)
            elif msg_box.clickedButton() == delete_btn:
                self._on_delete_item(item_id)

    def _on_item_saved(self, item_data):
        item_id = item_data.get('id')
        if item_id and item_id > 0:
            self.db.update_item(
                item_id=item_id,
                name=item_data['name'],
                expiry_date=item_data['expiry_date'],
                location=item_data['location'],
                category=item_data['category']
            )
        else:
            new_id = self.db.add_item(
                name=item_data['name'],
                expiry_date=item_data['expiry_date'],
                location=item_data['location'],
                category=item_data['category']
            )
            item_data['id'] = new_id
        self.refresh_items()
        self.sidebar.refresh()

    def _add_manual_item(self):
        dialog = ItemDialog(self)
        dialog.item_saved.connect(self._on_item_saved)
        dialog.exec_()

    def _show_photo_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 8px;
            }
            QMenu::item {
                padding: 12px 24px 12px 16px;
                border-radius: 8px;
                font-size: 11pt;
                color: #374151;
            }
            QMenu::item:hover {
                background-color: #EEF2FF;
                color: #4338CA;
            }
        """)

        screenshot_action = QAction("🖼️  截图识别  (" + SCREENSHOT_SHORTCUT + ")", self)
        screenshot_action.triggered.connect(self._take_screenshot)
        menu.addAction(screenshot_action)

        import_action = QAction("📂  导入图片", self)
        import_action.triggered.connect(self._import_image)
        menu.addAction(import_action)

        menu.addSeparator()

        camera_action = QAction("📷  调用摄像头", self)
        camera_action.triggered.connect(self._open_camera)
        menu.addAction(camera_action)

        pos = self.mapToGlobal(self.sidebar.add_btn.pos())
        pos.setY(pos.y() + self.sidebar.add_btn.height() + 8)
        menu.exec_(pos)

    def _open_camera(self):
        dialog = CameraDialog(self)
        dialog.capture_taken.connect(self._on_camera_capture)
        dialog.exec_()

    def _on_camera_capture(self, image_array):
        self._run_ocr(image_array=image_array)

    def _show_camera_info(self):
        QMessageBox.information(
            self, "摄像头功能",
            "📷 摄像头拍摄功能说明\n\n"
            "由于摄像头设备驱动差异较大，推荐使用以下更稳定的方式：\n\n"
            "1️⃣  **截图识别** (Ctrl+Shift+S)\n"
            "    使用电脑自带的相机APP拍照后，按快捷键截图识别\n\n"
            "2️⃣  **导入图片**\n"
            "    用手机或相机拍照后，将图片文件导入电脑进行识别\n\n"
            "3️⃣  **拖拽识别**\n"
            "    直接将图片文件拖入程序窗口即可自动识别\n\n"
            "💡  小提示：拍摄时请确保生产日期和保质期清晰对焦"
        )

    def _take_screenshot(self):
        if self.isVisible():
            self.showMinimized()
        QApplication.processEvents()

        def on_screenshot_taken(img_array):
            if self.isMinimized():
                self.showNormal()
                self.raise_()
                self.activateWindow()
            self._run_ocr(image_array=img_array)

        def on_cancelled():
            if self.isMinimized():
                self.showNormal()
                self.raise_()
                self.activateWindow()

        selector = ScreenshotSelector(self)
        selector.screenshot_taken.connect(on_screenshot_taken)
        selector.cancelled.connect(on_cancelled)

    def _import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if file_path:
            self._run_ocr(image_path=file_path)

    def _run_ocr(self, image_path=None, image_array=None):
        ocr = OCREngine()
        if not ocr.is_available():
            reply = QMessageBox.question(
                self, "OCR不可用",
                "⚠️  OCR识别引擎暂时不可用\n\n"
                "可能原因：EasyOCR依赖不完整或PyTorch版本冲突\n\n"
                "是否切换到「手动添加」模式？\n"
                "（您仍可手动输入物品信息）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._add_manual_item()
            return

        dialog = OCRProgressDialog(self, image_path, image_array)
        result = dialog.exec_()

        if hasattr(dialog, 'error_detail') and dialog.error_detail:
            reply = QMessageBox.question(
                self, "OCR识别失败",
                f"❌ OCR识别过程中出现问题：\n\n{dialog.error_detail}\n\n"
                f"是否切换到「手动添加」模式？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._add_manual_item()
            return

        if result == QDialog.Accepted and dialog.result:
            self._process_ocr_result(dialog.result)

    def _process_ocr_result(self, ocr_result):
        if not ocr_result.get('success'):
            QMessageBox.warning(
                self, "识别失败",
                f"OCR识别过程中出现错误:\n{ocr_result.get('error', '未知错误')}\n\n请尝试手动添加。"
            )
            return

        product_name = ocr_result.get('product_name', '').strip() or '未命名物品'
        expiry_date = ocr_result.get('expiry_date', '').strip()
        category = ocr_result.get('category', '其他')

        if not expiry_date:
            QMessageBox.information(
                self, "未识别到日期",
                "未能从图片中识别出有效的到期日期。\n"
                "请在弹出的对话框中手动填写到期日期。"
            )
            from PyQt5.QtCore import QDate
            current = QDate.currentDate().addDays(7)
            expiry_date = current.toString("yyyy-MM-dd")

        initial_data = {
            'name': product_name,
            'expiry_date': expiry_date,
            'location': '',
            'category': category
        }

        confirm_dialog = ItemDialog(self, item_data=initial_data)
        confirm_dialog.setWindowTitle("确认并录入")
        confirm_dialog.item_saved.connect(self._on_item_saved)
        confirm_dialog.exec_()

    def _on_reminder(self, reminders):
        for reminder in reminders:
            self.notification_manager.show_notification(reminder)

    def _on_reminder_check_complete(self, stats):
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
                    event.acceptProposedAction()
                    self.drop_hint.show()
                    self.drop_hint.raise_()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_hint.hide()

    def dropEvent(self, event):
        self.drop_hint.hide()
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
                    self._run_ocr(image_path=path)
                    break

    def closeEvent(self, event):
        self.notification_manager.close_all()
        event.accept()
