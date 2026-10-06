import sys, os, json, subprocess
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, QTimer, QEvent, QThread, pyqtSignal, QPointF
from PyQt5.QtGui import QImage, QColor, QPixmap, QPainter, QPolygonF

PNG_PATH = os.path.expanduser("~/.config/hud/corgi_pixel.png")

def generate_corgi():
    W, H = 72, 72
    base = QImage(W, H, QImage.Format_ARGB32)
    base.fill(QColor(0, 0, 0, 0))

    p = QPainter(base)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)

    # 1. Внешние уши корги (полутон)
    p.setBrush(QColor(135, 135, 135))
    p.drawPolygon(QPolygonF([QPointF(12, 42), QPointF(17, 4), QPointF(32, 24)]))
    p.drawPolygon(QPolygonF([QPointF(60, 42), QPointF(55, 4), QPointF(40, 24)]))

    # 2. Внутренняя часть ушей (светлый тон)
    p.setBrush(QColor(215, 215, 215))
    p.drawPolygon(QPolygonF([QPointF(16, 36), QPointF(19, 10), QPointF(30, 24)]))
    p.drawPolygon(QPolygonF([QPointF(56, 36), QPointF(53, 10), QPointF(42, 24)]))

    # 3. Голова и пушистые щеки
    p.setBrush(QColor(140, 140, 140))
    p.drawEllipse(QPointF(36, 36), 22, 17)
    p.drawEllipse(QPointF(20, 42), 9, 9)
    p.drawEllipse(QPointF(52, 42), 9, 9)

    # 4. Белая грудка снизу
    p.setBrush(QColor(255, 255, 255))
    p.drawPolygon(QPolygonF([QPointF(18, 72), QPointF(36, 56), QPointF(54, 72)]))

    # 5. Белая морда и проточина на лоб
    p.drawPolygon(QPolygonF([QPointF(34, 18), QPointF(38, 18), QPointF(40, 34), QPointF(32, 34)]))
    p.drawEllipse(QPointF(36, 46), 14, 11)

    # 6. Темные глаза с белыми бликами
    p.setBrush(QColor(20, 20, 20))
    p.drawEllipse(QPointF(25, 33), 4.5, 4.5)
    p.drawEllipse(QPointF(47, 33), 4.5, 4.5)
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(QPointF(24, 32), 1.5, 1.5)
    p.drawEllipse(QPointF(46, 32), 1.5, 1.5)

    # 7. Черный нос корги с бликом
    p.setBrush(QColor(15, 15, 15))
    p.drawEllipse(QPointF(36, 42), 5.5, 3.8)
    p.setBrush(QColor(190, 190, 190))
    p.drawEllipse(QPointF(36, 41), 2.5, 1.2)

    # 8. Открытая пасть и высунутый язычок
    p.setBrush(QColor(30, 30, 30))
    p.drawPolygon(QPolygonF([QPointF(28, 48), QPointF(44, 48), QPointF(40, 60), QPointF(32, 60)]))
    p.setBrush(QColor(180, 180, 180))
    p.drawRoundedRect(32, 49, 8, 12, 3, 3)
    p.end()

    # Точечный дизеринг высокого разрешения (Floyd-Steinberg)
    lum = [[0.0] * W for _ in range(H)]
    alpha = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            c = base.pixelColor(x, y)
            alpha[y][x] = c.alpha()
            lum[y][x] = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()

    out = QImage(W, H, QImage.Format_ARGB32)
    out.fill(QColor(0, 0, 0, 0))

    for y in range(H):
        for x in range(W):
            if alpha[y][x] < 35:
                continue
            old_val = lum[y][x]
            new_val = 255.0 if old_val > 128.0 else 0.0
            err = old_val - new_val
            out.setPixelColor(x, y, QColor(250, 250, 250, 255) if new_val == 255.0 else QColor(10, 15, 29, 255))
            if x + 1 < W:
                lum[y][x + 1] += err * 7 / 16
            if y + 1 < H:
                if x - 1 >= 0:
                    lum[y + 1][x - 1] += err * 3 / 16
                lum[y + 1][x] += err * 5 / 16
                if x + 1 < W:
                    lum[y + 1][x + 1] += err * 1 / 16

    out.save(PNG_PATH, "PNG")

generate_corgi()

class WeatherWorker(QThread):
    data_loaded = pyqtSignal(dict)

    def run(self):
        data = None
        try:
            res = subprocess.run(["curl", "-s", "--max-time", "5", "https://wttr.in/Yekaterinburg?format=j1"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                raw = json.loads(res.stdout)
                curr = raw["current_condition"][0]
                t_c = int(curr["temp_C"])
                
                desc = curr.get("weatherDesc", [{}])[0].get("value", "").lower()
                w_code = 0
                if "snow" in desc: w_code = 71
                elif "rain" in desc or "drizzle" in desc: w_code = 61
                elif "overcast" in desc: w_code = 3
                elif "cloud" in desc: w_code = 2

                now = datetime.now()
                times = [f"{now.strftime('%Y-%m-%d')}T{(now.hour + i)%24:02d}:00" for i in range(1, 6)]
                hourly_temps = []
                hourly_codes = []
                try:
                    for i in range(1, 6):
                        fut_hour = (now.hour + i) % 24
                        b_idx = min(fut_hour // 3, 7)
                        w_h = raw["weather"][0]["hourly"][b_idx]
                        hourly_temps.append(int(w_h["tempC"]))
                        hourly_codes.append(w_code)
                except Exception:
                    hourly_temps = [t_c] * 5
                    hourly_codes = [w_code] * 5

                data = {
                    "current": {"temperature_2m": t_c, "weather_code": w_code},
                    "hourly": {"time": times, "temperature_2m": hourly_temps, "weather_code": hourly_codes}
                }
        except Exception:
            pass

        if not data:
            now = datetime.now()
            times = [f"{now.strftime('%Y-%m-%d')}T{(now.hour + i)%24:02d}:00" for i in range(1, 6)]
            data = {
                "current": {"temperature_2m": -4, "weather_code": 2},
                "hourly": {"time": times, "temperature_2m": [-4]*5, "weather_code": [2]*5}
            }

        self.data_loaded.emit(data)

WMO_ICONS = {
    0:  ("Ясно", "☼", "#00f0ff"),
    1:  ("В осн. ясно", "🌤", "#38bdf8"),
    2:  ("Переменная обл.", "⛅", "#38bdf8"),
    3:  ("Пасмурно", "☁", "#94a3b8"),
    45: ("Туман", "≡", "#94a3b8"),
    48: ("Иней", "≡", "#94a3b8"),
    51: ("Морось", "⛆", "#00f0ff"),
    61: ("Небол. дождь", "⛆", "#00f0ff"),
    63: ("Дождь", "⛆", "#00f0ff"),
    65: ("Ливень", "⛆", "#38bdf8"),
    71: ("Снегопад", "❄", "#a855f7"),
    73: ("Снег", "❄", "#a855f7"),
    75: ("Сильный снег", "❄", "#c084fc"),
    80: ("Ливень", "⛆", "#00f0ff"),
    95: ("Гроза", "⚡", "#f43f5e"),
}

class WeatherHUD(QWidget):
    def showEvent(self, event):
        super().showEvent(event)
        try:
            wid = str(int(self.winId()))
            import subprocess
            subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_WINDOW_TYPE", "32a", "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DOCK"], check=False)
            subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE", "_NET_WM_STATE_STICKY, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER, _NET_WM_STATE_BELOW"], check=False)
        except Exception:
            pass

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.showNormal()
            self.lower()
        super().changeEvent(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYBER_HUD_WEATHER")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(35, 25, 415, 205)

        self.init_ui()

        self.worker = WeatherWorker()
        self.worker.data_loaded.connect(self.update_data)
        self.worker.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.worker.start)
        self.timer.start(900000)

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        self.setStyleSheet("""
            WeatherHUD {
                background: rgba(10, 15, 29, 0.70);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 14px;
            }
        """)

        top_box = QHBoxLayout()
        top_box.setSpacing(14)

        avatar_frame = QFrame()
        avatar_frame.setFixedSize(76, 76)
        avatar_frame.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.85);
                border: 2px solid #00f0ff;
                border-radius: 14px;
            }
        """)
        av_layout = QVBoxLayout(avatar_frame)
        av_layout.setContentsMargins(0, 0, 0, 0)
        av_layout.setAlignment(Qt.AlignCenter)

        self.avatar_lbl = QLabel()
        if os.path.exists(PNG_PATH):
            self.avatar_lbl.setPixmap(QPixmap(PNG_PATH))
        av_layout.addWidget(self.avatar_lbl)
        top_box.addWidget(avatar_frame)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)

        lbl_radar = QLabel("// METEO_TELEMETRY //")
        lbl_radar.setStyleSheet("color: #00f0ff; font-size: 10px; font-weight: 900; letter-spacing: 1px; font-family: monospace;")

        self.lbl_city = QLabel("ЕКАТЕРИНБУРГ")
        self.lbl_city.setStyleSheet("color: #a855f7; font-size: 15px; font-weight: 900; font-family: monospace;")

        temp_row = QHBoxLayout()
        temp_row.setSpacing(8)

        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setStyleSheet("color: #00f0ff; font-size: 26px; font-weight: 900; font-family: monospace;")

        self.lbl_icon = QLabel("☼")
        self.lbl_icon.setStyleSheet("color: #00f0ff; font-size: 18px; font-weight: bold;")

        self.lbl_desc = QLabel("Загрузка...")
        self.lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: bold;")

        temp_row.addWidget(self.lbl_temp)
        temp_row.addWidget(self.lbl_icon)
        temp_row.addWidget(self.lbl_desc)
        temp_row.addStretch()

        info_box.addWidget(lbl_radar)
        info_box.addWidget(self.lbl_city)
        info_box.addLayout(temp_row)
        top_box.addLayout(info_box)
        root.addLayout(top_box)

        self.forecast_box = QHBoxLayout()
        self.forecast_box.setSpacing(6)
        self.cards = []

        for _ in range(5):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(15, 23, 42, 0.7);
                    border: 1px solid rgba(168, 85, 247, 0.35);
                    border-radius: 8px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 6, 4, 6)
            c_lay.setSpacing(3)
            c_lay.setAlignment(Qt.AlignCenter)

            l_time = QLabel("--:--")
            l_time.setStyleSheet("color: #94a3b8; font-size: 10px; font-family: monospace;")
            l_time.setAlignment(Qt.AlignCenter)

            l_icon = QLabel("☼")
            l_icon.setStyleSheet("color: #00f0ff; font-size: 16px; font-weight: bold;")
            l_icon.setAlignment(Qt.AlignCenter)

            l_temp = QLabel("--°")
            l_temp.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: bold; font-family: monospace;")
            l_temp.setAlignment(Qt.AlignCenter)

            c_lay.addWidget(l_time)
            c_lay.addWidget(l_icon)
            c_lay.addWidget(l_temp)

            self.forecast_box.addWidget(card)
            self.cards.append((l_time, l_icon, l_temp))

        root.addLayout(self.forecast_box)

    def update_data(self, data):
        curr = data.get("current", {})
        temp = round(curr.get("temperature_2m", 0))
        code = curr.get("weather_code", 0)

        desc, glyph, col = WMO_ICONS.get(code, ("Ясно", "☼", "#00f0ff"))
        self.lbl_temp.setText(f"{temp:+d}°C")
        self.lbl_icon.setText(glyph)
        self.lbl_icon.setStyleSheet(f"color: {col}; font-size: 18px; font-weight: bold;")
        self.lbl_desc.setText(desc)

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])

        now_hour = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for i, t in enumerate(times):
            if t >= now_hour:
                start_idx = i + 1
                break

        for card_idx in range(5):
            idx = start_idx + card_idx
            if idx < len(times):
                t_str = times[idx].split("T")[1][:5]
                t_val = round(temps[idx])
                c_val = codes[idx]
                _, c_glyph, c_col = WMO_ICONS.get(c_val, ("Ясно", "☼", "#00f0ff"))

                l_time, l_icon, l_temp = self.cards[card_idx]
                l_time.setText(t_str)
                l_icon.setText(c_glyph)
                l_icon.setStyleSheet(f"color: {c_col}; font-size: 16px; font-weight: bold;")
                l_temp.setText(f"{t_val:+d}°")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = WeatherHUD()
    w.show()
    sys.exit(app.exec_())
