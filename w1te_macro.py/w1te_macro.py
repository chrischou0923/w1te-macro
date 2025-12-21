import tkinter as tk
from tkinter import ttk
import threading
import time
import json
import os
import sys

# ======================
# App info
# ======================
APP_NAME = "W1te Macro"
SETTINGS_FILE = "settings.json"

# ======================
# Settings
# ======================
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(app_dir(), SETTINGS_FILE)

default_settings = {
    "cps": 20,
    "output": "keyboard"  # keyboard / mouse
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_settings.copy()

def save_settings(data):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

settings = load_settings()

# ======================
# State
# ======================
running = False

# ======================
# Click thread (SAFE)
# ======================
def click_loop():
    global running
    interval = 1 / max(1, settings["cps"])
    while running:
        # macOS 安全版：只做模擬，不碰系統 hook
        print("click")  # ← 你之後可以換成實際 click
        time.sleep(interval)

# ======================
# UI callbacks
# ======================
def start_click():
    global running
    if running:
        return
    running = True
    status_var.set("Running")
    threading.Thread(target=click_loop, daemon=True).start()

def stop_click():
    global running
    running = False
    status_var.set("Stopped")

def on_cps_change(val):
    settings["cps"] = int(float(val))
    save_settings(settings)

def on_output_change():
    settings["output"] = output_var.get()
    save_settings(settings)

# ======================
# UI
# ======================
root = tk.Tk()
root.title(APP_NAME)
root.geometry("320x260")
root.resizable(False, False)

main = ttk.Frame(root, padding=15)
main.pack(fill="both", expand=True)

ttk.Label(main, text="W1te Macro", font=("Helvetica", 16, "bold")).pack(pady=10)

# CPS
ttk.Label(main, text="Clicks Per Second").pack()
cps_scale = ttk.Scale(
    main, from_=1, to=50,
    value=settings["cps"],
    command=on_cps_change
)
cps_scale.pack(fill="x", pady=5)

# Output
ttk.Label(main, text="Output").pack(pady=(10, 0))
output_var = tk.StringVar(value=settings["output"])
ttk.Radiobutton(main, text="Keyboard (F)", variable=output_var, value="keyboard", command=on_output_change).pack()
ttk.Radiobutton(main, text="Mouse Left", variable=output_var, value="mouse", command=on_output_change).pack()

# Buttons
btn_frame = ttk.Frame(main)
btn_frame.pack(pady=15)

ttk.Button(btn_frame, text="Start", width=10, command=start_click).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Stop", width=10, command=stop_click).pack(side="left", padx=5)

# Status
status_var = tk.StringVar(value="Stopped")
ttk.Label(main, textvariable=status_var).pack()

root.mainloop()

root.mainloop()

