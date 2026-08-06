import sys
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from app import App
from utils.resource_utils import resource_path
from views.main_window import WINDOW_DEFAULT_SIZE

SPLASH_MIN_MS = 500  # 启动画面最短展示时间


def create_splash():
    """根据 Machine.png 生成启动画面，尺寸与主窗口一致（cover 裁切填满）。"""
    pixmap = QPixmap(resource_path("Machine.png"))
    if pixmap.isNull():
        return None
    w, h = WINDOW_DEFAULT_SIZE
    img = pixmap.toImage()
    scale = max(w / img.width(), h / img.height())
    sw, sh = int(img.width() * scale), int(img.height() * scale)
    img = img.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    img = img.copy(x, y, w, h)
    return QSplashScreen(QPixmap.fromImage(img))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MC Log Analysis Tool")
    icon = QIcon(resource_path("log.ico"))
    if not icon.isNull():
        app.setWindowIcon(icon)

    splash_start = time.monotonic()
    splash = create_splash()
    if splash is not None:
        splash.show()
        splash.showMessage(
            "正在启动 MC Log Analysis Tool ...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white,
        )
        app.processEvents()

    window = App().root
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    if splash is not None:
        elapsed_ms = int((time.monotonic() - splash_start) * 1000)
        remaining_ms = SPLASH_MIN_MS - elapsed_ms
        if remaining_ms > 0:
            # 让事件循环继续运行，到点后再关闭启动画面
            QTimer.singleShot(remaining_ms, lambda: splash.finish(window))
        else:
            splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
