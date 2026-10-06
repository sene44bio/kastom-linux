#!/bin/bash
xprop -spy -root _NET_SHOWING_DESKTOP 2>/dev/null | while read -r line; do
    WID=$(wmctrl -l | grep "CYBER_HUD_TERM" | awk '{print $1}' | tail -n 1)
    if [ -n "$WID" ]; then
        xdotool windowmap "$WID" 2>/dev/null
        wmctrl -i -r "$WID" -b remove,hidden
        wmctrl -i -r "$WID" -b add,below,sticky
    fi
done
