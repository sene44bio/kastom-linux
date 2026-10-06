#!/bin/bash
set -e

echo "[+] Установка пакетов..."
sudo apt update
sudo apt install -y python3-pyqt5 python3-pyqt5.qtwebengine wmctrl xdotool mpv

echo "[+] Копирование файлов в систему..."
sudo mkdir -p /opt/cyber-welcome
sudo cp -r opt/cyber-welcome/* /opt/cyber-welcome/
sudo chown -R $USER:$USER /opt/cyber-welcome
chmod +x /opt/cyber-welcome/*.sh

mkdir -p ~/.config/startup-sfx
cp -r config/startup-sfx/* ~/.config/startup-sfx/
chmod +x ~/.config/startup-sfx/launch_full_intro.sh

mkdir -p ~/.config/autostart
cp config/autostart/cyber_intro.desktop ~/.config/autostart/

if [ -f ~/Applications/edex-ui.AppImage ]; then
    chmod +x ~/Applications/edex-ui.AppImage
else
    echo "[!] Положи edex-ui.AppImage в ~/Applications/"
fi

echo "[✔] Всё готово!"
