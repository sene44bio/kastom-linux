#!/bin/bash
exec 200>/tmp/embedded_terminal.lock
flock -n 200 || exit 0

PROFILE=$(gsettings get org.gnome.Terminal.ProfilesList default | tr -d \')
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ scrollbar-policy 'never' 2>/dev/null
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ use-transparent-background true 2>/dev/null
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ background-transparency-percent 100 2>/dev/null

WID=$(wmctrl -l | grep "CYBER_HUD_TERM" | awk '{print $1}' | tail -n 1)

if [ -z "$WID" ]; then
    gnome-terminal --title="CYBER_HUD_TERM" --geometry=80x24+0+260 -- bash -c "while true; do clear; exec bash; done" &
    
    for i in {1..30}; do
        sleep 0.15
        WID=$(wmctrl -l | grep "CYBER_HUD_TERM" | awk '{print $1}' | tail -n 1)
        [ -n "$WID" ] && break
    done
fi

if [ -n "$WID" ]; then
    sleep 0.2
    # Без рамок
    xprop -id "$WID" -f _MOTIF_WM_HINTS 32c -set _MOTIF_WM_HINTS "0x2, 0x0, 0x0, 0x0, 0x0"
    # Задаем тип DOCK, чтобы Cinnamon не сворачивал окно по Super+D
    xprop -id "$WID" -f _NET_WM_WINDOW_TYPE 32a -set _NET_WM_WINDOW_TYPE _NET_WM_WINDOW_TYPE_DOCK
    # Позиционирование и слои: закреплен на всех столах, без значка на панели, под обычными окнами
    xprop -id "$WID" -f _NET_WM_STATE 32a -set _NET_WM_STATE _NET_WM_STATE_STICKY,_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_BELOW
    wmctrl -i -r "$WID" -e 0,0,260,-1,-1
fi
