# ======================
# W1te Macro (macOS-safe, PyInstaller onefile OK)
# ======================

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pynput import keyboard, mouse
import threading
import time
import tkinter.font as tkfont
import json
import os
import sys
import platform
import random

# ======================
# Mouse button compatibility (macOS safe)
# ======================
def get_mouse_button(name: str, fallback="left"):
    name = (name or "").lower()
    if name in ("x1", "x2") and not hasattr(mouse.Button, name):
        name = fallback
    return getattr(mouse.Button, name, getattr(mouse.Button, fallback, mouse.Button.left))


# ======================
# Matplotlib (LAZY LOAD) – macOS SIGTRAP FIX
# ======================
MPL_OK = False
MPL_ERR = ""
Figure = None
FigureCanvasTkAgg = None

def _mpl_config_dir() -> str:
    try:
        base = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "W1teMacro",
            "mplcache",
        )
        os.makedirs(base, exist_ok=True)
        return base
    except:
        import tempfile
        base = os.path.join(tempfile.gettempdir(), "W1teMacro_mplcache")
        try:
            os.makedirs(base, exist_ok=True)
        except:
            pass
        return base

def ensure_matplotlib_loaded() -> bool:
    global MPL_OK, MPL_ERR, Figure, FigureCanvasTkAgg
    if MPL_OK and Figure and FigureCanvasTkAgg:
        return True
    try:
        os.environ["MPLCONFIGDIR"] = _mpl_config_dir()
        os.environ["MPLBACKEND"] = "TkAgg"
        from matplotlib.figure import Figure as _Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as _FCTK
        Figure = _Figure
        FigureCanvasTkAgg = _FCTK
        MPL_OK = True
        MPL_ERR = ""
        return True
    except Exception as e:
        MPL_OK = False
        MPL_ERR = str(e)
        return False


# ======================
# App Config
# ======================
LIGHT_THEME = "flatly"
DARK_THEME = "darkly"
APP_NAME = "W1te Macro"
LOGO_SECONDS = 2


# ======================
# Settings
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
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except:
        return {}

def write_settings_atomic(data):
    try:
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_PATH)
    except:
        pass

_loaded = load_settings()


# ======================
# Globals
# ======================
running = False
selected_cps = int(_loaded.get("cps", 100))

hotkey_kind = _loaded.get("hotkey_kind", "keyboard")
hotkey_type = _loaded.get("hotkey_type", "special")
hotkey_char = str(_loaded.get("hotkey_char", "f")).lower()[:1]
hotkey_special = getattr(keyboard.Key, str(_loaded.get("hotkey_special", "f1")), keyboard.Key.f1)
hotkey_mouse_btn = get_mouse_button(_loaded.get("hotkey_mouse_btn", "left"))

output_kind = _loaded.get("output_kind", "keyboard")
output_type = _loaded.get("output_type", "char")
output_char = str(_loaded.get("output_char", "f")).lower()[:1]
output_special = getattr(keyboard.Key, str(_loaded.get("output_special", "space")), keyboard.Key.space)
output_mouse_btn = get_mouse_button(_loaded.get("output_mouse_btn", "left"))

jitter_on = bool(_loaded.get("jitter_on", False))
jitter_pct = float(_loaded.get("jitter_pct", 0.12))
micro_pause_on = bool(_loaded.get("micro_pause_on", True))

LOCK_HOLD = "HOLD"
LOCK_TOGGLE = "TOGGLE"
pressed_keys = set()
capture_target = None

kb_listener = None
ms_listener = None

# CPS test
TEST_BIN = 0.1
test_running = False
test_duration = 10
test_start_t = 0.0
test_emit_times = []
test_lock = threading.Lock()

# plot handles (lazy)
fig = ax = canvas_plot = None
fig2 = ax2 = canvas_plot2 = None


# ======================
# Helpers
# ======================
def record_test_emit():
    if not test_running:
        return
    with test_lock:
        test_emit_times.append(time.perf_counter() - test_start_t)


# ======================
# Auto click thread
# ======================
def autoclicker_thread():
    global running
    mc = mouse.Controller()
    kc = keyboard.Controller()

    while True:
        if running:
            try:
                if output_kind == "mouse":
                    mc.click(output_mouse_btn)
                else:
                    if output_type == "char":
                        kc.press(output_char)
                        kc.release(output_char)
                    else:
                        kc.press(output_special)
                        kc.release(output_special)

                record_test_emit()

                base = 1 / max(1, selected_cps)
                delay = base
                if jitter_on:
                    delay *= (1 + random.uniform(-jitter_pct, jitter_pct))
                    if micro_pause_on and random.random() < 0.02:
                        delay += random.uniform(0.05, 0.12)
                time.sleep(max(0.001, delay))
            except:
                running = False
        else:
            time.sleep(0.05)


# ======================
# Listeners
# ======================
def is_hotkey_pressed(key):
    if hotkey_kind != "keyboard":
        return False
    if hotkey_type == "char":
        try:
            return key.char and key.char.lower() == hotkey_char
        except:
            return False
    return key == hotkey_special

def on_press(key):
    global running
    if capture_target:
        return
    if hotkey_kind != "keyboard":
        return
    if is_hotkey_pressed(key):
        if LOCK_TOGGLE not in pressed_keys:
            pressed_keys.add(LOCK_TOGGLE)
            running = not running

def on_release(key):
    if LOCK_TOGGLE in pressed_keys:
        pressed_keys.discard(LOCK_TOGGLE)

def on_click(x, y, button, pressed):
    global running
    if capture_target:
        return
    if hotkey_kind != "mouse":
        return
    if button != hotkey_mouse_btn:
        return
    if pressed:
        running = not running

def start_listeners():
    global kb_listener, ms_listener
    kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    ms_listener = mouse.Listener(on_click=on_click)
    kb_listener.start()
    ms_listener.start()


# ======================
# CPS Test
# ======================
def _make_plot(parent):
    ensure_matplotlib_loaded()
    f = Figure(figsize=(6, 3), dpi=100)
    a = f.add_subplot(111)
    a.grid(True, alpha=0.25)
    c = FigureCanvasTkAgg(f, master=parent)
    c.get_tk_widget().pack(fill=BOTH, expand=True)
    return f, a, c

def start_cps_test():
    global test_running, test_start_t, fig, ax, canvas_plot
    if not ensure_matplotlib_loaded():
        messagebox.showerror("CPS Test", MPL_ERR)
        return

    for w in plot_holder.winfo_children():
        w.destroy()

    fig, ax, canvas_plot = _make_plot(plot_holder)

    test_running = True
    test_emit_times.clear()
    test_start_t = time.perf_counter()
    update_test_tick()

def update_test_tick():
    global test_running
    if not test_running:
        return

    elapsed = time.perf_counter() - test_start_t
    if elapsed >= test_duration:
        test_running = False
        finish_cps_test()
        return

    with test_lock:
        count = len(test_emit_times)

    ax.clear()
    ax.set_ylim(0, max(50, selected_cps * 1.5))
    ax.bar(["CPS"], [count / max(0.1, elapsed)])
    canvas_plot.draw_idle()

    root.after(80, update_test_tick)

def finish_cps_test():
    total = len(test_emit_times)
    avg = total / max(0.1, test_duration)
    messagebox.showinfo("Result", f"Avg CPS: {avg:.1f}\nTotal: {total}")


# ======================
# UI
# ======================
root = ttk.Window(APP_NAME, themename=LIGHT_THEME, size=(820, 620))
root.minsize(580, 460)

main = ttk.Frame(root, padding=16)
main.pack(fill=BOTH, expand=True)

ttk.Label(main, text="W1te Macro", font=("Segoe UI", 22, "bold")).pack(anchor=W)
ttk.Button(main, text="Start CPS Test", bootstyle="info", command=start_cps_test).pack(anchor=W, pady=12)

plot_holder = ttk.Frame(main)
plot_holder.pack(fill=BOTH, expand=True)
ttk.Label(plot_holder, text="Plot loads when test starts", bootstyle="secondary").pack(pady=20)

# ======================
# Start
# ======================
threading.Thread(target=autoclicker_thread, daemon=True).start()
start_listeners()
root.mainloop()



