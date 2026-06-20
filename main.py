import os
import sys
import signal

def main():
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Microsoft YaHei")
    font.setPointSize(10)
    app.setFont(font)

    from config import APP_NAME, APP_DISPLAY_NAME, APP_VERSION
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)

    from modules.ui.main_window import MainWindow
    from modules.ui.system_tray import SystemTray

    main_window = MainWindow()
    tray = SystemTray(app)

    def show_window():
        if main_window.isMinimized():
            main_window.showNormal()
        elif not main_window.isVisible():
            main_window.show()
        main_window.raise_()
        main_window.activateWindow()

    tray.show_window_requested.connect(show_window)
    tray.take_screenshot_requested.connect(lambda: main_window._take_screenshot())
    tray.import_image_requested.connect(lambda: main_window._import_image())
    tray.add_item_requested.connect(lambda: main_window._add_manual_item())

    def quit_app():
        tray.cleanup()
        main_window.close()
        app.quit()

    tray.quit_requested.connect(quit_app)

    def refresh_all():
        main_window.refresh_items()
        main_window.sidebar.refresh()
        tray.update_status()

    main_window.refresh_items()
    tray.update_status()

    show_window()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
