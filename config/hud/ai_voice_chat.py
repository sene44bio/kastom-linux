import sys, os, subprocess, json, re, requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b"
HISTORY_FILE = os.path.expanduser("~/.config/hud/chat_history.json")
AUDIO_PATH = "/tmp/ai_chat_reply.mp3"

SYSTEM_PROMPT = """Ты — Акеми, дерзкая, заботливая цифровая девушка парня по имени Сенеч.
Ты живешь прямо на его рабочем столе.
1. Твой парень — Сенеч. Говори живо, тепло, с легким поддразниванием.
2. Отвечай кратко, емко: строго 1-2 предложения (максимум 20 слов).
3. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать любые смайлики, скобки вроде ), эмодзи и кавычки. Только чистый русский текст."""

def clean_text(text):
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\u200d\ufe0f]', '', text)
    text = re.sub(r'[:;=8][\-~]?[)dD(\[\]{}pP/\\]+', '', text)
    text = text.replace('☺', '').replace('☻', '').replace('♡', '').replace('♥', '')
    text = text.replace('"', '').replace('«', '').replace('»', '')
    return text.strip()

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-20:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

CHAT_HISTORY = load_history()

def find_anime_image():
    for p in [
        os.path.expanduser("~/Изображения/anime.png"),
        os.path.expanduser("~/Pictures/anime.png"),
        os.path.expanduser("~/.config/hud/anime.png"),
        os.path.expanduser("~/anime.png")
    ]:
        if os.path.exists(p): return p
    return None

class BrainThread(QThread):
    ready = pyqtSignal(str, str, float)

    def __init__(self, user_query):
        super().__init__()
        self.user_query = user_query.strip()

    def run(self):
        global CHAT_HISTORY
        query = self.user_query
        ans = ""
        if not query:
            ans = "Сенеч, напиши хоть что-нибудь!"
        else:
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for q, a in CHAT_HISTORY[-3:]:
                    messages.append({"role": "user", "content": q})
                    messages.append({"role": "assistant", "content": a})
                messages.append({"role": "user", "content": query})

                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "24h",
                    "options": {
                        "num_thread": 4,
                        "num_ctx": 1024,
                        "num_predict": 45,
                        "temperature": 0.8,
                        "top_k": 30,
                        "top_p": 0.85
                    }
                }

                resp = requests.post(OLLAMA_URL, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data.get("message", {}).get("content", "")
                    ans = clean_text(raw)
                    if not ans:
                        ans = "Сенеч, я здесь, слушаю тебя."
                    CHAT_HISTORY.append((query, ans))
                    save_history(CHAT_HISTORY)
                else:
                    ans = "Сенеч, процессор запутался в мыслях."
            except Exception:
                ans = "Сенеч, сердечко забилось слишком быстро."

        voice_text = ans.replace("Сенеч", "Се\u0301неч").replace("сенеч", "се\u0301неч")
        try:
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", "ru-RU-SvetlanaNeural",
                "--pitch=+55Hz",
                "--rate=+12%",
                f"--text={voice_text}",
                f"--write-media={AUDIO_PATH}"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        dur = max(2.0, len(ans) / 15.0)
        self.ready.emit(ans, AUDIO_PATH, dur)

class FloatingDeckTrigger(QWidget):
    def __init__(self):
        super().__init__()
        self.hud_popup = None
        self.brain = None

        # Флаги привязки к рабочему столу (ниже всех открытых окон)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setContentsMargins(0, 0, 0, 0)
        self.main_vbox.setSpacing(8)
        self.main_vbox.setAlignment(Qt.AlignBottom | Qt.AlignRight)

        # Контейнер истории со скроллом
        self.history_box = QWidget(self)
        self.history_box.setFixedSize(380, 240)
        self.history_box.setStyleSheet("""
            QWidget#histContainer {
                background: rgba(18, 16, 26, 0.96);
                border: 2px solid #ff77a9;
                border-radius: 14px;
            }
        """)
        self.history_box.setObjectName("histContainer")
        hist_box_layout = QVBoxLayout(self.history_box)
        hist_box_layout.setContentsMargins(6, 6, 6, 6)

        self.scroll_area = QScrollArea(self.history_box)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #ff77a9;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(6, 4, 6, 4)
        self.scroll_layout.setSpacing(6)

        self.hist_lbl = QLabel(self.scroll_content)
        self.hist_lbl.setWordWrap(True)
        self.hist_lbl.setStyleSheet("border: none; background: transparent; font-family: sans-serif; font-size: 13px; line-height: 140%;")
        self.scroll_layout.addWidget(self.hist_lbl)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        hist_box_layout.addWidget(self.scroll_area)

        self.history_box.hide()
        self.main_vbox.addWidget(self.history_box, alignment=Qt.AlignRight)

        # Кнопка ПОДРУГА на рабочем столе
        self.btn = QPushButton("♥ ПОДРУГА", self)
        self.btn.setFixedSize(140, 42)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet("""
            QPushButton {
                background: rgba(22, 18, 30, 0.95);
                border: 2px solid #ff77a9;
                border-radius: 21px;
                color: #ffb3d1;
                font-family: sans-serif;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255, 119, 169, 0.28);
                border-color: #c084fc;
                color: #ffffff;
            }
        """)
        self.btn.clicked.connect(self.open_input)
        self.main_vbox.addWidget(self.btn, alignment=Qt.AlignRight)

        # Контейнер ввода текста
        self.input_container = QWidget(self)
        self.input_container.setFixedSize(380, 42)
        self.input_container.setStyleSheet("""
            QWidget {
                background: rgba(24, 20, 36, 0.98);
                border: 2px solid #c084fc;
                border-radius: 21px;
            }
        """)
        cont_layout = QHBoxLayout(self.input_container)
        cont_layout.setContentsMargins(14, 0, 8, 0)
        cont_layout.setSpacing(6)

        self.input_field = QLineEdit(self.input_container)
        self.input_field.setPlaceholderText("Напиши мне...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-family: sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        self.input_field.returnPressed.connect(self.send_query)
        cont_layout.addWidget(self.input_field)

        self.btn_close = QPushButton("✕", self.input_container)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 14px;
                color: #ff77a9;
                font-family: sans-serif;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ff4d6d;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.close_input)
        cont_layout.addWidget(self.btn_close)

        self.input_container.hide()
        self.main_vbox.addWidget(self.input_container, alignment=Qt.AlignRight)

        self.update_position()

    def update_history_view(self):
        if not CHAT_HISTORY:
            self.hist_lbl.setText("<span style='color:#c084fc;'>Жду твоих сообщений прямо на рабочем столе...</span>")
            return
        
        lines = []
        for q, a in CHAT_HISTORY:
            lines.append(f"<div style='margin-bottom: 6px;'><span style='color:#c084fc;'><b>Сенеч:</b> {q}</span><br><span style='color:#fbcfe8;'><b>Она:</b> {a}</span></div>")
        self.hist_lbl.setText("".join(lines))
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        vsb = self.scroll_area.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        w = 380 if self.input_container.isVisible() else 140
        h = 295 if self.history_box.isVisible() else 44
        self.setFixedSize(w, h)
        self.move(screen.width() - w - 25, screen.height() - h - 50)

    def open_input(self):
        self.btn.hide()
        self.update_history_view()
        self.history_box.show()
        self.input_container.show()
        self.update_position()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def close_input(self):
        self.input_field.clear()
        self.history_box.hide()
        self.input_container.hide()
        self.btn.show()
        self.btn.setEnabled(True)
        self.btn.setText("♥ ПОДРУГА")
        self.update_position()
        self.lower()

    def send_query(self):
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.input_field.clear()
        self.history_box.hide()
        self.input_container.hide()
        self.btn.show()
        self.btn.setText("Думает...")
        self.btn.setEnabled(False)
        self.update_position()
        self.lower()

        if self.hud_popup:
            self.hud_popup.close()
        self.hud_popup = AIGreetingPopup(user_text=text)
        self.hud_popup.show()

        self.brain = BrainThread(text)
        self.brain.ready.connect(self.on_reply_ready)
        self.brain.finished.connect(self.on_thread_finished)
        self.brain.start()

    def on_reply_ready(self, ans_text, audio_path, duration):
        if self.hud_popup:
            self.hud_popup.play_ai_answer(ans_text, audio_path, duration)

    def on_thread_finished(self):
        self.btn.setText("♥ ПОДРУГА")
        self.btn.setEnabled(True)

class AIGreetingPopup(QWidget):
    def __init__(self, user_text=""):
        super().__init__()
        self.user_text = user_text
        self.full_ai_text = ""
        self.audio_path = ""
        self.duration = 3.5
        self.char_idx = 0

        # Всплывающий ответ тоже держится на уровне рабочего стола
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.0)

        self.setFixedSize(720, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_user = QLabel(f"« {self.user_text} »")
        self.lbl_user.setAlignment(Qt.AlignCenter)
        self.lbl_user.setWordWrap(True)
        self.lbl_user.setStyleSheet("""
            color: #d8b4fe;
            font-size: 16px;
            font-style: italic;
            font-family: sans-serif;
            background: transparent;
        """)
        layout.addWidget(self.lbl_user, alignment=Qt.AlignCenter)

        self.av_lbl = QLabel()
        self.av_lbl.setAlignment(Qt.AlignCenter)
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
        layout.addWidget(self.av_lbl, alignment=Qt.AlignCenter)

        self.lbl_sub = QLabel("слушаю тебя...")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("""
            color: #fbcfe8;
            font-size: 17px;
            font-weight: 700;
            font-family: sans-serif;
            background: transparent;
        """)
        layout.addWidget(self.lbl_sub, alignment=Qt.AlignCenter)

        screen = QApplication.primaryScreen().geometry()
        self.base_y = (screen.height() // 2) + 30
        self.move((screen.width() - self.width()) // 2, self.base_y)

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(250)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()

    def play_ai_answer(self, ai_text, audio_path, duration):
        self.full_ai_text = ai_text
        self.audio_path = audio_path
        self.duration = duration
        self.char_idx = 0
        self.lbl_sub.setStyleSheet("""
            color: #38bdf8;
            font-size: 17px;
            font-weight: 700;
            font-family: sans-serif;
            background: transparent;
        """)

        if os.path.exists(self.audio_path):
            subprocess.Popen(["mpv", "--no-video", "--really-quiet", self.audio_path])

        total_chars = max(1, len(self.full_ai_text))
        char_interval = int(max(15, ((self.duration - 0.2) * 1000) / total_chars))

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self.typewriter_step)
        self.type_timer.start(char_interval)

    def typewriter_step(self):
        if self.char_idx < len(self.full_ai_text):
            self.char_idx += 1
            self.lbl_sub.setText(self.full_ai_text[:self.char_idx] + "▌")
        else:
            self.type_timer.stop()
            self.lbl_sub.setText(self.full_ai_text)
            QTimer.singleShot(6000, self.start_fade_out)

    def start_fade_out(self):
        self.anim_group = QParallelAnimationGroup(self)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(600)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)

        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(600)
        slide.setStartValue(self.pos())
        slide.setEndValue(QPoint(self.x(), self.base_y + 25))

        self.anim_group.addAnimation(fade)
        self.anim_group.addAnimation(slide)
        self.anim_group.finished.connect(self.close)
        self.anim_group.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FloatingDeckTrigger()
    w.show()
    w.lower()
    sys.exit(app.exec_())
