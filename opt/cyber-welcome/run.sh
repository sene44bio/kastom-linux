#!/bin/bash
export DISPLAY="${DISPLAY:-:0}"

# 1. Запуск eDEX-UI
/home/sene44/Applications/edex-ui.AppImage --no-sandbox &
EDEX_PID=$!

# 2. Таймер анимации ровно 13 секунд
sleep 13

# 3. Закрытие eDEX-UI
kill -9 $EDEX_PID 2>/dev/null
pkill -9 -f edex-ui 2>/dev/null

# 4. Запуск экрана входа
python3 /opt/cyber-welcome/welcome.py
