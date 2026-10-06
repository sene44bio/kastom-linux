#!/bin/bash
# Сбрасываем старые процессы
killall conky 2>/dev/null
pkill -f cava_dock.py 2>/dev/null
pkill -f hud_center.py 2>/dev/null
pkill -f hud_weather.py 2>/dev/null
pkill -f desktop_hud_keeper.sh 2>/dev/null
pkill -f embedded_terminal.sh 2>/dev/null
pkill -f ai_greeting.py 2>/dev/null

sleep 1

# 1. Основные фоновые HUD-виджеты
nohup conky -c ~/.config/conky/conky.conf >/dev/null 2>&1 &
nohup python3 ~/.config/hud/hud_center.py >/dev/null 2>&1 &
nohup python3 ~/.config/hud/hud_weather.py >/dev/null 2>&1 &
nohup python3 ~/.config/cava/cava_dock.py ~/.config/cava/config_dock >/dev/null 2>&1 &
nohup ~/.config/hud/embedded_terminal.sh >/dev/null 2>&1 &
nohup ~/.config/hud/desktop_hud_keeper.sh >/dev/null 2>&1 &

# 2. Голосовое приветствие ИИ (ровно 1 запуск через 4 секунды)
(sleep 4 && python3 ~/.config/hud/ai_greeting.py) >/dev/null 2>&1 &

# 3. Фиксация слоев виджетов
(
    sleep 2
    for pid in $(pgrep -f "hud_center.py|hud_weather.py"); do
        for wid in $(wmctrl -lp | awk -v p="$pid" '$3 == p {print $1}'); do
            xprop -id "$wid" -f _NET_WM_WINDOW_TYPE 32a -set _NET_WM_WINDOW_TYPE _NET_WM_WINDOW_TYPE_DOCK 2>/dev/null
            wmctrl -i -r "$wid" -b add,skip_taskbar,skip_pager,sticky,below 2>/dev/null
        done
    done
) &
