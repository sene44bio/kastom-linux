import sys, os, subprocess, json, re, requests, time
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b"
HISTORY_FILE = os.path.expanduser("~/.config/hud/chat_history.json")
AUDIO_PATH = "/tmp/ai_chat_reply.mp3"
ALARM_SOUND = os.path.expanduser("~/.config/hud/alarm_sound.wav")

SYSTEM_PROMPT = """Ты — Акеми, дерзкая, заботливая цифровая девушка парня по имени Сенеч.
Ты живешь прямо на его рабочем столе.
1. Твой парень — Сенеч. Говори живо, тепло, с легким поддразниванием.
2. Отвечай кратко, емко: строго 1-2 предложения (максимум 20 слов).
3. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать любые смайлики, скобки вроде ), эмодзи и кавычки. Только чистый русский текст."""

SYNONYMS = {
    "action_off": ["выключи", "выруби", "офни", "погаси", "потуши", "загаси", "вырубай", "отключи", "выключить"],
    "action_reboot": ["перезагрузи", "ребутни", "рестартни", "перезапусти", "ребут"],
    "action_lock": ["заблокируй", "залочь", "локни", "запри"],
    "target_screen": ["моник", "монитор", "экран", "дисплей"],
    "target_pc": ["пк", "комп", "систему", "тачку", "пекарню", "комплюктер"],
    "media_next": ["дальше", "некст", "следующий", "след", "переключи"],
    "media_prev": ["назад", "предыдущий", "пред"],
    "media_pause": ["стоп", "пауза", "замри", "останови", "заткнись", "тишина", "хватит", "молчи"],
    "media_play": ["продолжи", "плей", "играй", "включи музыку", "запусти музыку"],
    "vol_up": ["громче", "прибавь", "погромче", "добавь звук", "сделай громче"],
    "vol_down": ["тише", "убавь", "потише", "сделай тише", "приглуши"],
    "intent_alarm": ["будильник", "разбуди", "подъем"],
    "intent_timer": ["таймер", "засеки", "напомни"],
    "intent_weather": ["погода", "погоду", "погоде", "температура", "градусник", "холодно", "тепло"],
    "intent_screenshot": ["скрин", "скриншот", "заскринь", "сделай скрин"],
    "intent_stats": ["ресурсы", "железо", "нагрузка", "процессор", "память", "что с пк", "статус"],
    "intent_sleep": ["отбой", "я спать", "спокойной ночи", "режим сна"]
}

WORD_NUMBERS = {
    "одну": 1, "один": 1, "минуту": 60, "минута": 60, "две": 2, "три": 3, "четыре": 4, 
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "полминуты": 30, "полчаса": 1800, "час": 3600, "полтора": 5400
}

def get_real_weather():
    try:
        r = requests.get("https://wttr.in/Yekaterinburg?format=j1", timeout=3)
        if r.status_code == 200:
            d = r.json()
            temp = d["current_condition"][0]["temp_C"]
            desc = d["current_condition"][0]["lang_ru"][0]["value"].lower()
            return f"В Екатеринбурге сейчас {temp} градусов, {desc}. Одевайся теплее, Сенеч!"
    except Exception:
        pass
    return "В Екатеринбурге морозно и свежо, держись в тепле, Сенеч."

def get_system_stats():
    try:
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'", shell=True).decode().strip()
        ram = subprocess.check_output("free -m | awk '/Mem:/ {printf(\"%.1f/%.1f ГБ\", $3/1024, $2/1024)}'", shell=True).decode().strip()
        return f"Процессор нагружен на {cpu} процентов, память занята на {ram}. Дека работает стабильно, Сенеч!"
    except Exception:
        return "Все датчики в зеленой зоне, станция функционирует штатно."

def parse_alarm_target(text):
    t = text.lower()
    now = datetime.now()

    # Поиск шаблонов: "на 23 25", "на 23:25", "в 8:00", "в 7 утра", "на 8 вечера"
    m = re.search(r'(?:на|в)\s+(\d{1,2})(?:[:\s\.](\d{2}))?', t)
    if m:
        h = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        if "вечера" in t and h < 12: h += 12
        if "утра" in t and h == 12: h = 0

        target = now.replace(hour=h, minute=mins, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        diff = int((target - now).total_seconds())
        time_display = f"{h:02d}:{mins:02d}"
        return diff, time_display
    return None, None

def parse_timer_seconds(text):
    t = text.lower()
    if "полтора часа" in t: return 5400
    if "полчаса" in t: return 1800
    if "полминуты" in t: return 30
    if "через час" in t or "на час" in t: return 3600
    if "минуту" in t and not re.search(r'\d+', t): return 60
    if "секунду" in t and not re.search(r'\d+', t): return 10

    sec = 0
    h_m = re.search(r'(\d+)\s*(?:час|часа|часов|h)', t)
    if h_m: sec += int(h_m.group(1)) * 3600

    m_m = re.search(r'(\d+)\s*(?:мин|минут|m)', t)
    if m_m: sec += int(m_m.group(1)) * 60

    s_m = re.search(r'(\d+)\s*(?:сек|секунд|s)', t)
    if s_m: sec += int(s_m.group(1))

    if sec == 0:
        words = t.split()
        for i, w in enumerate(words):
            if w in WORD_NUMBERS:
                val = WORD_NUMBERS[w]
                if i + 1 < len(words) and any(x in words[i+1] for x in ["мин", "минут"]): sec += val * 60
                elif i + 1 < len(words) and any(x in words[i+1] for x in ["час", "часа"]): sec += val * 3600
                elif i + 1 < len(words) and any(x in words[i+1] for x in ["сек", "секунд"]): sec += val

    if sec == 0:
        nums = re.findall(r'\b\d+\b', t)
        if nums:
            val = int(nums[0])
            sec = val if any(x in t for x in ["сек", "s"]) else val * 60

    return sec if sec > 0 else 60

def parse_system_intent(text):
    p = text.lower().strip()
    has = lambda grp: any(w in p for w in SYNONYMS[grp])

    # Глушение любого играющего будильника
    if any(w in p for w in ["заткнись", "выключи сигнал", "выруби будильник", "хватит орать", "стоп сигнал"]):
        return {"type": "stop_alarm_sound", "reply": "Сигнал выключен, отдыхай дальше, Сенеч."}

    # Режим "Отбой / Спать"
    if has("intent_sleep"):
        return {"type": "sleep_mode", "reply": "Спокойной ночи, Сенеч. Гашу станцию до твоего пробуждения."}

    # Скриншот рабочего стола
    if has("intent_screenshot"):
        return {"type": "screenshot", "reply": "Сделала снимок экрана и сохранила в Изображения."}

    # Статус железа
    if has("intent_stats"):
        return {"type": "stats", "reply": get_system_stats()}

    # Погода
    if has("intent_weather"):
        return {"type": "weather", "reply": get_real_weather()}

    # Будильник по времени часов (на 23 25 / на 8:00)
    if has("intent_alarm"):
        diff, t_str = parse_alarm_target(p)
        if diff:
            return {"type": "alarm", "seconds": diff, "target_str": t_str, "reply": f"Будильник на {t_str} установлен. Я разбужу тебя вовремя!"}
        else:
            sec = parse_timer_seconds(p)
            txt_desc = f"{sec // 60} мин" if sec >= 60 and sec % 60 == 0 else f"{sec} сек"
            return {"type": "timer", "seconds": sec, "reply": f"Будильник через {txt_desc} взведён. Прослежу за временем!"}

    # Обычный таймер
    if has("intent_timer"):
        sec = parse_timer_seconds(p)
        txt_desc = f"{sec // 60} мин" if sec >= 60 and sec % 60 == 0 else f"{sec} сек"
        return {"type": "timer", "seconds": sec, "reply": f"Таймер на {txt_desc} пошел. Время пошло, Сенеч!"}

    # Музыка
    if has("media_next"): return {"type": "media_next", "reply": "Следующий трек, Сенеч."}
    if has("media_prev"): return {"type": "media_prev", "reply": "Возвращаю трек назад."}
    if has("media_pause"): return {"type": "media_pause", "reply": "Музыка на паузе."}
    if has("media_play"): return {"type": "media_play", "reply": "Врубила музло дальше!"}

    # Громкость
    if "максимум" in p or "на всю" in p:
        return {"type": "set_vol", "val": 100, "reply": "Громкость на максимум, погнали!"}
    if "без звука" in p or "мут" in p:
        return {"type": "set_vol", "val": 0, "reply": "Звук полностью заглушен."}
    if has("vol_up"): return {"type": "vol_up", "reply": "Сделала громче на пять процентов."}
    if has("vol_down"): return {"type": "vol_down", "reply": "Сделала тише на пять процентов."}
    if "громкость" in p or "звук" in p:
        m = re.search(r'(\d+)', p)
        if m:
            v = int(m.group(1))
            return {"type": "set_vol", "val": v, "reply": f"Выставила громкость на {v} процентов."}

    # Экран и ПК
    if any(w in p for w in SYNONYMS["action_off"]) and any(w in p for w in SYNONYMS["target_screen"]):
        return {"type": "screen_off", "reply": "Гашу монитор, береги глаза, Сенеч."}
    if has("action_lock"):
        return {"type": "lock", "reply": "Блокирую дек, доступ закрыт."}
    if any(w in p for w in SYNONYMS["action_off"]) and any(w in p for w in ["пк", "комп", "пекарню", "систему", "тачку"]):
        sec = parse_timer_seconds(p) if any(x in p for x in ["через", "на"]) else 5
        return {"type": "shutdown", "seconds": sec, "reply": f"Выключаю станцию через {sec} секунд."}
    if has("action_reboot"):
        return {"type": "reboot", "seconds": 5, "reply": "Перезагружаю систему, скоро вернусь."}

    return None

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
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return []
    return []

def save_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-20:], f, ensure_ascii=False, indent=2)
    except Exception: pass

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
    ready = pyqtSignal(str, str, float, object)

    def __init__(self, user_query):
        super().__init__()
        self.user_query = user_query.strip()

    def run(self):
        global CHAT_HISTORY
        query = self.user_query
        ans = ""
        action_payload = None

        if not query:
            ans = "Сенеч, напиши хоть что-нибудь!"
        else:
            action_payload = parse_system_intent(query)
            if action_payload:
                ans = action_payload["reply"]
                CHAT_HISTORY.append((query, ans))
                save_history(CHAT_HISTORY)
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
                            "num_thread": 4, "num_ctx": 1024, "num_predict": 45,
                            "temperature": 0.8, "top_k": 30, "top_p": 0.85
                        }
                    }
                    resp = requests.post(OLLAMA_URL, json=payload, timeout=12)
                    if resp.status_code == 200:
                        raw = resp.json().get("message", {}).get("content", "")
                        ans = clean_text(raw) or "Сенеч, я здесь, слушаю тебя."
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
                "--pitch=+55Hz", "--rate=+12%",
                f"--text={voice_text}", f"--write-media={AUDIO_PATH}"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception: pass

        dur = max(2.0, len(ans) / 14.0)
        self.ready.emit(ans, AUDIO_PATH, dur, action_payload)

class FloatingDeckTrigger(QWidget):
    def __init__(self):
        super().__init__()
        self.hud_popup = None
        self.brain = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setContentsMargins(0, 0, 0, 0)
        self.main_vbox.setSpacing(8)
        self.main_vbox.setAlignment(Qt.AlignBottom | Qt.AlignRight)

        self.btn_toggle = QPushButton("♥ ПОДРУГА", self)
        self.btn_toggle.setFixedSize(140, 36)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(18, 16, 26, 0.95);
                color: #ff77a9;
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #ff77a9;
                border-radius: 18px;
            }
            QPushButton:hover { background: #ff77a9; color: #ffffff; }
        """)
        self.btn_toggle.clicked.connect(self.toggle_input)
        self.main_vbox.addWidget(self.btn_toggle, alignment=Qt.AlignRight)

        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Приказ или вопрос...")
        self.input_field.setFixedSize(260, 36)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(18, 16, 26, 0.95);
                color: #ffffff;
                font-size: 13px;
                border: 2px solid #ff77a9;
                border-radius: 18px;
                padding-left: 12px;
                padding-right: 12px;
            }
        """)
        self.input_field.returnPressed.connect(self.send_query)
        self.input_field.hide()
        self.main_vbox.addWidget(self.input_field, alignment=Qt.AlignRight)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 320, screen.height() - 110)

    def toggle_input(self):
        if self.input_field.isVisible():
            self.input_field.hide()
        else:
            self.input_field.show()
            self.input_field.setFocus()

    def send_query(self):
        txt = self.input_field.text().strip()
        if not txt: return
        self.input_field.clear()
        self.input_field.hide()

        if self.hud_popup: self.hud_popup.close()
        self.hud_popup = FloatingAiAnswer(txt)
        self.hud_popup.show()
        self.hud_popup.lower()

        self.brain = BrainThread(txt)
        self.brain.ready.connect(self.hud_popup.play_ai_answer)
        self.brain.start()

class FloatingAiAnswer(QWidget):
    def __init__(self, user_text):
        super().__init__()
        self.user_text = user_text
        self.alarm_proc = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.0)

        self.setFixedWidth(840)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 10, 20, 10)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignCenter)

        self.lbl_user = QLabel(f"« {self.user_text} »")
        self.lbl_user.setAlignment(Qt.AlignCenter)
        self.lbl_user.setWordWrap(True)
        self.lbl_user.setStyleSheet("color: #d8b4fe; font-size: 15px; font-style: italic;")
        self.layout.addWidget(self.lbl_user)

        self.av_lbl = QLabel()
        self.av_lbl.setAlignment(Qt.AlignCenter)
        img_path = find_anime_image()
        if img_path and os.path.exists(img_path):
            src_pix = QPixmap(img_path)
            size = 140
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
        self.layout.addWidget(self.av_lbl, alignment=Qt.AlignCenter)

        # Неоновый таймер / будильник
        self.timer_badge = QLabel("")
        self.timer_badge.setAlignment(Qt.AlignCenter)
        self.timer_badge.setStyleSheet("""
            color: #00ffff;
            font-family: monospace;
            font-size: 22px;
            font-weight: 900;
            background: rgba(0, 255, 255, 0.08);
            border: 1px solid rgba(0, 255, 255, 0.4);
            border-radius: 8px;
            padding: 4px 16px;
        """)
        self.timer_badge.hide()
        self.layout.addWidget(self.timer_badge, alignment=Qt.AlignCenter)

        self.lbl_sub = QLabel("слушаю тебя...")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("color: #fbcfe8; font-size: 17px; font-weight: 700; line-height: 1.4;")
        self.layout.addWidget(self.lbl_sub)

        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedSize(380, 6)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar { background: rgba(18, 16, 26, 0.8); border: 1px solid #ff77a9; border-radius: 3px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0077, stop:1 #00ffff); }
        """)
        self.prog_bar.hide()
        self.layout.addWidget(self.prog_bar, alignment=Qt.AlignCenter)

        # Кнопка отмены таймера
        self.btn_abort = QPushButton("Отмена")
        self.btn_abort.setFixedSize(110, 26)
        self.btn_abort.setStyleSheet("""
            QPushButton {
                background: rgba(35, 15, 25, 0.85);
                color: #ff5588;
                border: 1px solid #ff5588;
                font-size: 12px;
                font-weight: bold;
                border-radius: 13px;
            }
            QPushButton:hover { background: #ff5588; color: #ffffff; }
        """)
        self.btn_abort.clicked.connect(self.abort_command)
        self.btn_abort.hide()
        self.layout.addWidget(self.btn_abort, alignment=Qt.AlignCenter)

        # Кнопка ВЫКЛЮЧЕНИЯ БУДИЛЬНИКА
        self.btn_stop_alarm = QPushButton("⏹ ВЫКЛЮЧИТЬ СИГНАЛ")
        self.btn_stop_alarm.setFixedSize(240, 38)
        self.btn_stop_alarm.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0055, stop:1 #ff5500);
                color: #ffffff;
                font-size: 14px;
                font-weight: 900;
                font-family: monospace;
                border: 2px solid #ffffff;
                border-radius: 19px;
            }
            QPushButton:hover { background: #ffffff; color: #ff0055; }
        """)
        self.btn_stop_alarm.clicked.connect(self.stop_alarm_sound)
        self.btn_stop_alarm.hide()
        self.layout.addWidget(self.btn_stop_alarm, alignment=Qt.AlignCenter)

        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        self.base_y = (screen.height() // 2) + 20
        self.move((screen.width() - self.width()) // 2, self.base_y)

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(250)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.countdown_tick)
        self.remaining_sec = 0
        self.alarm_label_prefix = ""

    def play_ai_answer(self, ai_text, audio_path, duration, action_payload):
        self.full_ai_text = ai_text
        self.audio_path = audio_path
        self.duration = duration
        self.char_idx = 0
        self.lbl_sub.setStyleSheet("color: #38bdf8; font-size: 17px; font-weight: 700; line-height: 1.4;")

        if os.path.exists(self.audio_path):
            subprocess.Popen(["mpv", "--no-video", "--really-quiet", self.audio_path])

        total_chars = max(1, len(self.full_ai_text))
        char_interval = int(max(15, ((self.duration - 0.2) * 1000) / total_chars))

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self.typewriter_step)
        self.type_timer.start(char_interval)

        if action_payload:
            self.handle_action(action_payload)

    def handle_action(self, act):
        t = act["type"]
        if t == "stop_alarm_sound":
            subprocess.run(["pkill", "-f", "alarm_sound.wav"])
            self.stop_alarm_sound()
        elif t == "sleep_mode":
            subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
            QTimer.singleShot(2500, lambda: subprocess.run(["xset", "dpms", "force", "off"]))
        elif t == "screenshot":
            pic_path = os.path.expanduser(f"~/Изображения/deck_{int(time.time())}.png")
            os.makedirs(os.path.dirname(pic_path), exist_ok=True)
            subprocess.run(["scrot", pic_path], stderr=subprocess.DEVNULL)
        elif t == "media_next": subprocess.run(["playerctl", "next"])
        elif t == "media_prev": subprocess.run(["playerctl", "previous"])
        elif t == "media_pause": subprocess.run(["playerctl", "pause"])
        elif t == "media_play": subprocess.run(["playerctl", "play"])
        elif t == "set_vol": subprocess.run(["pamixer", "--set-volume", str(act["val"])])
        elif t == "vol_up": subprocess.run(["pamixer", "-i", "5"])
        elif t == "vol_down": subprocess.run(["pamixer", "-d", "5"])
        elif t == "screen_off":
            QTimer.singleShot(2500, lambda: subprocess.run(["xset", "dpms", "force", "off"]))
        elif t == "lock":
            QTimer.singleShot(1500, lambda: subprocess.run(["cinnamon-screensaver-command", "--lock"]))
        elif t == "alarm":
            self.start_timer_mode(act["seconds"], f"БУДИЛЬНИК: {act['target_str']}")
        elif t == "timer":
            self.start_timer_mode(act["seconds"], "ТАЙМЕР")
        elif t == "shutdown":
            self.start_timer_mode(act["seconds"], "ВЫКЛЮЧЕНИЕ", lambda: subprocess.run(["systemctl", "poweroff"]))
        elif t == "reboot":
            self.start_timer_mode(act["seconds"], "ПЕРЕЗАГРУЗКА", lambda: subprocess.run(["systemctl", "reboot"]))

    def start_timer_mode(self, seconds, prefix="ТАЙМЕР", callback=None):
        self.remaining_sec = seconds
        self.alarm_label_prefix = prefix
        self.pending_exec = callback
        self.prog_bar.setRange(0, seconds)
        self.prog_bar.setValue(seconds)
        self.prog_bar.show()
        self.btn_abort.show()

        mins = seconds // 60
        secs = seconds % 60
        self.timer_badge.setText(f"[ {self.alarm_label_prefix} | {mins:02d}:{secs:02d} ]")
        self.timer_badge.show()

        self.adjust_position()
        self.countdown_timer.start(1000)

    def countdown_tick(self):
        self.remaining_sec -= 1
        self.prog_bar.setValue(self.remaining_sec)
        m = self.remaining_sec // 60
        s = self.remaining_sec % 60
        self.timer_badge.setText(f"[ {self.alarm_label_prefix} | {m:02d}:{s:02d} ]")

        if self.remaining_sec <= 0:
            self.countdown_timer.stop()
            self.prog_bar.hide()
            self.btn_abort.hide()
            self.timer_badge.setText("[ СИГНАЛ ТРЕВОГИ / ПОДЪЕМ ]")
            self.timer_badge.setStyleSheet("""
                color: #ff0055;
                font-family: monospace;
                font-size: 22px;
                font-weight: 900;
                background: rgba(255, 0, 85, 0.15);
                border: 2px solid #ff0055;
                border-radius: 8px;
                padding: 4px 16px;
            """)
            
            # Бесконечный луп сирены
            if os.path.exists(ALARM_SOUND):
                self.alarm_proc = subprocess.Popen(["mpv", "--loop=inf", "--really-quiet", "--volume=100", ALARM_SOUND])
            
            self.btn_stop_alarm.show()
            self.lbl_sub.setText("Сенеч, время пришло! Нажми кнопку или скажи Хватит!")
            self.adjust_position()

            if getattr(self, "pending_exec", None):
                self.pending_exec()

    def stop_alarm_sound(self):
        if self.alarm_proc:
            self.alarm_proc.terminate()
            self.alarm_proc = None
        subprocess.run(["pkill", "-f", "alarm_sound.wav"])
        self.btn_stop_alarm.hide()
        self.timer_badge.hide()
        self.lbl_sub.setText("Сигнал выключен. Отличного дня, Сенеч!")
        QTimer.singleShot(2500, self.start_fade_out)

    def abort_command(self):
        self.countdown_timer.stop()
        if self.alarm_proc:
            self.alarm_proc.terminate()
            self.alarm_proc = None
        subprocess.run(["pkill", "-f", "alarm_sound.wav"])
        self.prog_bar.hide()
        self.btn_abort.hide()
        self.timer_badge.hide()
        self.lbl_sub.setText("Действие отменено.")
        QTimer.singleShot(2000, self.start_fade_out)

    def typewriter_step(self):
        if self.char_idx < len(self.full_ai_text):
            self.char_idx += 1
            self.lbl_sub.setText(self.full_ai_text[:self.char_idx] + "▌")
        else:
            self.type_timer.stop()
            self.lbl_sub.setText(self.full_ai_text)
            self.adjust_position()
            if not self.countdown_timer.isActive() and not self.alarm_proc:
                QTimer.singleShot(6000, self.start_fade_out)

    def adjust_position(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, self.base_y)

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
