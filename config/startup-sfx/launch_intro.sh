#!/bin/bash
# Фоновый звук инициализации
mpv --really-quiet ~/.config/startup-sfx/boot.wav &
# Запуск sci-fi интерфейса
~/Applications/edex-ui.AppImage &
APP_PID=$!
# Показ анимации и интерфейса 10 секунд
sleep 10
# Плавное закрытие и переход на рабочий стол
kill $APP_PID 2>/dev/null
