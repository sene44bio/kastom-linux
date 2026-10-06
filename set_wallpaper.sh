#!/bin/bash
WALL_PATH="$HOME/kastom-linux/wallpapers/wallpaper_cyber_mint.png"
gsettings set org.cinnamon.desktop.background picture-uri "file://$WALL_PATH" 2>/dev/null
gsettings set org.gnome.desktop.background picture-uri "file://$WALL_PATH" 2>/dev/null
