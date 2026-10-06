import sys, subprocess, threading
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QPainter, QColor, QLinearGradient

class CavaDock(QWidget):
    def __init__(self, config_path):
        super().__init__()
        self.bars_count = 64
        self.values = [0] * self.bars_count

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        screen = QApplication.primaryScreen().geometry()
        self.bar_h = 110
        self.setGeometry(25, screen.height() - self.bar_h - 44, screen.width() - 50, self.bar_h)

        self.proc = subprocess.Popen(
            ['cava', '-p', config_path],
            stdout=subprocess.PIPE,
            bufsize=self.bars_count
        )

        self.thread = threading.Thread(target=self.read_cava, daemon=True)
        self.thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            wid = str(int(self.winId()))
            subprocess.run([
                'xprop', '-id', wid,
                '-f', '_NET_WM_WINDOW_TYPE', '32a',
                '-set', '_NET_WM_WINDOW_TYPE', '_NET_WM_WINDOW_TYPE_DESKTOP'
            ], check=False)
            subprocess.run([
                'xprop', '-id', wid,
                '-f', '_NET_WM_STATE', '32a',
                '-set', '_NET_WM_STATE', '_NET_WM_STATE_STICKY, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER, _NET_WM_STATE_BELOW'
            ], check=False)
            self.lower()
        except Exception:
            pass

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.showNormal()
            self.lower()
        super().changeEvent(event)

    def read_cava(self):
        while True:
            data = self.proc.stdout.read(self.bars_count)
            if not data:
                break
            self.values = list(data)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = (w - (self.bars_count * 4)) / self.bars_count

        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, QColor('#a855f7'))
        grad.setColorAt(1.0, QColor('#00f0ff'))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)

        for i, val in enumerate(self.values):
            bh = (val / 255.0) * h
            if bh < 2:
                bh = 2
            x = i * (bar_w + 4)
            y = h - bh
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bh), 2, 2)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = sys.argv[1] if len(sys.argv) > 1 else '/home/sene44/.config/cava/config_dock'
    widget = CavaDock(cfg)
    widget.show()
    sys.exit(app.exec_())
