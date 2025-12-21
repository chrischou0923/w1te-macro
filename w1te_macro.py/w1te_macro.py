# ===============================
# W1te Macro - Final Release
# Windows / macOS Compatible
# ===============================

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from pynput import keyboard, mouse
import threading
import time
import random
import json
import os
import sys
import platform

# ===============================
# Safe mouse button resolver (macOS)
# ===============================
def safe_mouse_button(name: str):
    name = (name or "").lower()
    if hasattr(mouse.Button, name):
        return getattr(mouse.Button, name)
    return mouse.Button.left

# ===============================
# Paths / settings
# ===============================
def app_dir():
    return os.path.dirname(os.path.abspath(sys.argv[0]))

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
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

settings = load_settings()

# ===============================
# App config
# ===============================
APP_NAME = "W1te Macro"
LIGHT = "flatly"
DARK = "darkly"

# ===============================
# Globals
# ===============================
running = False
selected_cps = int(settings.get("cps", 100))
mode = settings.get("mode", "toggle")

hotkey_key = settings.get("hotkey", "f1")
output_key = settings.get("output", "left")

jitter_on = settings.get("jitter", False)
jitter_pct = float(settings.get("jitter_pct", 0.12))

# ===============================
# Controllers
# ===============================
kb = keyboard.Controller()
ms = mouse.Controller()

# ===============================
# CPS Test (safe – no trace trap)
# ===============================
TEST_RUNNING = False
TEST_START = 0
TEST_EVENTS = []

def record_emit():
    if TEST_RUNNING:
        TEST_EVENTS.append(time.perf_counter() - TEST_START)

# ===============================
# Auto click thread
# ===============================
def click_loop():
    global running
    while True:
        if running:
            try:
                if output_key in ("left", "right", "middle", "x1", "x2"):
                    ms.click(safe_mouse_button(output_key))
                else:
                    kb.press(output_key)
                    kb.release(output_key)

                record_emit()

                delay = 1 / max(1, selected_cps)
                if jitter_on:
                    delay *= random.uniform(1 - jitter_pct, 1 + jitter_pct)

                time.sleep(max(0.001, delay))
            except:
                running = False
        else:
            time.sleep(0.05)

# ===============================
# Hotkey handling
# ===============================
def on_press(key):
    global running
    try:
        name = key.char.lower()
    except:
        name = str(key).replace("Key.", "").lower()

    if name == hotkey_key:
        if mode == "toggle":
            running = not running
        else:
            running = True

def on_release(key):
    global running
    if mode == "hold":
        running = False

keyboard.Listener(on_press=on_press, on_release=on_release).start()

# ===============================
# UI
# ===============================
theme = DARK if settings.get("dark", False) else LIGHT
root = ttk.Window(APP_NAME, themename=theme, size=(900, 520))
root.resizable(False, False)

# ===============================
# Layout
# ===============================
main = ttk.Frame(root, padding=14)
main.pack(fill=BOTH, expand=True)

left = ttk.Frame(main)
left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

right = ttk.Frame(main)
right.pack(side=RIGHT, fill=BOTH)

# ===============================
# Left: Settings
# ===============================
ttk.Label(left, text="Settings", font=("Segoe UI", 16, "bold")).pack(anchor=W)

def apply():
    global selected_cps, mode
    selected_cps = int(cps_var.get())
    mode = mode_var.get()
    save_settings({
        "cps": selected_cps,
        "mode": mode,
        "hotkey": hotkey_key,
        "output": output_key,
        "jitter": jitter_var.get(),
        "jitter_pct": jitter_scale.get(),
        "dark": theme_var.get()
    })

cps_var = ttk.StringVar(value=str(selected_cps))
ttk.Label(left, text="CPS").pack(anchor=W, pady=(10, 0))
ttk.Combobox(left, values=["10","20","50","100","200","300","500"], textvariable=cps_var, width=10).pack(anchor=W)

mode_var = ttk.StringVar(value=mode)
ttk.Radiobutton(left, text="Toggle", value="toggle", variable=mode_var).pack(anchor=W)
ttk.Radiobutton(left, text="Hold", value="hold", variable=mode_var).pack(anchor=W)

jitter_var = ttk.BooleanVar(value=jitter_on)
ttk.Checkbutton(left, text="Humanize (Jitter)", variable=jitter_var).pack(anchor=W, pady=(10,0))
jitter_scale = ttk.Scale(left, from_=0, to=0.3)
jitter_scale.set(jitter_pct)
jitter_scale.pack(anchor=W)

ttk.Button(left, text="Apply", command=apply, bootstyle="primary").pack(anchor=W, pady=12)

# ===============================
# Right: CPS Test (embedded)
# ===============================
ttk.Label(right, text="CPS Test", font=("Segoe UI", 16, "bold")).pack(anchor=W)

cps_label = ttk.Label(right, text="0.0 CPS", font=("Segoe UI", 32, "bold"))
cps_label.pack(pady=20)

def start_test():
    global TEST_RUNNING, TEST_START, TEST_EVENTS
    TEST_EVENTS.clear()
    TEST_START = time.perf_counter()
    TEST_RUNNING = True
    root.after(5000, finish_test)
    update_test()

def update_test():
    if not TEST_RUNNING:
        return
    elapsed = time.perf_counter() - TEST_START
    cps = len(TEST_EVENTS) / max(0.1, elapsed)
    cps_label.config(text=f"{cps:.1f} CPS")
    root.after(100, update_test)

def finish_test():
    global TEST_RUNNING
    TEST_RUNNING = False
    cps = len(TEST_EVENTS) / 5
    messagebox.showinfo("CPS Test", f"Average CPS: {cps:.1f}")

ttk.Button(right, text="Start CPS Test", bootstyle="success", command=start_test).pack()

# ===============================
# Start threads
# ===============================
threading.Thread(target=click_loop, daemon=True).start()

root.mainloop()



