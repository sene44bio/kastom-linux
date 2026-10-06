import sys, os, json, subprocess, fcntl, datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QPixmap, QColor, QPainter, QPainterPath
from llama_cpp import Llama

# Защита от дублей
lock_file = open('/tmp/ai_greeting.lock', 'w')
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    sys.exit(0)

AUDIO_PATH = "/tmp/ai_greeting.mp3"
MODEL_PATH = os.path.expanduser("~/.config/hud/models/qwen2.5-1.5b.gguf")

def find_anime_image():
    candidates = [
        os.path.expanduser("~/Изображения/anime.png"),
        os.path.expanduser("~/Pictures/anime.png"),
        os.path.expanduser("~/.config/hud/anime.png"),
        os.path.expanduser("~/anime.png"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    for d in [os.path.expanduser("~/Изображения"), os.path.expanduser("~/Pictures")]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if "anime" in f.lower() and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return os.path.join(d, f)
    return None

WEATHER_RU = {
    0: "ясно", 1: "в основном ясно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 51: "морось", 61: "небольшой дождь", 63: "дождь",
    71: "снегопад", 73: "снег", 75: "сильный снег", 95: "гроза"
}

def get_live_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=56.8433&longitude=60.6044&current=temperature_2m,weather_code&timezone=Asia%2FYekaterinburg"
        out = subprocess.check_output(["curl", "-s", "--max-time", "3", url], text=True)
        data = json.loads(out)
        curr = data.get("current", {})
        temp = round(curr.get("temperature_2m", 0))
        code = curr.get("weather_code", 2)
        desc = WEATHER_RU.get(code, "переменная облачность")
        return f"{temp:+d}°C", desc
    except Exception:
        return "+3°C", "переменная облачность"

def generate_ai_phrase(weather_temp, weather_desc):
    now = datetime.datetime.now()
    hour = now.hour
    time_str = now.strftime("%H:%M")
    
    if 0 <= hour < 6:
        time_desc = "глубокая ночь, пора спать"
    elif 6 <= hour < 12:
        time_desc = "утро, время просыпаться"
    elif 12 <= hour < 18:
        time_desc = "день, разгар работы"
    else:
        time_desc = "вечер, время отдыха"

    try:
        llm = Llama(model_path=MODEL_PATH, n_ctx=512, n_threads=4, verbose=False)
        sys_prompt = (
            "Ты — бортовой искусственный интеллект кибердеки. Твоего оператора зовут Сенеч.\n"
            "Твоя задача: поприветствовать оператора короткой и живой фразой ровно в 1-2 предложения.\n"
            "Обязательно обратись к нему по имени: Сенеч.\n"
            "Упомяни погоду или время суток с легкой иронией или киберпанк стилем.\n"
            "Никогда не отказывайся и не извиняйся. Не используй кавычки, смайлики и эмодзи."
        )
        user_prompt = f"Время: {time_str} ({time_desc}). Погода в городе: {weather_temp}, {weather_desc}. Поприветствуй Сенеча."
        full_prompt = f"<|im_start|>system\n{sys_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\nСенеч, "
        
        res = llm(full_prompt, max_tokens=60, stop=["<|im_end|>", "\n"], temperature=0.6)
        text = res["choices"][0]["text"].strip()
        text = "Сенеч, " + text.replace('"', '').replace('«', '').replace('»', '')
        
        # Если модель все же сглючила
        bad_words = ["извините", "не могу", "контекст", "как языковая модель"]
        if any(w in text.lower() for w in bad_words) or len(text) < 15:
            text = f"Сенеч, системы активны. На часах {time_str}, за бортом {weather_temp}, {weather_desc}."
            
        return text
    except Exception:
        return f"Сенеч, все системы в строю! За бортом {weather_temp}, {weather_desc}."

def get_audio_duration(file_path):
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ], text=True)
        return float(out.strip())
    except Exception:
        pass
    try:
        out = subprocess.check_output([
            "mpv", "--no-video", "--frames=0", "--term-playing-msg=${=duration}", file_path
        ], text=True)
        for line in out.splitlines():
            try: return float(line.strip())
            except ValueError: continue
    except Exception:
        pass
    return 5.5

class SpeechWorker(QThread):
    ready = pyqtSignal(str, str, float)

    def run(self):
        weather_temp, weather_desc = get_live_weather()
        ai_text = generate_ai_phrase(weather_temp, weather_desc)

        # Фонетика имени для синтезатора
        voice_text = ai_text.replace("Сенеч", "Се\u0301неч").replace("сенеч", "се\u0301неч")

        try:
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", "ru-RU-SvetlanaNeural",
                "--pitch=+70Hz",
                "--rate=+12%",
                f"--text={voice_text}",
                f"--write-media={AUDIO_PATH}"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        duration = get_audio_duration(AUDIO_PATH)
        self.ready.emit(ai_text, AUDIO_PATH, duration)

class AIGreetingHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYBER_AI_GREETING")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setWindowOpacity(0.0)

        self.full_text = ""
        self.char_idx = 0
        self.base_y = 0

        self.init_ui()
        self.center_under_logo()

        self.worker = SpeechWorker()
        self.worker.ready.connect(self.on_speech_ready)
        self.worker.start()

    def init_ui(self):
        self.setFixedSize(680, 280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Аватарка
        self.av_lbl = QLabel()
        self.av_lbl.setAlignment(Qt.AlignCenter)
        self.av_lbl.setStyleSheet("background: transparent;")
        
        img_path = find_anime_image()
        if img_path and os.path.exists(img_path):
            src_pix = QPixmap(img_path)
            size = 145
            scaled = src_pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            path = QPainterPath()
            path.addEllipse(4, 4, size-8, size-8)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            self.av_lbl.setPixmap(rounded)
        else:
            self.av_lbl.setText("🌸")
            self.av_lbl.setStyleSheet("font-size: 70px; background: transparent;")
            
        layout.addWidget(self.av_lbl, alignment=Qt.AlignCenter)

        # 2. Субтитры
        self.lbl_sub = QLabel("")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("""
            color: #00f0ff;
            font-size: 16px;
            font-weight: 800;
            font-family: monospace;
            background: transparent;
            qproperty-alignment: AlignCenter;
            text-shadow: 1px 1px 2px #000000, -1px -1px 2px #000000, 1px -1px 2px #000000, -1px 1px 2px #000000;
        """)
        layout.addWidget(self.lbl_sub, alignment=Qt.AlignCenter)

    def center_under_logo(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        self.base_y = (screen.height() // 2) + 85
        self.move(x, self.base_y)

    def on_speech_ready(self, sub_text, audio_file, duration):
        self.full_text = sub_text
        self.lbl_sub.setText("")
        self.char_idx = 0

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(450)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_in.start()

        if os.path.exists(audio_file):
            subprocess.Popen(["mpv", "--no-video", "--really-quiet", audio_file])

        total_chars = max(1, len(self.full_text))
        char_interval = int(max(20, ((duration - 0.3) * 1000) / total_chars))

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self.typewriter_step)
        self.type_timer.start(char_interval)

    def typewriter_step(self):
        if self.char_idx < len(self.full_text):
            self.char_idx += 1
            self.lbl_sub.setText(self.full_text[:self.char_idx] + "█")
        else:
            self.type_timer.stop()
            self.lbl_sub.setText(self.full_text)
            QTimer.singleShot(5000, self.start_fade_out)

    def start_fade_out(self):
        self.anim_group = QParallelAnimationGroup(self)

        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(950)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InQuad)

        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(950)
        slide.setStartValue(self.pos())
        slide.setEndValue(QPoint(self.x(), self.base_y + 30))
        slide.setEasingCurve(QEasingCurve.InCubic)

        self.anim_group.addAnimation(fade)
        self.anim_group.addAnimation(slide)
        self.anim_group.finished.connect(self.close_and_exit)
        self.anim_group.start()

    def close_and_exit(self):
        self.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AIGreetingHUD()
    w.show()
    sys.exit(app.exec_())
