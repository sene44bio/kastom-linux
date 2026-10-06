#!/bin/bash
exec 200>/tmp/embedded_terminal.lock
flock -n 200 || exit 0

PROFILE=$(gsettings get org.gnome.Terminal.ProfilesList default | tr -d \')
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ scrollbar-policy 'never' 2>/dev/null
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ use-transparent-background true 2>/dev/null
gsettings set org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/ background-transparency-percent 100 2>/dev/null

WID=$(wmctrl -l | grep "CYBER_HUD_TERM" | awk '{print $1}' | tail -n 1)

if [ -z "$WID" ]; then
    gnome-terminal --title="CYBER_HUD_TERM" --geometry=80x24+0+260 -- bash -c "while true; do clear; exec bash; done"
    
    for i in {1..25}; do
        sleep 0.2
        WID=$(wmctrl -l | grep "CYBER_HUD_TERM" | awk '{print $1}' | tail -n 1)
        [ -n "$WID" ] && break
    done
fi

if [ -n "$WID" ]; then
    sleep 0.2
    xprop -id "$WID" -f _NET_WM_WINDOW_TYPE 32a -set _NET_WM_WINDOW_TYPE _NET_WM_WINDOW_TYPE_NORMAL
    xprop -id "$WID" -f _MOTIF_WM_HINTS 32c -set _MOTIF_WM_HINTS "0x2, 0x0, 0x0, 0x0, 0x0"
    wmctrl -i -r "$WID" -e 0,0,260,-1,-1
    wmctrl -i -r "$WID" -b remove,above,hidden
    wmctrl -i -r "$WID" -b add,skip_taskbar,skip_pager,sticky,below
    xprop -id "$WID" -remove _NET_WM_WINDOW_OPACITY 2>/dev/null
fi
