import sys, os, subprocess, locale
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSlider, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except Exception:
    pass

class CyberCenterHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dragging = False
        self.total_duration = 0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        screen = QApplication.primaryScreen().geometry()
        w, h = 680, 220
        self.setGeometry((screen.width() - w) // 2, 25, w, h)

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_hud)
        self.timer.start(500)
        self.update_hud()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        # 1. Часы
        self.lbl_clock = QLabel()
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setStyleSheet("color: #00f0ff; font-size: 52px; font-weight: 900; font-family: 'Monospace', monospace;")
        layout.addWidget(self.lbl_clock)

        # 2. Дата
        self.lbl_date = QLabel()
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_date.setStyleSheet("color: #a855f7; font-size: 14px; font-weight: bold; margin-top: -6px;")
        layout.addWidget(self.lbl_date)

        # 3. Название трека
        self.lbl_track = QLabel("// CYBER_DECK READY //")
        self.lbl_track.setAlignment(Qt.AlignCenter)
        self.lbl_track.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(self.lbl_track)

        # 4. Ползунок и тайминги
        slider_box = QHBoxLayout()
        slider_box.setContentsMargins(40, 4, 40, 2)
        slider_box.setSpacing(12)

        self.lbl_pos = QLabel("00:00")
        self.lbl_pos.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: bold; font-family: monospace;")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #1e293b;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a855f7, stop:1 #00f0ff);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00f0ff;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                border: 2px solid #ffffff;
            }
            QSlider::handle:horizontal:hover {
                background: #ffffff;
            }
        """)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)

        self.lbl_len = QLabel("00:00")
        self.lbl_len.setStyleSheet("color: #a855f7; font-size: 11px; font-weight: bold; font-family: monospace;")

        slider_box.addWidget(self.lbl_pos)
        slider_box.addWidget(self.slider)
        slider_box.addWidget(self.lbl_len)
        layout.addLayout(slider_box)

        # 5. Кнопки управления
        btn_box = QHBoxLayout()
        btn_box.setSpacing(18)
        btn_box.setAlignment(Qt.AlignCenter)

        btn_style_small = """
            QPushButton {
                background: rgba(15, 23, 42, 0.6);
                color: #00f0ff;
                border: 1px solid rgba(0, 240, 255, 0.4);
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
                min-width: 34px;
                min-height: 34px;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.2);
                border: 1px solid #00f0ff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(168, 85, 247, 0.4);
                border: 1px solid #a855f7;
            }
        """

        btn_style_play = """
            QPushButton {
                background: rgba(15, 23, 42, 0.8);
                color: #00f0ff;
                border: 2px solid #00f0ff;
                border-radius: 22px;
                font-size: 17px;
                font-weight: bold;
                min-width: 44px;
                min-height: 44px;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.3);
                border: 2px solid #ffffff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(168, 85, 247, 0.4);
                border: 2px solid #a855f7;
            }
        """

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setStyleSheet(btn_style_small)
        self.btn_prev.clicked.connect(lambda: subprocess.Popen(["playerctl", "previous"]))

        self.btn_play = QPushButton("▶")
        self.btn_play.setStyleSheet(btn_style_play)
        self.btn_play.clicked.connect(lambda: subprocess.Popen(["playerctl", "play-pause"]))

        self.btn_next = QPushButton("⏭")
        self.btn_next.setStyleSheet(btn_style_small)
        self.btn_next.clicked.connect(lambda: subprocess.Popen(["playerctl", "next"]))

        btn_box.addWidget(self.btn_prev)
        btn_box.addWidget(self.btn_play)
        btn_box.addWidget(self.btn_next)
        layout.addLayout(btn_box)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            wid = str(int(self.winId()))
            subprocess.run([
                "xprop", "-id", wid,
                "-f", "_NET_WM_STATE", "32a",
                "-set", "_NET_WM_STATE", "_NET_WM_STATE_STICKY, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER, _NET_WM_STATE_BELOW"
            ], check=False)
            self.lower()
        except Exception:
            pass

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.showNormal()
            self.lower()
        super().changeEvent(event)

    def fmt_time(self, s):
        return f"{int(s) // 60:02d}:{int(s) % 60:02d}"

    def on_slider_pressed(self):
        self.is_dragging = True

    def on_slider_moved(self, val):
        self.lbl_pos.setText(self.fmt_time(val))

    def on_slider_released(self):
        target_pos = self.slider.value()
        subprocess.Popen(["playerctl", "position", str(target_pos)])
        self.is_dragging = False

    def update_hud(self):
        # Часы и дата
        now = datetime.now()
        self.lbl_clock.setText(now.strftime("%H:%M"))
        self.lbl_date.setText(now.strftime("%A, %d %B %Y").capitalize())

        # Статус плеера
        try:
            status = subprocess.check_output("playerctl status 2>/dev/null", shell=True).decode().strip()
        except Exception:
            status = ""

        if not status:
            self.lbl_track.setText("// CYBER_DECK READY //")
            self.lbl_pos.setText("00:00")
            self.lbl_len.setText("00:00")
            self.btn_play.setText("▶")
            if not self.is_dragging:
                self.slider.setValue(0)
            return

        self.btn_play.setText("⏸" if status == "Playing" else "▶")

        try:
            track = subprocess.check_output("playerctl metadata --format '{{ artist }} – {{ title }}' 2>/dev/null", shell=True).decode().strip()
            if not track or track == "–":
                track = subprocess.check_output("playerctl metadata --format '{{ title }}' 2>/dev/null", shell=True).decode().strip() or "Playing..."
        except Exception:
            track = "Audio Stream"

        prefix = "▶ " if status == "Playing" else "⏸ "
        self.lbl_track.setText(f"{prefix}{track[:48]}")

        try:
            pos = float(subprocess.check_output("playerctl position 2>/dev/null", shell=True).decode().strip())
        except Exception:
            pos = 0.0

        try:
            length = float(subprocess.check_output("playerctl metadata mpris:length 2>/dev/null", shell=True).decode().strip()) / 1000000.0
        except Exception:
            length = 0.0

        self.total_duration = length
        self.lbl_len.setText(self.fmt_time(length) if length > 0 else "--:--")

        if not self.is_dragging and length > 0:
            self.slider.setRange(0, int(length))
            self.slider.setValue(int(pos))
            self.lbl_pos.setText(self.fmt_time(pos))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = CyberCenterHUD()
    hud.show()
    sys.exit(app.exec_())
