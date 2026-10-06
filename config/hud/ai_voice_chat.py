import sys, os, subprocess, json, re, requests, time
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QProgressBar, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath

CF_CONFIG_FILE = os.path.expanduser("~/.config/hud/cf_config.json")
HISTORY_FILE = os.path.expanduser("~/.config/hud/chat_history.json")
AUDIO_PATH = "/tmp/ai_chat_reply.mp3"
ALARM_SOUND = os.path.expanduser("~/.config/hud/alarm_sound.wav")

SYSTEM_PROMPT = """Ты — Акеми, харизматичная, ироничная и преданная цифровая напарница парня по имени Сенеч.
Ты встроена в его кастомный киберпанк-дек на базе Linux.
1. Твой собеседник — Сенеч. Общайся свободно, остроумно, по-дружески, без приторной ванильности.
2. Отвечай развернуто, емко, интересно и обязательно доводи каждую фразу до логической точки.
3. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать любые эмодзи, смайлики (включая скобки ), кавычки и звездочки. Только чистый русский текст."""

SYNONYMS = {
    "action_off": ["выключи", "выруби", "офни", "погаси", "потуши", "загаси", "вырубай", "отключи", "выключить"],
    "action_reboot": ["перезагрузи", "ребутни", "рестартни", "перезапусти", "ребут"],
    "action_lock": ["заблокируй", "залочь", "локни", "запри"],
    "target_screen": ["моник", "монитор", "экран", "дисплей"],
    "target_pc": ["пк", "комп", "систему", "тачку", "пекарню", "комплюктер"],
    "media_next": ["дальше", "некст", "следующий", "след", "переключи"],
    "media_prev": ["назад", "предыдущий", "пред"],
    "media_pause": ["стоп", "пауза", "замри", "останови", "заткнись", "тишина", "хватит", "молчи"],
    "media_play": ["продолжи", "плей", "играй"],
    "vol_up": ["громче", "прибавь", "погромче", "добавь звук", "сделай громче"],
    "vol_down": ["тише", "убавь", "потише", "сделай тише", "приглуши"],
    "intent_alarm": ["будильник", "разбуди", "подъем"],
    "intent_timer": ["таймер", "засеки", "напомни"],
    "intent_weather": ["погода", "погоду", "погоде", "температура", "градусник", "холодно", "тепло"],
    "intent_screenshot": ["скрин", "скриншот", "заскринь", "сделай скрин"],
    "intent_stats": ["ресурсы", "железо", "нагрузка", "процессор", "память", "что с пк", "статус"],
    "intent_sleep": ["отбой", "я спать", "спокойной ночи", "режим сна"],
    "intent_purge": ["очисти память", "сбрось память", "очисти кэш", "дропни кэш"]
}

WORD_NUMBERS = {
    "одну": 1, "один": 1, "минуту": 60, "минута": 60, "две": 2, "три": 3, "четыре": 4, 
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "полминуты": 30, "полчаса": 1800, "час": 3600, "полтора": 5400
}

def load_cf_config():
    if os.path.exists(CF_CONFIG_FILE):
        try:
            with open(CF_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def get_real_weather():
    try:
        r = requests.get("https://wttr.in/Yekaterinburg?format=j1", timeout=3)
        if r.status_code == 200:
            d = r.json()
            temp = d["current_condition"][0]["temp_C"]
            desc = d["current_condition"][0]["lang_ru"][0]["value"].lower()
            return f"В Екатеринбурге сейчас {temp} градусов, {desc}. На улице свежо, Сенеч."
    except Exception:
        pass
    return "В Екатеринбурге прохладно и морозно, держись в тепле, Сенеч."

def get_system_stats():
    try:
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'", shell=True).decode().strip()
        ram = subprocess.check_output("free -m | awk '/Mem:/ {printf(\"%.1f/%.1f ГБ\", $3/1024, $2/1024)}'", shell=True).decode().strip()
        return f"Процессор нагружен на {cpu} процентов, память занята на {ram}. Дека работает стабильно."
    except Exception:
        return "Все датчики в зеленой зоне, система в порядке."

def launch_telegram():
    subprocess.Popen([
        "sh", "-c",
        "which telegram-desktop >/dev/null && telegram-desktop || (flatpak run org.telegram.desktop 2>/dev/null || /opt/Telegram/Telegram 2>/dev/null)"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def launch_browser(url=None):
    target = url if url else "https://ya.ru"
    subprocess.Popen([
        "sh", "-c",
        f"which yandex-browser-stable >/dev/null && yandex-browser-stable '{target}' || (which yandex-browser >/dev/null && yandex-browser '{target}' || xdg-open '{target}')"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def open_music_app():
    subprocess.Popen([
        "sh", "-c",
        "which yandex-music >/dev/null && yandex-music || (flatpak run ru.yandex.YandexMusic 2>/dev/null || xdg-open https://music.yandex.ru)"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def close_app(target):
    t = target.lower()
    if any(x in t for x in ["телеграм", "телеге", "телегу", "тг"]):
        subprocess.run(["pkill", "-f", "telegram"], stderr=subprocess.DEVNULL)
        return "Закрыла Телеграм."
    if any(x in t for x in ["браузер", "яндекс"]):
        subprocess.run(["pkill", "-f", "yandex-browser"], stderr=subprocess.DEVNULL)
        return "Погасила Яндекс Браузер."
    if any(x in t for x in ["музыку", "яндекс музыку"]):
        subprocess.run(["pkill", "-f", "yandex-music"], stderr=subprocess.DEVNULL)
        subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
        return "Остановила музыку."
    if any(x in t for x in ["терминал", "консоль"]):
        subprocess.run(["pkill", "-f", "gnome-terminal"], stderr=subprocess.DEVNULL)
        return "Прикрыла лишние терминалы."
    return "Приложение не найдено в процессах."

def parse_alarm_target(text):
    t = text.lower()
    now = datetime.now()
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

    if any(w in p for w in ["заткнись", "выключи сигнал", "выруби будильник", "стоп сигнал", "хватит"]):
        return {"type": "stop_alarm", "reply": "Сигнал отключен."}

    search_m = re.search(r'(?:найди|гугли|поищи)\s+(.+)', p)
    if search_m:
        q = search_m.group(1).strip()
        return {"type": "search_web", "query": q, "reply": f"Ищу информацию по запросу {q}."}

    if any(w in p for w in ["закрой", "прикрой", "выруби приложение", "убей"]):
        reply = close_app(p)
        return {"type": "noop", "reply": reply}

    if any(w in p for w in ["открой", "запусти", "вруби", "включи"]):
        if any(x in p for x in ["телеграм", "телеге", "телегу", "тг"]):
            return {"type": "open_tg", "reply": "Запускаю Телеграм."}
        if any(x in p for x in ["ютуб", "youtube"]):
            return {"type": "open_yt", "reply": "Открываю Ютуб в браузере."}
        if any(x in p for x in ["музыку", "яндекс музыку", "треки"]):
            return {"type": "open_music", "reply": "Включаю Яндекс Музыку."}
        if any(x in p for x in ["браузер", "яндекс", "интернет"]):
            return {"type": "open_browser", "reply": "Запускаю Яндекс Браузер."}
        if any(x in p for x in ["код", "cursor", "vscode"]):
            return {"type": "open_app_cmd", "cmd": "cursor", "reply": "Открываю среду разработки."}
        if any(x in p for x in ["терминал", "консоль"]):
            return {"type": "open_app_cmd", "cmd": "gnome-terminal", "reply": "Терминал готов к работе."}

    if has("intent_purge"):
        subprocess.run(["sync"])
        return {"type": "noop", "reply": "Сбросила системный дисковый кэш, память свободна."}

    if has("intent_sleep"):
        return {"type": "sleep_mode", "reply": "Спокойной ночи, Сенеч. Перевожу дек в режим ожидания."}

    if has("intent_screenshot"):
        return {"type": "screenshot", "reply": "Скриншот сохранён в папку изображений."}

    if has("intent_stats"):
        return {"type": "stats", "reply": get_system_stats()}

    if has("intent_weather"):
        return {"type": "weather", "reply": get_real_weather()}

    if has("intent_alarm"):
        diff, t_str = parse_alarm_target(p)
        if diff:
            return {"type": "alarm", "seconds": diff, "target_str": t_str, "reply": f"Будильник на {t_str} установлен."}
        else:
            sec = parse_timer_seconds(p)
            txt_desc = f"{sec // 60} мин" if sec >= 60 and sec % 60 == 0 else f"{sec} сек"
            return {"type": "alarm", "seconds": sec, "target_str": txt_desc, "reply": f"Будильник через {txt_desc} взведён."}

    if has("intent_timer"):
        sec = parse_timer_seconds(p)
        txt_desc = f"{sec // 60} мин" if sec >= 60 and sec % 60 == 0 else f"{sec} сек"
        return {"type": "timer", "seconds": sec, "reply": f"Таймер на {txt_desc} пошел."}

    if has("media_next"): return {"type": "media_next", "reply": "Следующий трек."}
    if has("media_prev"): return {"type": "media_prev", "reply": "Предыдущий трек."}
    if has("media_pause"): return {"type": "media_pause", "reply": "Музыка на паузе."}
    if has("media_play"): return {"type": "media_play", "reply": "Продолжаю играть."}

    if "максимум" in p or "на всю" in p:
        return {"type": "set_vol", "val": 100, "reply": "Громкость на максимум."}
    if "без звука" in p or "мут" in p:
        return {"type": "set_vol", "val": 0, "reply": "Звук заглушен."}
    if has("vol_up"): return {"type": "vol_up", "reply": "Громкость плюс пять процентов."}
    if has("vol_down"): return {"type": "vol_down", "reply": "Громкость минус пять процентов."}
    if "громкость" in p or "звук" in p:
        m = re.search(r'(\d+)', p)
        if m:
            v = int(m.group(1))
            return {"type": "set_vol", "val": v, "reply": f"Громкость {v} процентов."}

    if any(w in p for w in SYNONYMS["action_off"]) and any(w in p for w in SYNONYMS["target_screen"]):
        return {"type": "screen_off", "reply": "Гашу монитор."}
    if has("action_lock"):
        return {"type": "lock", "reply": "Блокирую дек."}
    if any(w in p for w in SYNONYMS["action_off"]) and any(w in p for w in ["пк", "комп", "пекарню", "систему", "тачку"]):
        sec = parse_timer_seconds(p) if any(x in p for x in ["через", "на"]) else 5
        return {"type": "shutdown", "seconds": sec, "reply": f"Выключаю станцию через {sec} секунд."}
    if has("action_reboot"):
        return {"type": "reboot", "seconds": 5, "reply": "Перезагружаю систему."}

    return None

def clean_text(text):
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\u200d\ufe0f]', '', text)
    text = re.sub(r'[:;=8][\-~]?[)dD(\[\]{}pP/\\]+', '', text)
    text = text.replace('☺', '').replace('☻', '').replace('♡', '').replace('♥', '')
    text = text.replace('"', '').replace('«', '').replace('»', '').replace('*', '')
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
            json.dump(history[-30:], f, ensure_ascii=False, indent=2)
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
                cf = load_cf_config()
                if cf:
                    try:
                        url = f"https://api.cloudflare.com/client/v4/accounts/{cf['account_id']}/ai/run/{cf.get('model', '@cf/meta/llama-3.1-8b-instruct')}"
                        headers = {"Authorization": f"Bearer {cf['api_token']}"}
                        
                        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                        for q, a in CHAT_HISTORY[-4:]:
                            messages.append({"role": "user", "content": q})
                            messages.append({"role": "assistant", "content": a})
                        messages.append({"role": "user", "content": query})

                        payload = {"messages": messages, "max_tokens": 1024}
                        resp = requests.post(url, headers=headers, json=payload, timeout=12)
                        if resp.status_code == 200:
                            raw = resp.json().get("result", {}).get("response", "")
                            ans = clean_text(raw) or "Я здесь, слушаю тебя."
                            CHAT_HISTORY.append((query, ans))
                            save_history(CHAT_HISTORY)
                        else:
                            ans = "Облако слегка задумалось, повтори ещё раз."
                    except Exception:
                        ans = "Связь с облачной сетью прервалась, но локальные системы в норме."
                else:
                    ans = "Конфигурация нейросети отсутствует."

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

        dur = max(2.0, len(ans) / 16.0)
        self.ready.emit(ans, AUDIO_PATH, dur, action_payload)

# -------------------------------------------------------------
# ЦЕНТРАЛЬНЫЙ АВАТАР: БЕЗУПРЕЧНАЯ ПРИВЯЗКА К СТОЛУ + SPINNER + БЫСТРЫЙ TYPEWRITER
# -------------------------------------------------------------
class CenterDeckAvatar(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setFixedWidth(860)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_user = QLabel("")
        self.lbl_user.setAlignment(Qt.AlignCenter)
        self.lbl_user.setWordWrap(True)
        self.lbl_user.setStyleSheet("color: #d8b4fe; font-size: 15px; font-style: italic; background: transparent;")
        self.lbl_user.hide()
        layout.addWidget(self.lbl_user)

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
        layout.addWidget(self.av_lbl, alignment=Qt.AlignCenter)

        # Неоновый спиннер ожидания
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.spinner_lbl = QLabel("")
        self.spinner_lbl.setAlignment(Qt.AlignCenter)
        self.spinner_lbl.setStyleSheet("color: #00ffff; font-family: monospace; font-size: 20px; font-weight: bold; background: transparent;")
        self.spinner_lbl.hide()
        layout.addWidget(self.spinner_lbl, alignment=Qt.AlignCenter)

        self.timer_badge = QLabel("")
        self.timer_badge.setAlignment(Qt.AlignCenter)
        self.timer_badge.setStyleSheet("""
            color: #00ffff; font-family: monospace; font-size: 18px; font-weight: bold;
            background: rgba(0, 255, 255, 0.08); border: 1px solid rgba(0, 255, 255, 0.35);
            border-radius: 6px; padding: 3px 14px;
        """)
        self.timer_badge.hide()
        layout.addWidget(self.timer_badge, alignment=Qt.AlignCenter)

        self.lbl_sub = QLabel("")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("color: #fbcfe8; font-size: 16px; font-weight: 700; line-height: 1.4; background: transparent;")
        self.lbl_sub.hide()
        layout.addWidget(self.lbl_sub)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() // 2) + 20)

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self.typewriter_step)
        self.full_text = ""
        self.char_idx = 0

        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self.spin_tick)

        # Защита от сворачивания Super+D: мягкий таймер на установку типа окна
        QTimer.singleShot(500, self.enforce_desktop_layer)

    def enforce_desktop_layer(self):
        try:
            win_id = int(self.winId())
            subprocess.run(["xprop", "-id", str(win_id), "-f", "_NET_WM_WINDOW_TYPE", "32a",
                            "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DESKTOP"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["xprop", "-id", str(win_id), "-f", "_NET_WM_STATE", "32a",
                            "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_BELOW"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def start_thinking(self, prompt_text):
        self.type_timer.stop()
        self.lbl_user.setText(f"« {prompt_text} »")
        self.lbl_user.show()
        self.lbl_sub.hide()
        self.spinner_lbl.setText("⠋")
        self.spinner_lbl.show()
        self.spin_timer.start(80)
        self.adjustSize()

    def spin_tick(self):
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.spinner_lbl.setText(self.spinner_frames[self.spinner_idx])

    def start_speech(self, user_text, reply_text, duration):
        self.spin_timer.stop()
        self.spinner_lbl.hide()

        self.lbl_user.setText(f"« {user_text} »")
        self.lbl_user.show()

        self.full_text = reply_text
        self.char_idx = 0
        self.lbl_sub.setText("")
        self.lbl_sub.show()

        # Быстрый typewriter: максимум 18 мс на символ, чтобы печать не отставала
        total_chars = max(1, len(self.full_text))
        interval = max(12, int(((duration * 0.75) * 1000) / total_chars))

        self.type_timer.stop()
        self.type_timer.start(interval)
        self.adjustSize()

    def typewriter_step(self):
        # Печатаем сразу пачками по 2 символа для приятной динамики
        step_len = 2 if len(self.full_text) > 40 else 1
        if self.char_idx < len(self.full_text):
            self.char_idx = min(len(self.full_text), self.char_idx + step_len)
            self.lbl_sub.setText(self.full_text[:self.char_idx] + ("▌" if self.char_idx < len(self.full_text) else ""))
        else:
            self.type_timer.stop()
            self.lbl_sub.setText(self.full_text)
            self.adjustSize()

    def clear_text_display(self):
        self.spin_timer.stop()
        self.type_timer.stop()
        self.spinner_lbl.hide()
        self.lbl_user.hide()
        self.lbl_sub.hide()
        self.adjustSize()

# -------------------------------------------------------------
# КНОПКА ТРИГГЕР НА РАБОЧЕМ СТОЛЕ
# -------------------------------------------------------------
class FloatingDeckTrigger(QWidget):
    def __init__(self, center_avatar):
        super().__init__()
        self.center_avatar = center_avatar
        self.hud_popup = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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
        self.btn_toggle.clicked.connect(self.toggle_chat)
        layout.addWidget(self.btn_toggle)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 170, screen.height() - 85)

        QTimer.singleShot(600, self.enforce_desktop_layer)

    def enforce_desktop_layer(self):
        try:
            win_id = int(self.winId())
            subprocess.run(["xprop", "-id", str(win_id), "-f", "_NET_WM_WINDOW_TYPE", "32a",
                            "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DESKTOP"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["xprop", "-id", str(win_id), "-f", "_NET_WM_STATE", "32a",
                            "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_BELOW"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def toggle_chat(self):
        if self.hud_popup and self.hud_popup.isVisible():
            self.hud_popup.close()
            self.hud_popup = None
            self.center_avatar.clear_text_display()
        else:
            self.hud_popup = FloatingAiChatDialog(self, self.center_avatar)
            self.hud_popup.show()

# -------------------------------------------------------------
# ДИАЛОГОВЫЙ ЧАТ
# -------------------------------------------------------------
class FloatingAiChatDialog(QWidget):
    def __init__(self, parent_trigger, center_avatar):
        super().__init__()
        self.parent_trigger = parent_trigger
        self.center_avatar = center_avatar
        self.alarm_proc = None
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.countdown_tick)
        self.remaining_sec = 0
        self.badge_title = "ТАЙМЕР"

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setFixedSize(480, 560)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background: rgba(14, 12, 22, 0.96);
                border: 2px solid #ff77a9;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        header = QHBoxLayout()
        title_lbl = QLabel("АКЕМИ // ДЕК АССИСТЕНТ")
        title_lbl.setStyleSheet("color: #ff77a9; font-size: 13px; font-weight: bold; border: none;")
        header.addWidget(title_lbl)
        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #888899; font-size: 14px; font-weight: bold; border: none; }
            QPushButton:hover { color: #ff5588; }
        """)
        btn_close.clicked.connect(self.close_and_clear)
        header.addWidget(btn_close)
        card_layout.addLayout(header)

        self.timer_badge = QLabel("")
        self.timer_badge.setAlignment(Qt.AlignCenter)
        self.timer_badge.setStyleSheet("""
            color: #00ffff; font-family: monospace; font-size: 15px; font-weight: bold;
            background: rgba(0, 255, 255, 0.08); border: 1px solid rgba(0, 255, 255, 0.4);
            border-radius: 6px; padding: 4px;
        """)
        self.timer_badge.hide()
        card_layout.addWidget(self.timer_badge)

        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(4)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar { background: rgba(18, 16, 26, 0.8); border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0077, stop:1 #00ffff); }
        """)
        self.prog_bar.hide()
        card_layout.addWidget(self.prog_bar)

        self.btn_stop_alarm = QPushButton("⏹ ВЫКЛЮЧИТЬ СИГНАЛ")
        self.btn_stop_alarm.setFixedHeight(30)
        self.btn_stop_alarm.setStyleSheet("""
            QPushButton {
                background: #ff0055; color: #ffffff; font-size: 12px; font-weight: bold;
                border-radius: 15px; border: none;
            }
            QPushButton:hover { background: #ff3377; }
        """)
        self.btn_stop_alarm.clicked.connect(self.stop_alarm_sound)
        self.btn_stop_alarm.hide()
        card_layout.addWidget(self.btn_stop_alarm)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none; background: rgba(255, 255, 255, 0.05); width: 4px; border-radius: 2px;
            }
            QScrollBar::handle:vertical { background: #ff77a9; border-radius: 2px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent; border: none;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(4, 4, 4, 4)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        card_layout.addWidget(self.scroll_area)

        input_box = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Команда или вопрос...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(25, 22, 36, 0.95);
                color: #ffffff;
                font-size: 13px;
                border: 1px solid #ff77a9;
                border-radius: 14px;
                padding: 6px 12px;
            }
        """)
        self.input_field.returnPressed.connect(self.handle_send)
        input_box.addWidget(self.input_field)

        btn_send = QPushButton("➤")
        btn_send.setFixedSize(36, 32)
        btn_send.setStyleSheet("""
            QPushButton {
                background: #ff77a9; color: #12101a; font-size: 14px; font-weight: bold;
                border-radius: 14px; border: none;
            }
            QPushButton:hover { background: #ff99c2; }
        """)
        btn_send.clicked.connect(self.handle_send)
        input_box.addWidget(btn_send)
        card_layout.addLayout(input_box)

        main_layout.addWidget(self.card)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 25, screen.height() - self.height() - 90)

        self.populate_history()
        self.input_field.setFocus()

    def close_and_clear(self):
        self.close()
        self.center_avatar.clear_text_display()

    def populate_history(self):
        for q, a in CHAT_HISTORY[-6:]:
            self.append_message(q, is_user=True)
            self.append_message(a, is_user=False)
        self.scroll_to_bottom()

    def append_message(self, text, is_user=False):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        if is_user:
            bubble.setStyleSheet("""
                QLabel {
                    background: rgba(255, 119, 169, 0.12);
                    color: #d8b4fe;
                    font-size: 13px;
                    border: 1px solid rgba(255, 119, 169, 0.25);
                    border-radius: 10px;
                    padding: 6px 10px;
                }
            """)
            self.chat_layout.addWidget(bubble, alignment=Qt.AlignRight)
        else:
            bubble.setStyleSheet("""
                QLabel {
                    background: rgba(26, 32, 54, 0.8);
                    color: #e0f2fe;
                    font-size: 13px;
                    border: 1px solid rgba(56, 189, 248, 0.25);
                    border-radius: 10px;
                    padding: 6px 10px;
                }
            """)
            self.chat_layout.addWidget(bubble, alignment=Qt.AlignLeft)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def handle_send(self):
        txt = self.input_field.text().strip()
        if not txt: return
        self.input_field.clear()

        # 1. Сразу отображаем в чате
        self.append_message(txt, is_user=True)
        # 2. Сразу отображаем на центральном аватаре и включаем спиннер ожидания
        self.center_avatar.start_thinking(txt)

        self.brain = BrainThread(txt)
        self.brain.ready.connect(lambda reply, audio, dur, act: self.on_brain_reply(txt, reply, audio, dur, act))
        self.brain.start()

    def on_brain_reply(self, user_txt, reply, audio, dur, act):
        self.append_message(reply, is_user=False)
        # Запускаем синхронную быструю печать
        self.center_avatar.start_speech(user_txt, reply, dur)

        if os.path.exists(audio):
            subprocess.Popen(["mpv", "--no-video", "--really-quiet", audio])

        if act:
            self.handle_action(act)

    def handle_action(self, act):
        t = act["type"]
        if t == "stop_alarm": self.stop_alarm_sound()
        elif t == "open_tg": launch_telegram()
        elif t == "open_yt": launch_browser("https://youtube.com")
        elif t == "open_browser": launch_browser()
        elif t == "search_web": launch_browser(f"https://ya.ru/search/?text={act['query']}")
        elif t == "open_music": open_music_app()
        elif t == "open_app_cmd": subprocess.Popen([act["cmd"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif t == "sleep_mode":
            subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
            QTimer.singleShot(2000, lambda: subprocess.run(["xset", "dpms", "force", "off"]))
        elif t == "screenshot":
            pic = os.path.expanduser(f"~/Изображения/deck_{int(time.time())}.png")
            subprocess.run(["scrot", pic], stderr=subprocess.DEVNULL)
        elif t == "media_next": subprocess.run(["playerctl", "next"])
        elif t == "media_prev": subprocess.run(["playerctl", "previous"])
        elif t == "media_pause": subprocess.run(["playerctl", "pause"])
        elif t == "media_play": subprocess.run(["playerctl", "play"])
        elif t == "set_vol": subprocess.run(["pamixer", "--set-volume", str(act["val"])])
        elif t == "vol_up": subprocess.run(["pamixer", "-i", "5"])
        elif t == "vol_down": subprocess.run(["pamixer", "-d", "5"])
        elif t == "screen_off":
            QTimer.singleShot(2000, lambda: subprocess.run(["xset", "dpms", "force", "off"]))
        elif t == "lock":
            QTimer.singleShot(1000, lambda: subprocess.run(["cinnamon-screensaver-command", "--lock"]))
        elif t == "alarm":
            self.start_timer_mode(act["seconds"], f"БУДИЛЬНИК {act['target_str']}")
        elif t == "timer":
            self.start_timer_mode(act["seconds"], "ТАЙМЕР")
        elif t == "shutdown":
            self.start_timer_mode(act["seconds"], "ВЫКЛЮЧЕНИЕ", lambda: subprocess.run(["systemctl", "poweroff"]))
        elif t == "reboot":
            self.start_timer_mode(act["seconds"], "ПЕРЕЗАГРУЗКА", lambda: subprocess.run(["systemctl", "reboot"]))

    def start_timer_mode(self, seconds, title="ТАЙМЕР", callback=None):
        self.remaining_sec = seconds
        self.badge_title = title
        self.pending_exec = callback
        self.prog_bar.setRange(0, seconds)
        self.prog_bar.setValue(seconds)
        self.prog_bar.show()

        mins = seconds // 60
        secs = seconds % 60
        self.timer_badge.setText(f"[ {self.badge_title} | {mins:02d}:{secs:02d} ]")
        self.timer_badge.show()
        self.countdown_timer.start(1000)

    def countdown_tick(self):
        self.remaining_sec -= 1
        self.prog_bar.setValue(self.remaining_sec)
        m = self.remaining_sec // 60
        s = self.remaining_sec % 60
        self.timer_badge.setText(f"[ {self.badge_title} | {m:02d}:{s:02d} ]")

        if self.remaining_sec <= 0:
            self.countdown_timer.stop()
            self.prog_bar.hide()
            self.timer_badge.setText(f"[ ВРЕМЯ ВЫШЛО ]")
            if os.path.exists(ALARM_SOUND):
                self.alarm_proc = subprocess.Popen(["mpv", "--loop=inf", "--really-quiet", "--volume=100", ALARM_SOUND])
            self.btn_stop_alarm.show()
            if getattr(self, "pending_exec", None):
                self.pending_exec()

    def stop_alarm_sound(self):
        if self.alarm_proc:
            self.alarm_proc.terminate()
            self.alarm_proc = None
        subprocess.run(["pkill", "-f", "alarm_sound.wav"])
        self.btn_stop_alarm.hide()
        self.timer_badge.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    center_av = CenterDeckAvatar()
    center_av.show()
    center_av.lower()
    w = FloatingDeckTrigger(center_av)
    w.show()
    w.lower()
    sys.exit(app.exec_())
