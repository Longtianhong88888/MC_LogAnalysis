import sys
import time

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from app import App
from utils.resource_utils import resource_path
from views.main_window import WINDOW_DEFAULT_SIZE

SPLASH_MIN_MS = 500  # 启动画面最短展示时间
FADE_MS = 300        # 淡入淡出过渡时长
_ANIMS = set()       # 持有运行中的动画引用，防止被提前回收


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


def _crossfade(splash, window, duration=FADE_MS):
    """启动画面平滑淡出，露出下方已就绪的主窗口，避免生硬切换。"""
    fade_out = QPropertyAnimation(splash, b"windowOpacity")
    fade_out.setDuration(duration)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)
    fade_out.setEasingCurve(QEasingCurve.InOutQuad)
    _ANIMS.add(fade_out)

    def _finish():
        splash.hide()
        splash.finish(window)
        _ANIMS.discard(fade_out)

    fade_out.finished.connect(_finish)
    fade_out.start()


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
        remaining_ms = max(0, SPLASH_MIN_MS - elapsed_ms)
        QTimer.singleShot(remaining_ms, lambda: _crossfade(splash, window))

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
