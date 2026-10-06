# Cyber Deck Startup Sequence & Welcome GUI

Кастомный двухэтапный экран запуска для Linux Mint в стиле Cyber-Deck / Sci-Fi.

---

## 🤖 AI Prompt Context (Промпт для ИИ в новых чатах)
> Если открываешь новый чат с ИИ, просто скопируй этот блок:
>
> **Окружение:** Linux Mint 22.3 x86_64, Cinnamon / Muffin (сессия X11), пользователь sene44.
> **Архитектура запуска:**
> 1. Автостарт через ~/.config/autostart/cyber_intro.desktop вызывает ~/.config/startup-sfx/launch_full_intro.sh.
> 2. Сначала запускается терминал ~/Applications/edex-ui.AppImage --no-sandbox на 12–13 секунд со звуком boot.wav.
> 3. Через wmctrl окно eDEX-UI держится поверх всех окон, пока в фоне подгружается PyQt5-окно.
> 4. eDEX-UI плавно глушится через kill/pkill, на экран выходит безрамочный GUI: /opt/cyber-welcome/welcome.py + index.html.
> 5. При нажатии «Войти» или Enter меняется document.title = "EXIT", и скрипт Python закрывает окно.
> **Зависимости:** python3-pyqt5, python3-pyqt5.qtwebengine, wmctrl, xdotool, mpv.

---

## 📂 Структура файлов

- config/startup-sfx/launch_full_intro.sh — главный скрипт: запуск eDEX-UI, таймеры, слои окон, звук и закрытие.
- config/startup-sfx/boot.wav — звуковой сигнал готовности системы.
- config/autostart/cyber_intro.desktop — автозапуск связки при входе в систему.
- opt/cyber-welcome/welcome.py — окно на PyQt5 WebEngine.
- opt/cyber-welcome/index.html — дизайн, часы, аватар и кнопка выхода.
- opt/cyber-welcome/run.sh — запасной скрипт ручного запуска.
- install.sh — автоустановщик на чистую систему.

---

## 🚀 Установка на чистой системе

```bash
git clone [https://github.com/sene44bio/kastom-linux.git](https://github.com/sene44bio/kastom-linux.git)
cd kastom-linux
chmod +x install.sh
./install.sh
