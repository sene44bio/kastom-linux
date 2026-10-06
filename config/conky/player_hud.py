#!/usr/bin/env python3
import subprocess, sys

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except Exception:
        return ''

status = run_cmd('playerctl status')
if not status:
    print('${alignc}${color3}// CYBER_DECK READY //${color}\n${alignc}${color3}00:00 ──────────────────────── 00:00${color}\n${alignc}${color3}[⏮ PREV]    [▶ PLAY]    [⏭ NEXT]${color}')
    sys.exit(0)

title_artist = run_cmd("playerctl metadata --format '{{ artist }} — {{ title }}'")
if not title_artist or title_artist == ' — ':
    title_artist = run_cmd("playerctl metadata --format '{{ title }}'") or 'Unknown Track'
if len(title_artist) > 55:
    title_artist = title_artist[:52] + '...'

pos_str = run_cmd('playerctl position')
len_str = run_cmd('playerctl metadata mpris:length')

try:
    pos_sec = int(float(pos_str))
except Exception:
    pos_sec = 0

try:
    len_sec = int(int(len_str) / 1000000)
except Exception:
    len_sec = 0

def fmt_time(s):
    return f'{s // 60:02d}:{s % 60:02d}'

pos_fmt = fmt_time(pos_sec)
len_fmt = fmt_time(len_sec) if len_sec > 0 else '--:--'

bar_len = 28
if len_sec > 0:
    ratio = min(max(pos_sec / len_sec, 0.0), 1.0)
    idx = int(ratio * (bar_len - 1))
    scrubber = '${color1}' + ('━' * idx) + '${color}╸${color3}' + ('─' * (bar_len - 1 - idx)) + '${color}'
    pct = f'({int(ratio * 100)}%)'
else:
    scrubber = '${color3}' + ('─' * bar_len) + '${color}'
    pct = ''

icon = '${color1}▶ NOW PLAYING:${color}' if status == 'Playing' else '${color2}⏸ PAUSED:${color}'
controls = '${color2}[⏮ PREV]${color}    ${color1}[⏯ PLAY/PAUSE]${color}    ${color2}[⏭ NEXT]${color}'

print(f'${{alignc}}{icon} ${{font Monospace:size=10:bold}}{title_artist}${{font}}')
print(f'${{alignc}}${{font Monospace:size=9:bold}}${{color1}}{pos_fmt}${{color}}  {scrubber}  ${{color1}}{len_fmt}${{color}} ${{color2}}{pct}${{color}}${{font}}')
print(f'${{alignc}}${{font Monospace:size=9:bold}}{controls}${{font}}')
