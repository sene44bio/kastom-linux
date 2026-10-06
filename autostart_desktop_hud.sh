#!/bin/bash
# Сброс старых процессов
killall conky 2>/dev/null
pkill -f cava_dock.py 2>/dev/null
pkill -f hud_center.py 2>/dev/null
pkill -f hud_weather.py 2>/dev/null
pkill -f desktop_hud_keeper.sh 2>/dev/null
nohup python3 ~/.config/conky/player_hud.py >/dev/null 2>&1 &
pkill -f embedded_terminal.sh 2>/dev/null

sleep 1

# 1. Часы и системные блоки Conky
nohup conky -c ~/.config/conky/conky.conf >/dev/null 2>&1 &
nohup conky -c ~/.config/conky/conky_center.conf >/dev/null 2>&1 &

# 2. Погода
nohup python3 ~/.config/hud/hud_weather.py >/dev/null 2>&1 &

# 3. Аудиоспектр Cava
nohup python3 ~/.config/cava/cava_dock.py ~/.config/cava/config_dock >/dev/null 2>&1 &

# 4. Встроенный терминал
nohup python3 ~/.config/conky/player_hud.py >/dev/null 2>&1 &
nohup ~/.config/hud/embedded_terminal.sh >/dev/null 2>&1 &

# 5. Скрипт удержания слоев
nohup ~/.config/hud/desktop_hud_keeper.sh >/dev/null 2>&1 &
