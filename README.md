```bash
cat << 'EOF' > ~/kastom-linux/README.md
# Kastom Linux — Cyberpunk Edition (Linux Mint / Cinnamon)

Полноценная кастомная среда рабочего стола в стилистике Cyberpunk / Sci-Fi Deck, построенная поверх Linux Mint (Cinnamon / Muffin X11). 

Конфигурация включает кинематографичную последовательность запуска системы, комплекс прозрачных легковесных виджетов рабочего стола (HUD), аппаратный аудио-визуализатор, встроенный интерактивный терминал и фоновые демоны управления слоями окон X11.

---

## ⚡ Оглавление
1. [Архитектура и компоненты](#-архитектура-и-компоненты)
2. [Структура репозитория](#-структура-репозитория)
3. [Принцип работы виджетов и окон](#-принцип-работы-виджетов-и-окон)
4. [Зависимости](#-зависимости)
5. [Развёртывание и установка на чистую систему](#-развёртывание-и-установка-на-чистую-систему)
6. [Управление и автозапуск](#-управление-и-автозапуск)

---

## 🖥 Архитектура и компоненты

### 1. Кинематографичный запуск (Startup Sequence)
* **eDEX-UI Boot Screen:** Запуск эмулятора терминала с визуализацией загрузки периферии и звуковыми эффектами (SFX).
* **Welcome Screen (`opt/cyber-welcome/`):** Графический экран входа оператора на базе Python/PyQt.
* **Защита от циклов (Lockfile):** Скрипт `launch_full_intro.sh` использует механизм `/tmp/cyber_intro.lock`. Это исключает повторный запуск интро при обычном перезапуске оболочки или рестарте сессии.

### 2. Центральный дек (`hud_center.py`)
* Крупные неоновые часы, текущая дата и системный индикатор готовности (`// CYBER_DECK READY //`).
* Встроенный медиаплеер с управлением треками (Play/Pause, Next, Prev), таймингами и интерактивной полосой прогресса.
* Работает через интерфейс MPRIS / D-Bus, подхватывая управление системными плеерами и браузером.

### 3. Метео-телеметрия (`hud_weather.py`)
* Виджет погоды с пиксельным маскотом и карточками почасового прогноза на 5 часов вперед.
* **Сетевой движок:** Переведен на прямой опрос `wttr.in/Yekaterinburg?format=j1` без внешних тяжелых зависимостей. Данные запрашиваются через неблокирующий поток `QThread` каждые 15 минут с защитой по таймауту (6 секунд), исключая зависание интерфейса.

### 4. Системный монитор справа (Conky)
* Панель телеметрии оператора (`OPERATOR: SENE44 / STATUS: ACTIVE [ONLINE]`).
* Мониторинг загрузки процессора по ядрам (Intel Core i5) в реальном времени с прогресс-барами.
* Показатели использования оперативной памяти (RAM), занятого дискового пространства (SSD) и сетевого трафика (DL/UL).

### 5. Аудио-визуализатор снизу (Cava Dock)
* Спектральный анализатор частот звука, закрепленный над нижней панелью задач.
* Построен на связке Cava + кастомный Python-рендерер без рамок и теней.

### 6. Встроенный рабочий терминал (`embedded_terminal.sh`)
* Полноценный рабочий терминал `gnome-terminal`, прозрачно интегрированный в фон рабочего стола с запуском Neofetch.
* **Фиксация при Super+D:** Окно терминала переведено в X11-атомы `_NET_WM_WINDOW_TYPE_DOCK` и `_NET_WM_STATE_BELOW`, что предотвращает его сворачивание при сочетании клавиш **Super + D** (режим «Показать рабочий стол»), сохраняя полную интерактивность и возможность ввода команд.

---

## 📁 Структура репозитория

```text
kastom-linux/
├── config/
│   ├── autostart/                  # .desktop файлы автозапуска окружения
│   │   ├── ai_deck.desktop
│   │   ├── conky.desktop
│   │   ├── cyber_deck_hud.desktop
│   │   └── cyber_intro.desktop
│   ├── autostart_desktop_hud.sh    # Главный скрипт инициализации HUD-слоев
│   ├── cava/                       # Конфиги спектрального аудио-анализатора
│   │   ├── cava_dock.py
│   │   └── config_dock
│   ├── conky/                      # Конфиг системного монитора
│   │   └── conky.conf
│   ├── hud/                        # Исполняемые скрипты и ассеты виджетов
│   │   ├── corgi_pixel.png         # Ассет маскота для метео-виджета
│   │   ├── desktop_hud_keeper.sh   # Демон удержания терминала в слое стола
│   │   ├── embedded_terminal.sh    # Запуск и фиксация терминала на столе
│   │   ├── hud_center.py           # Часы и медиаплеер
│   │   └── hud_weather.py          # Виджет погоды
│   └── startup-sfx/                # Логика и звуки интро
│       └── launch_full_intro.sh
├── opt/
│   └── cyber-welcome/              # GUI-приветствие
│       ├── welcome.py
│       └── index.html
├── wallpapers/                     # Кастомные киберпанк-обои
│   └── wallpaper_cyber_mint.png
├── set_wallpaper.sh                # Применение обоев в Cinnamon/GNOME
└── README.md                       # Документация проекта

```

---

## 🛠 Зависимости

Для корректной работы всех компонентов в системе должны быть установлены:

```bash
sudo apt update && sudo apt install -y \
    python3 python3-pyqt5 python3-pip \
    conky-all cava curl wmctrl xdotool x11-utils jq

```

---

## 🚀 Развёртывание и установка на чистую систему

1. **Клонирование репозитория:**
```bash
git clone [https://github.com/sene44bio/kastom-linux.git](https://github.com/sene44bio/kastom-linux.git) ~/kastom-linux

```


2. **Копирование конфигураций в систему:**
```bash
mkdir -p ~/.config/hud ~/.config/conky ~/.config/cava ~/.config/autostart
cp -r ~/kastom-linux/config/hud/* ~/.config/hud/
cp -r ~/kastom-linux/config/conky/* ~/.config/conky/
cp -r ~/kastom-linux/config/cava/* ~/.config/cava/
cp ~/kastom-linux/config/autostart_desktop_hud.sh ~/.config/
cp ~/kastom-linux/config/autostart/*.desktop ~/.config/autostart/
chmod +x ~/.config/hud/*.sh ~/.config/autostart_desktop_hud.sh

```


3. **Установка обоев:**
```bash
~/kastom-linux/set_wallpaper.sh

```


4. **Запуск рабочего стола без перезагрузки:**
```bash
~/.config/autostart_desktop_hud.sh

```



---

## ⚙️ Управление и фоновые процессы

* **Перезапуск всех HUD-виджетов:**
```bash
~/.config/autostart_desktop_hud.sh

```


* **Остановка всех виджетов:**
```bash
pkill -f hud_center.py
pkill -f hud_weather.py
pkill -f cava_dock.py
pkill -f conky
pkill -f embedded_terminal.sh
pkill -f desktop_hud_keeper.sh

```



EOF

cd ~/kastom-linux
git add README.md
git commit -m "docs: write comprehensive cyberpunk deck documentation and deployment guide"
git push origin main

```

Теперь на главной странице твоего репозитория будет лежать чистое техническое описание архитектуры, компонентов и развёртывания.

```
