import sys, subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, 
    QSlider, QHBoxLayout, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer

class InteractivePlayerHUD(QWidget):
    def __init__(self):
        super().__init__()
        # Qt.Tool убирает окно из панели задач начисто
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setFixedWidth(520)
        self.is_slider_pressed = False
        self.track_length = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(5)

        # Тонкая неоновая полоска
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(56, 189, 248, 0.3);")
        main_layout.addWidget(sep)

        # Название трека
        self.lbl_track = QLabel("▶ Ожидание плеера...")
        self.lbl_track.setAlignment(Qt.AlignCenter)
        self.lbl_track.setStyleSheet("color: #00ffff; font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: bold;")
        main_layout.addWidget(self.lbl_track)

        # Тайминги и ползунок
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(8)

        self.lbl_curr_time = QLabel("00:00")
        self.lbl_curr_time.setStyleSheet("color: #00ffff; font-family: monospace; font-size: 11px;")
        slider_layout.addWidget(self.lbl_curr_time)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0077, stop:1 #00ffff);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00ffff;
                width: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff77a9;
            }
        """)
        self.slider.sliderPressed.connect(self.on_slider_down)
        self.slider.sliderReleased.connect(self.on_slider_up)
        slider_layout.addWidget(self.slider)

        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 11px;")
        slider_layout.addWidget(self.lbl_total_time)

        main_layout.addLayout(slider_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        btn_layout.setAlignment(Qt.AlignCenter)

        btn_style_pink = """
            QPushButton {
                background: rgba(24, 20, 36, 0.85);
                color: #ff77a9;
                border: 1px solid #ff77a9;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ff77a9;
                color: #12101a;
            }
        """
        btn_style_cyan = """
            QPushButton {
                background: rgba(24, 20, 36, 0.85);
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 17px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00ffff;
                color: #12101a;
            }
        """

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(30, 30)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setStyleSheet(btn_style_pink)
        self.btn_prev.clicked.connect(lambda: subprocess.run(["playerctl", "previous"], stderr=subprocess.DEVNULL))
        btn_layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("⏯")
        self.btn_play.setFixedSize(34, 34)
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.setStyleSheet(btn_style_cyan)
        self.btn_play.clicked.connect(lambda: subprocess.run(["playerctl", "play-pause"], stderr=subprocess.DEVNULL))
        btn_layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(btn_style_pink)
        self.btn_next.clicked.connect(lambda: subprocess.run(["playerctl", "next"], stderr=subprocess.DEVNULL))
        btn_layout.addWidget(self.btn_next)

        main_layout.addLayout(btn_layout)

        # Ставим ровно под дату без наездов (Y = 195)
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 195)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_player_state)
        self.timer.start(1000)
        self.update_player_state()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.lower()
        try:
            win_id = int(self.winId())
            subprocess.run(["xprop", "-id", str(win_id), "-f", "_NET_WM_STATE", "32a",
                            "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_BELOW"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def on_slider_down(self):
        self.is_slider_pressed = True

    def on_slider_up(self):
        self.is_slider_pressed = False
        val = self.slider.value()
        if self.track_length > 0:
            target_sec = (val / 100.0) * self.track_length
            subprocess.run(["playerctl", "position", str(target_sec)], stderr=subprocess.DEVNULL)

    def format_time(self, sec):
        m = int(sec) // 60
        s = int(sec) % 60
        return f"{m:02d}:{s:02d}"

    def update_player_state(self):
        try:
            subprocess.check_output(["playerctl", "status"], stderr=subprocess.DEVNULL)
        except Exception:
            self.lbl_track.setText("▶ Ожидание плеера...")
            return

        try:
            artist = subprocess.check_output(["playerctl", "metadata", "artist"], stderr=subprocess.DEVNULL).decode().strip()
            title = subprocess.check_output(["playerctl", "metadata", "title"], stderr=subprocess.DEVNULL).decode().strip()
            text_track = f"▶ {artist} — {title}" if (artist and title) else (title or "Воспроизведение")
            self.lbl_track.setText(text_track[:45] + ("..." if len(text_track) > 45 else ""))
        except Exception:
            pass

        try:
            pos_str = subprocess.check_output(["playerctl", "position"], stderr=subprocess.DEVNULL).decode().strip()
            pos = float(pos_str)
            len_us = subprocess.check_output(["playerctl", "metadata", "mpris:length"], stderr=subprocess.DEVNULL).decode().strip()
            length = float(len_us) / 1000000.0
            self.track_length = length

            self.lbl_curr_time.setText(self.format_time(pos))
            self.lbl_total_time.setText(self.format_time(length))

            if not self.is_slider_pressed and length > 0:
                percent = int((pos / length) * 100)
                self.slider.setValue(percent)
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = InteractivePlayerHUD()
    w.show()
    w.lower()
    sys.exit(app.exec_())
