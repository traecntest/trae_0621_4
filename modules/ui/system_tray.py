import os
import sys
from PyQt5.QtWidgets import (QSystemTrayIcon, QMenu, QAction, QApplication,
                             QMessageBox)
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QBrush

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import APP_DISPLAY_NAME, APP_DATA_DIR, DB_PATH
from modules.database import Database
from modules.reminder import ReminderEngine, calculate_days_remaining


def create_tray_icon(expiring_count: int = 0):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor(99, 102, 241))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 16, 16)

    painter.setPen(QColor(255, 255, 255))
    font = QFont("Microsoft YaHei")
    font.setPointSize(20)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "📦")

    if expiring_count > 0:
        painter.setBrush(QColor(239, 68, 68))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(42, 2, 20, 20)

        painter.setPen(QColor(255, 255, 255))
        font2 = QFont("Arial")
        font2.setPointSize(9)
        font2.setBold(True)
        painter.setFont(font2)
        count_text = str(expiring_count) if expiring_count < 100 else "99+"
        painter.drawText(42, 2, 20, 20, Qt.AlignCenter, count_text)

    painter.end()
    return QIcon(pixmap)


class SystemTray(QObject):
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    take_screenshot_requested = pyqtSignal()
    import_image_requested = pyqtSignal()
    add_item_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.reminder_engine = ReminderEngine(self)

        self.tray_icon = QSystemTrayIcon(create_tray_icon(), parent)
        self.tray_icon.setToolTip(APP_DISPLAY_NAME)

        self._setup_menu()
        self._setup_signals()

        self.update_status()
        self.tray_icon.show()

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.update_status)
        self._status_timer.start(30 * 60 * 1000)

        self.reminder_engine.start()

    def _setup_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 8px;
                min-width: 220px;
            }
            QMenu::item {
                padding: 10px 20px 10px 16px;
                border-radius: 8px;
                font-size: 10pt;
                color: #374151;
            }
            QMenu::item:hover {
                background-color: #EEF2FF;
                color: #4338CA;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E5E7EB;
                margin: 8px 4px;
            }
        """)

        self.title_action = QAction("📦  " + APP_DISPLAY_NAME, self.menu)
        title_font = self.title_action.font()
        title_font.setBold(True)
        self.title_action.setFont(title_font)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)

        self.status_action = QAction("⏰  加载中...", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        self.show_action = QAction("🪟  打开主窗口", self.menu)
        self.show_action.triggered.connect(self.show_window_requested.emit)
        self.menu.addAction(self.show_action)

        self.menu.addSeparator()

        self.screenshot_action = QAction("🖼️  截图识别", self.menu)
        self.screenshot_action.triggered.connect(self.take_screenshot_requested.emit)
        self.menu.addAction(self.screenshot_action)

        self.import_action = QAction("📂  导入图片", self.menu)
        self.import_action.triggered.connect(self.import_image_requested.emit)
        self.menu.addAction(self.import_action)

        self.add_action = QAction("✏️  手动添加", self.menu)
        self.add_action.triggered.connect(self.add_item_requested.emit)
        self.menu.addAction(self.add_action)

        self.menu.addSeparator()

        self.reminder_action = QAction("🔔  立即检查提醒", self.menu)
        self.reminder_action.triggered.connect(self._check_now)
        self.menu.addAction(self.reminder_action)

        self.open_data_action = QAction("📁  打开数据目录", self.menu)
        self.open_data_action.triggered.connect(self._open_data_dir)
        self.menu.addAction(self.open_data_action)

        self.menu.addSeparator()

        self.quit_action = QAction("🚪  退出程序", self.menu)
        self.quit_action.triggered.connect(self._confirm_quit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _setup_signals(self):
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.reminder_engine.reminder_triggered.connect(self._on_reminder)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.show_window_requested.emit()

    def update_status(self):
        stats = self.db.get_stats()
        expiring = stats['expiring_3d']
        expired = stats['expired']

        if expired > 0 and expiring > 0:
            status_text = f"⚠️  {expired}件已过期，{expiring}件即将到期"
            badge_count = expired + expiring
        elif expired > 0:
            status_text = f"⚠️  {expired}件物品已过期"
            badge_count = expired
        elif expiring > 0:
            status_text = f"⏰  {expiring}件物品即将到期"
            badge_count = expiring
        else:
            status_text = f"✅  一切正常，共{stats['total']}件物品"
            badge_count = 0

        self.status_action.setText(status_text)
        self.tray_icon.setIcon(create_tray_icon(badge_count))
        tip_parts = [APP_DISPLAY_NAME, status_text]
        tip_parts.append(f"📁 数据目录: {APP_DATA_DIR}")
        self.tray_icon.setToolTip("\n".join(tip_parts))

    def _check_now(self):
        self.reminder_engine.force_check()
        self.update_status()

    def _on_reminder(self, reminders):
        for reminder in reminders:
            title = "⏰  物品到期提醒"
            message = reminder.get('suggestion', '')
            days = reminder.get('days_remaining', 0)
            if days < 0:
                icon = QSystemTrayIcon.Critical
            elif days <= 1:
                icon = QSystemTrayIcon.Warning
            else:
                icon = QSystemTrayIcon.Information
            self.tray_icon.showMessage(title, message, icon, 10000)

    def _open_data_dir(self):
        try:
            if sys.platform == 'win32':
                os.startfile(APP_DATA_DIR)
            elif sys.platform == 'darwin':
                os.system(f'open "{APP_DATA_DIR}"')
            else:
                os.system(f'xdg-open "{APP_DATA_DIR}"')
        except Exception as e:
            QMessageBox.information(
                None, "数据目录",
                f"数据目录位置:\n{APP_DATA_DIR}\n\n数据库文件: {DB_PATH}"
            )

    def _confirm_quit(self):
        reply = QMessageBox.question(
            None, "退出确认",
            f"确定要退出{APP_DISPLAY_NAME}吗？\n"
            f"退出后将无法收到物品到期提醒通知。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.tray_icon.hide()
            self.quit_requested.emit()

    def show_reminder_message(self, title: str, message: str, icon_type=QSystemTrayIcon.Information,
                              msecs: int = 10000):
        self.tray_icon.showMessage(title, message, icon_type, msecs)

    def cleanup(self):
        if self.tray_icon.isVisible():
            self.tray_icon.hide()
        self._status_timer.stop()
        self.reminder_engine.stop()
