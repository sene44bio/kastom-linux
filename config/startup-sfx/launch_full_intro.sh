#!/bin/bash
export DISPLAY=:0

# 1. Запуск eDEX-UI
/home/sene44/Applications/edex-ui.AppImage --no-sandbox &
EDEX_PID=$!

# 2. Ждем 4 секунды, пока eDEX-UI создаст окно
sleep 4

# 3. Намертво вешаем на eDEX-UI статус "Всегда сверху" (слой TOP)
wmctrl -r :ACTIVE: -b add,above 2>/dev/null
wmctrl -r "edex" -b add,above 2>/dev/null

# 4. Запускаем Welcome — теперь он физически не сможет перекрыть eDEX-UI
python3 /opt/cyber-welcome/welcome.py &
HUD_PID=$!

# 5. Возвращаем фокус на терминал и докручиваем таймер (всего 12 сек)
sleep 0.2
wmctrl -a "edex" 2>/dev/null
sleep 7.8

# 6. Звуковой сигнал и завершение eDEX-UI
mpv --really-quiet /home/sene44/.config/startup-sfx/boot.wav &
kill $EDEX_PID 2>/dev/null
pkill -f edex-ui 2>/dev/null

# 7. Активируем Welcome для управления кнопками и кликом
xdotool search --class "python3" windowactivate 2>/dev/null
wait $HUD_PID 2>/dev/null
