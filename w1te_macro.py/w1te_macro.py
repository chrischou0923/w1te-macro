import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from pynput import keyboard, mouse
import threading
import time
import json
import os
import sys
import platform

# ======================
# App Config
# ======================
APP_NAME = "W1te Macro"
LIGHT_THEME = "flatly"
LOGO_SECONDS = 2

# ======================
# Paths & Settings
# ======================
def app_dir():
    try:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    except:
        return os.getcwd()

SETTINGS_PATH = os.path.join(app_dir(), "settings.json")

def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except:
        pass

settings = load_settings()

# ======================
# State
# ======================
running = False
selected_cps = int(settings.get("cps", 100))
mode = settings.get("mode", "toggle")
hotkey = settings.get("hotkey", "f")
output_mode = settings.get("output", "keyboard")  # keyboard / mouse

capture_hotkey = False

kb_controller = keyboard.Controller()
mouse_controller = mouse.Controller()

# ======================
# Language
# ======================
LANG = {
    "English": {
        "title": "W1te Auto Clicker",
        "hotkey": "Hotkey",
        "detect": "Detect",
        "mode": "Mode",
        "toggle": "Toggle",
        "hold": "Hold",
        "speed": "Speed (CPS)",
        "output": "Output",
        "keyboard": "Key (F)",
        "mouse": "Mouse Left",
        "status_wait": "Waiting",
        "status_run": "Clicking",
    },
    "繁體中文": {
        "title": "W1te 自動連點器",
        "hotkey": "啟動熱鍵",
        "detect": "偵測",
        "mode": "模式",
        "toggle": "開關式",
        "hold": "按壓式",
        "speed": "速度 (CPS)",
        "output": "輸出方式",
        "keyboard": "鍵盤 F",
        "mouse": "滑鼠左鍵",
        "status_wait": "等待中",
        "status_run": "連點中",
    },
    "한국어": {
        "title": "W1te 오토 클릭커",
        "hotkey": "핫키",
        "detect": "감지",
        "mode": "모드",
        "toggle": "토글",
        "hold": "홀드",
        "speed": "속도 (CPS)",
        "output": "출력",
        "keyboard": "키보드 F",
        "mouse": "마우스 왼쪽",
        "status_wait": "대기",
        "status_run": "클릭 중",
    }
}

lang_name = settings.get("lang", "English")
L = LANG[lang_name]

# ======================
# Auto Click Thread
# ======================
def clicker():
    global running
    while True:
        if running:
            if output_mode == "keyboard":
                kb_controller.press("f")
                kb_controller.release("f")
            else:
                mouse_controller.click(mouse.Button.left)
            time.sleep(1 / max(1, selected_cps))
        else:
            time.sleep(0.05)

# ======================
# Listener
# ======================
def on_press(key):
    global running, capture_hotkey, hotkey

    if capture_hotkey:
        try:
            hotkey = key.char.lower()
        except:
            hotkey = str(key).replace("Key.", "")
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, hotkey.upper())
        capture_hotkey = False
        save_all()
        return

    if mode_var.get() == "hold":
        if str(key).replace("Key.", "").lower() == hotkey:
            running = True
            status_var.set(L["status_run"])

    if mode_var.get() == "toggle":
        if str(key).replace("Key.", "").lower() == hotkey:
            running = not running
            status_var.set(L["status_run"] if running else L["status_wait"])

def on_release(key):
    global running
    if mode_var.get() == "hold":
        if str(key).replace("Key.", "").lower() == hotkey:
            running = False
            status_var.set(L["status_wait"])

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# ======================
# UI
# ======================
root = ttk.Window(title=APP_NAME, themename=LIGHT_THEME, size=(420, 320))
root.resizable(False, False)

title = ttk.Label(root, text=L["title"], font=("Segoe UI", 18, "bold"))
title.pack(pady=10)

frm = ttk.Frame(root, padding=10)
frm.pack(fill=X)

# Hotkey
ttk.Label(frm, text=L["hotkey"]).grid(row=0, column=0, sticky=W)
hotkey_entry = ttk.Entry(frm, width=8)
hotkey_entry.insert(0, hotkey.upper())
hotkey_entry.grid(row=0, column=1, padx=6)

def start_detect():
    global capture_hotkey
    capture_hotkey = True

ttk.Button(frm, text=L["detect"], command=start_detect).grid(row=0, column=2)

# Mode
ttk.Label(frm, text=L["mode"]).grid(row=1, column=0, sticky=W, pady=6)
mode_var = ttk.StringVar(value=mode)
ttk.Radiobutton(frm, text=L["toggle"], variable=mode_var, value="toggle").grid(row=1, column=1)
ttk.Radiobutton(frm, text=L["hold"], variable=mode_var, value="hold").grid(row=1, column=2)

# CPS
ttk.Label(frm, text=L["speed"]).grid(row=2, column=0, sticky=W, pady=6)
cps_var = ttk.StringVar(value=str(selected_cps))
ttk.Combobox(frm, textvariable=cps_var, values=["10","20","50","100","200","300"], width=8).grid(row=2, column=1)

# Output
ttk.Label(frm, text=L["output"]).grid(row=3, column=0, sticky=W, pady=6)
output_var = ttk.StringVar(value=output_mode)
ttk.Radiobutton(frm, text=L["keyboard"], variable=output_var, value="keyboard").grid(row=3, column=1)
ttk.Radiobutton(frm, text=L["mouse"], variable=output_var, value="mouse").grid(row=3, column=2)

# Status
status_var = ttk.StringVar(value=L["status_wait"])
ttk.Label(root, textvariable=status_var, bootstyle="secondary").pack(pady=10)

# ======================
# Save
# ======================
def save_all():
    global selected_cps, output_mode, mode
    try:
        selected_cps = int(cps_var.get())
    except:
        selected_cps = 100
    output_mode = output_var.get()
    mode = mode_var.get()
    save_settings({
        "lang": lang_name,
        "hotkey": hotkey,
        "mode": mode,
        "cps": selected_cps,
        "output": output_mode,
    })

root.protocol("WM_DELETE_WINDOW", lambda: (save_all(), root.destroy()))

threading.Thread(target=clicker, daemon=True).start()
root.mainloop()


