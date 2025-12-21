# w1te_macro.py
# W1te Macro (macOS + Windows) — Final A Version
# ✅ 有語言選擇畫面
# ✅ 有「偵測熱鍵」(啟動連點器)
# ✅ CPS 選單保留（控制速度）
# ✅ CPS Test 已移除（你說不用）
# ✅ 輸出鍵固定只給兩種選擇：F 或 Mouse Left（左鍵）
# ✅ 修好：熱鍵判定 / 連點實際輸出 / macOS x1/x2 相容（不會再 AttributeError）

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

def mouse_btn_to_str(btn):
    if btn == mouse.Button.left: return "left"
    if btn == mouse.Button.right: return "right"
    if btn == mouse.Button.middle: return "middle"
    if hasattr(mouse.Button, "x1") and btn == mouse.Button.x1: return "x1"
    if hasattr(mouse.Button, "x2") and btn == mouse.Button.x2: return "x2"
    return "left"

# ======================
# App Config
# ======================
LIGHT_THEME = "flatly"
DARK_THEME = "darkly"

APP_NAME = "W1te Macro"
LOGO_SECONDS = 2  # Logo 停留秒數

# ======================
# Settings persistence
# ======================
def app_dir() -> str:
    try:
        p = sys.argv[0]
        if not p:
            return os.getcwd()
        return os.path.dirname(os.path.abspath(p))
    except:
        return os.getcwd()

SETTINGS_PATH = os.path.join(app_dir(), "settings.json")

def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except:
        return {}

_loaded_settings = load_settings()

def write_settings_atomic(data: dict):
    try:
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_PATH)
    except:
        pass

# ======================
# Globals
# ======================
running = False
selected_cps = int(_loaded_settings.get("cps", 100))

# Hotkey storage
hotkey_kind = _loaded_settings.get("hotkey_kind", "keyboard")  # "keyboard" or "mouse"
hotkey_type = _loaded_settings.get("hotkey_type", "special")   # "char" or "special"
hotkey_char = str(_loaded_settings.get("hotkey_char", "f")).lower()[:1]
_hotkey_special_name = str(_loaded_settings.get("hotkey_special", "f1")).lower()
hotkey_special = getattr(keyboard.Key, _hotkey_special_name, keyboard.Key.f1)
hotkey_mouse_btn = get_mouse_button(str(_loaded_settings.get("hotkey_mouse_btn", "left")), fallback="left")

# Output selection: ONLY "F" or "MOUSE_LEFT"
output_choice = _loaded_settings.get("output_choice", "F")
if output_choice not in ("F", "MOUSE_LEFT"):
    output_choice = "F"

# Humanize / Jitter (persisted)
jitter_on = bool(_loaded_settings.get("jitter_on", False))
try:
    jitter_pct = float(_loaded_settings.get("jitter_pct", 0.12))
except:
    jitter_pct = 0.12
micro_pause_on = bool(_loaded_settings.get("micro_pause_on", True))

# Listener / permission status
kb_listener = None
ms_listener = None
listeners_ok = True
listener_error_text = ""

# Capture target: None / "hotkey"
capture_target = None
pressed_keys = set()

LOCK_HOLD = "HOLD_LOCK"
LOCK_TOGGLE = "TOGGLE_LOCK"
LOCK_MOUSE_TOGGLE = "MOUSE_TOGGLE_LOCK"

fullscreen = False

# ======================
# Languages
# ======================
LANG_EN = {
    "title": "W1te Auto Clicker PRO",
    "subtitle": "Hotkey / Mouse Button • Toggle / Hold • CPS • Output (F / Left Click)",
    "card_hotkey": " HOTKEY ",
    "card_settings": " SETTINGS ",
    "hotkey": "Hotkey",
    "detect": "Detect",
    "mode": "Mode",
    "speed": "Speed (CPS)",
    "toggle": "Toggle",
    "hold": "Hold",
    "status_wait": "Waiting",
    "status_detect_hotkey": "Detecting HOTKEY: press a key / mouse button once",
    "status_run": "Clicking",
    "status_stop": "Stopped",
    "hotkey_now": "Current hotkey:",
    "tip_hotkey": "Supports: a / 1 / … or F1–F12 or mouse buttons (left/right/middle/x1/x2 if available)",
    "theme": "Theme",
    "light": "Light",
    "dark": "Dark",
    "language": "Language",
    "warn_same_key": "⚠ Hotkey equals output (F). Please use a different hotkey (e.g., F1).",
    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ Hotkey/Mouse listener blocked. Enable macOS permissions and press Retry.",
    "perm_help_title": "macOS Permissions",
    "output": "Output",
    "output_f": "Keyboard F",
    "output_left": "Mouse Left Click",
}
LANG_ZH = {
    "title": "W1te 自動連點工具 PRO",
    "subtitle": "熱鍵 / 滑鼠按鍵 • 開關/按壓 • CPS • 輸出（F / 左鍵）",
    "card_hotkey": " 熱鍵 ",
    "card_settings": " 設定 ",
    "hotkey": "啟動熱鍵",
    "detect": "偵測",
    "mode": "模式",
    "speed": "速度 (CPS)",
    "toggle": "開關式",
    "hold": "按壓式",
    "status_wait": "等待設定",
    "status_detect_hotkey": "偵測熱鍵中：請按下你要的鍵或滑鼠鍵一次",
    "status_run": "連點中",
    "status_stop": "已停止",
    "hotkey_now": "目前熱鍵：",
    "tip_hotkey": "支援：a / 1 / … 或 F1～F12 或滑鼠鍵(左/右/中/x1/x2 若支援)",
    "theme": "主題",
    "light": "白",
    "dark": "黑",
    "language": "語言",
    "warn_same_key": "⚠ 熱鍵與輸出（F）相同，可能自觸發。請換別的熱鍵（例如 F1）。",
    "retry": "重試",
    "mac_perm": "macOS 權限",
    "perm_warn_listener": "⚠ 熱鍵/滑鼠監聽被擋住。請開啟 macOS 權限後按「重試」。",
    "perm_help_title": "macOS 權限",
    "output": "輸出",
    "output_f": "鍵盤 F",
    "output_left": "滑鼠左鍵",
}
LANG_KR = {
    "title": "W1te 오토 클릭커 PRO",
    "subtitle": "핫키 / 마우스 버튼 • 토글/홀드 • CPS • 출력(F / 좌클릭)",
    "card_hotkey": " 핫키 ",
    "card_settings": " 설정 ",
    "hotkey": "시작 키",
    "detect": "감지",
    "mode": "모드",
    "speed": "속도 (CPS)",
    "toggle": "토글식",
    "hold": "홀드식",
    "status_wait": "대기",
    "status_detect_hotkey": "핫키 감지 중: 키/마우스를 한 번 누르세요",
    "status_run": "클릭 중",
    "status_stop": "정지됨",
    "hotkey_now": "현재 핫키:",
    "tip_hotkey": "지원: a / 1 / … 또는 F1~F12 또는 마우스 버튼(지원 시 x1/x2)",
    "theme": "테마",
    "light": "라이트",
    "dark": "다크",
    "language": "언어",
    "warn_same_key": "⚠ 핫키가 출력(F)와 같아요. 다른 핫키로 바꿔주세요 (예: F1).",
    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ 리스너가 차단됨. macOS 권한을 켜고 Retry 누르세요.",
    "perm_help_title": "macOS Permissions",
    "output": "출력",
    "output_f": "키보드 F",
    "output_left": "마우스 왼쪽 클릭",
}

current_lang = LANG_EN

# ======================
# UI Thread Helpers
# ======================
MAIN_THREAD = None
def ui(fn):
    if MAIN_THREAD is None:
        return
    if threading.current_thread() is MAIN_THREAD:
        fn()
    else:
        root.after(0, fn)

# ======================
# Scrollable container
# ======================
class VScrollable(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner.bind("<Enter>", self._bind_mousewheel)
        self.inner.bind("<Leave>", self._unbind_mousewheel)

    def _on_inner_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        try:
            self.canvas.itemconfigure(self._win_id, width=self.canvas.winfo_width())
        except:
            pass

    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        delta = event.delta
        if platform.system().lower() == "darwin":
            self.canvas.yview_scroll(int(-delta), "units")
        else:
            self.canvas.yview_scroll(int(-delta / 120), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

# ======================
# Auto UI Scaling
# ======================
BASE_W, BASE_H = 580, 460
SCALE_MIN, SCALE_MAX = 1.0, 1.95
FONT_NAMES = ["TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"]
base_font_sizes = {}
TITLE_BASE = 18

_scale_job = None
_last_scale = None

def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def apply_scale(scale: float):
    global _last_scale
    scale = _clamp(scale, SCALE_MIN, SCALE_MAX)
    if _last_scale is not None and abs(scale - _last_scale) < 0.03:
        return
    _last_scale = scale
    try:
        root.tk.call("tk", "scaling", scale)
    except:
        pass

    for name, base_size in base_font_sizes.items():
        try:
            f = tkfont.nametofont(name)
            new_size = int(base_size * scale)
            if new_size == 0:
                new_size = -1 if base_size < 0 else 1
            f.configure(size=new_size)
        except:
            pass

    try:
        title_label.configure(font=("Segoe UI", max(14, int(TITLE_BASE * scale)), "bold"))
    except:
        pass

def on_root_resize(event):
    global _scale_job
    if event.widget != root:
        return
    if _scale_job is not None:
        try:
            root.after_cancel(_scale_job)
        except:
            pass

    w = max(1, root.winfo_width())
    h = max(1, root.winfo_height())
    target = min(w / BASE_W, h / BASE_H)
    _scale_job = root.after(90, lambda: (apply_scale(target), schedule_save()))

# ======================
# Settings save (debounced)
# ======================
_save_job = None

def _key_to_display(key_obj):
    return str(key_obj).replace("Key.", "").upper()

def _safe_get(var, default=None):
    try:
        return var.get()
    except:
        return default

def gather_settings() -> dict:
    try:
        w = int(root.winfo_width())
        h = int(root.winfo_height())
    except:
        w, h = 820, 620

    data = {
        "lang": _safe_get(globals().get("lang_var"), _loaded_settings.get("lang", "English")),
        "theme_dark": bool(_safe_get(globals().get("theme_var"), bool(_loaded_settings.get("theme_dark", False)))),
        "mode": _safe_get(globals().get("mode_var"), _loaded_settings.get("mode", "toggle")),
        "cps": int(_safe_get(globals().get("cps_var"), int(_loaded_settings.get("cps", 100)))),

        "hotkey_kind": hotkey_kind,
        "hotkey_type": hotkey_type,
        "hotkey_char": hotkey_char,
        "hotkey_special": str(hotkey_special).replace("Key.", ""),
        "hotkey_mouse_btn": mouse_btn_to_str(hotkey_mouse_btn),

        "output_choice": _safe_get(globals().get("output_var"), output_choice),

        "jitter_on": bool(_safe_get(globals().get("jitter_var"), jitter_on)),
        "jitter_pct": float(_safe_get(globals().get("jitter_pct_var"), jitter_pct)),
        "micro_pause_on": bool(_safe_get(globals().get("micro_pause_var"), micro_pause_on)),

        "window_w": w,
        "window_h": h,
    }
    return data

def write_settings_now():
    write_settings_atomic(gather_settings())

def schedule_save():
    global _save_job
    if MAIN_THREAD is None:
        return
    if _save_job is not None:
        try:
            root.after_cancel(_save_job)
        except:
            pass
    _save_job = root.after(280, write_settings_now)

# ======================
# UI Helpers
# ======================
def set_status(text, style):
    def _():
        status_var.set(text)
        status_badge.configure(bootstyle=style)
    ui(_)

def _format_hotkey_text():
    if hotkey_kind == "mouse":
        s = mouse_btn_to_str(hotkey_mouse_btn).upper()
        if s == "X1": return "XBUTTON1"
        if s == "X2": return "XBUTTON2"
        return s
    else:
        if hotkey_type == "char":
            return hotkey_char.upper()
        return _key_to_display(hotkey_special)

def update_hotkey_info():
    def _():
        hotkey_info_var.set(f"{current_lang['hotkey_now']} {_format_hotkey_text()}")
    ui(_)

def _is_macos():
    return platform.system().lower() == "darwin"

def show_macos_permission_help():
    msg = (
        "macOS 需要允許權限，否則熱鍵/滑鼠監聽可能會無效。\n\n"
        "請到：\n"
        "系統設定 → 隱私權與安全性 →\n"
        "✅ 輔助使用 (Accessibility)\n"
        "✅ 輸入監控 (Input Monitoring)\n\n"
        "Terminal 跑：允許 Terminal\n"
        "打包 App：允許你的 App\n\n"
        "開完後回到程式按「重試」。"
    )
    messagebox.showinfo(current_lang["perm_help_title"], msg)

def _refresh_permission_status():
    if capture_target == "hotkey":
        set_status(current_lang["status_detect_hotkey"], "warning")
    elif running:
        set_status(current_lang["status_run"], "success")
    else:
        set_status(current_lang["status_wait"], "secondary")

def check_self_trigger_warning():
    # 只有輸出是 F 時才會有「熱鍵=F」的自觸發問題
    if output_var.get() == "F" and hotkey_kind == "keyboard" and hotkey_type == "char":
        if hotkey_char.lower() == "f" and (not capture_target) and (not running):
            set_status(current_lang["warn_same_key"], "warning")

# ======================
# Key matching (FIXED: macOS/windows both)
# ======================
def key_matches_hotkey(key_obj) -> bool:
    if hotkey_kind != "keyboard":
        return False
    if hotkey_type == "char":
        try:
            return key_obj.char and key_obj.char.lower() == hotkey_char
        except:
            return False
    else:
        return key_obj == hotkey_special

# ======================
# Click Thread (Auto Clicker)  ✅ FIXED OUTPUT
# ======================
def autoclicker_thread():
    global running
    ms = mouse.Controller()
    kb = keyboard.Controller()

    while True:
        if running:
            try:
                # output
                if output_var.get() == "MOUSE_LEFT":
                    ms.click(mouse.Button.left)
                else:
                    kb.press("f")
                    kb.release("f")

                # cps
                try:
                    cps = max(1, int(cps_var.get()))
                except:
                    cps = 100
                base = 1 / cps

                # humanize
                if jitter_var.get() and float(jitter_pct_var.get()) > 0:
                    pct = float(jitter_pct_var.get())
                    delay = base * (1.0 + random.uniform(-pct, pct))
                else:
                    delay = base

                if jitter_var.get() and micro_pause_var.get():
                    if random.random() < 0.02:
                        delay += random.uniform(0.05, 0.14)

                time.sleep(max(0.001, delay))
            except:
                running = False
                _refresh_permission_status()
                time.sleep(0.05)
        else:
            time.sleep(0.05)

# ======================
# Capture hotkey
# ======================
def start_capture_hotkey():
    global capture_target, running
    running = False
    pressed_keys.clear()
    capture_target = "hotkey"
    _refresh_permission_status()

def set_hotkey_keyboard_char(ch: str):
    global hotkey_kind, hotkey_type, hotkey_char, capture_target, running
    hotkey_kind = "keyboard"
    hotkey_type = "char"
    hotkey_char = (ch or "f").lower()[:1]
    capture_target = None
    running = False
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, hotkey_char.upper())
        update_hotkey_info()
        check_self_trigger_warning()
        _refresh_permission_status()
        schedule_save()
    ui(_)

def set_hotkey_keyboard_special(key_obj):
    global hotkey_kind, hotkey_type, hotkey_special, capture_target, running
    hotkey_kind = "keyboard"
    hotkey_type = "special"
    hotkey_special = key_obj
    capture_target = None
    running = False
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, _key_to_display(key_obj))
        update_hotkey_info()
        check_self_trigger_warning()
        _refresh_permission_status()
        schedule_save()
    ui(_)

def set_hotkey_mouse(btn):
    global hotkey_kind, hotkey_mouse_btn, capture_target, running
    hotkey_kind = "mouse"
    hotkey_mouse_btn = btn
    capture_target = None
    running = False
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, _format_hotkey_text())
        update_hotkey_info()
        check_self_trigger_warning()
        _refresh_permission_status()
        schedule_save()
    ui(_)

# ======================
# Apply Settings
# ======================
def apply_all_settings(event=None):
    global selected_cps, running
    running = False
    pressed_keys.clear()

    try:
        selected_cps = int(cps_var.get())
    except:
        selected_cps = 100
        cps_var.set("100")

    _refresh_permission_status()
    check_self_trigger_warning()
    schedule_save()

def on_mode_change():
    global running
    running = False
    pressed_keys.clear()
    _refresh_permission_status()
    schedule_save()

# ======================
# Keyboard / Mouse Listeners (Main)
# ======================
def on_press(key):
    global running, capture_target

    # Capture HOTKEY
    if capture_target == "hotkey":
        try:
            # prefer special keys
            specials = {
                keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3, keyboard.Key.f4, keyboard.Key.f5,
                keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9, keyboard.Key.f10,
                keyboard.Key.f11, keyboard.Key.f12,
                keyboard.Key.space, keyboard.Key.enter, keyboard.Key.shift,
                keyboard.Key.ctrl, keyboard.Key.alt
            }
            if key in specials:
                set_hotkey_keyboard_special(key)
                return
            ch = key.char
            if ch:
                set_hotkey_keyboard_char(ch)
                return
        except:
            set_hotkey_keyboard_special(key)
            return
        return

    # Normal run (keyboard hotkey)
    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "hold":
        if key_matches_hotkey(key):
            if LOCK_HOLD in pressed_keys:
                return
            pressed_keys.add(LOCK_HOLD)
            running = True
            _refresh_permission_status()
        return

    if mode_var.get() == "toggle":
        if key_matches_hotkey(key):
            if LOCK_TOGGLE in pressed_keys:
                return
            pressed_keys.add(LOCK_TOGGLE)
            running = not running
            _refresh_permission_status()
        return

def on_release(key):
    global running
    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "toggle":
        if key_matches_hotkey(key):
            pressed_keys.discard(LOCK_TOGGLE)
        return

    if mode_var.get() == "hold":
        if key_matches_hotkey(key):
            pressed_keys.discard(LOCK_HOLD)
            running = False
            _refresh_permission_status()

def on_click(x, y, button, pressed):
    global running, capture_target

    # Capture by mouse
    if pressed and capture_target == "hotkey":
        set_hotkey_mouse(button)
        return

    # Normal run (mouse hotkey)
    if hotkey_kind != "mouse":
        return
    if button != hotkey_mouse_btn:
        return

    if mode_var.get() == "hold":
        running = bool(pressed)
        _refresh_permission_status()
        return

    if mode_var.get() == "toggle":
        if pressed:
            if LOCK_MOUSE_TOGGLE in pressed_keys:
                return
            pressed_keys.add(LOCK_MOUSE_TOGGLE)
            running = not running
            _refresh_permission_status()
        else:
            pressed_keys.discard(LOCK_MOUSE_TOGGLE)

def stop_listeners():
    global kb_listener, ms_listener
    try:
        if kb_listener:
            kb_listener.stop()
    except:
        pass
    try:
        if ms_listener:
            ms_listener.stop()
    except:
        pass
    kb_listener = None
    ms_listener = None

def start_listeners():
    global kb_listener, ms_listener, listeners_ok, listener_error_text
    stop_listeners()
    try:
        kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        kb_listener.start()
        ms_listener = mouse.Listener(on_click=on_click)
        ms_listener.start()
        listeners_ok = True
        listener_error_text = ""
    except Exception as e:
        listeners_ok = False
        listener_error_text = str(e)[:250]
        set_status(current_lang["perm_warn_listener"], "warning")
    _refresh_permission_status()

def retry_listeners():
    start_listeners()
    update_language()

# ======================
# Rounded lang buttons
# ======================
def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=24, **kwargs):
    points = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=32, **kwargs)

def _hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def _shade(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * factor); g = int(g * factor); b = int(b * factor)
    return _rgb_to_hex(r, g, b)

class RoundLangButton(tk.Canvas):
    def __init__(self, master, title, desc, command, radius=22, **kwargs):
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.title = title
        self.desc = desc
        self.command = command
        self.radius = radius
        self.fill = "#2b7fff"
        self.hover_fill = "#256fe0"
        self.outline = "#000000"
        self.text_color = "#ffffff"
        self.configure(cursor="hand2")
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._click())
        self._is_hover = False
        self.redraw()

    def set_palette(self, fill, hover_fill, outline, text="#ffffff"):
        self.fill = fill
        self.hover_fill = hover_fill
        self.outline = outline
        self.text_color = text
        self.redraw()

    def _set_hover(self, on: bool):
        self._is_hover = on
        self.redraw()

    def _click(self):
        try:
            if callable(self.command):
                self.command()
        except:
            pass

    def redraw(self):
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        bg = self.master.winfo_toplevel().style.colors.bg if hasattr(self.master.winfo_toplevel(), "style") else "#f5f5f5"
        try:
            self.configure(background=bg)
        except:
            pass
        pad = 2
        fill = self.hover_fill if self._is_hover else self.fill
        _round_rect(self, pad, pad, w - pad, h - pad, r=min(self.radius, int(h * 0.35)),
                    fill=fill, outline=self.outline, width=2)
        self.create_text(w / 2, h * 0.42, text=self.title, fill=self.text_color, font=("Segoe UI", 16, "bold"))
        self.create_text(w / 2, h * 0.72, text=self.desc, fill=self.text_color, font=("Segoe UI", 10))

# ======================
# Splash transitions
# ======================
def fade_to(alpha_target, step=0.08, delay=12, on_done=None):
    try:
        cur = float(root.attributes("-alpha"))
    except:
        cur = 1.0

    if alpha_target < cur:
        cur = max(alpha_target, cur - step)
    else:
        cur = min(alpha_target, cur + step)

    try:
        root.attributes("-alpha", cur)
    except:
        if on_done:
            root.after(0, on_done)
        return

    if abs(cur - alpha_target) <= 0.001:
        if on_done:
            root.after(delay, on_done)
        return

    root.after(delay, lambda: fade_to(alpha_target, step, delay, on_done))

def show_frame(frame_to_show):
    for f in (logo_frame, lang_frame, main_frame):
        try:
            f.pack_forget()
        except:
            pass
    frame_to_show.pack(fill=BOTH, expand=True)

# ======================
# Language / Theme update
# ======================
def update_language():
    global current_lang
    v = lang_var.get()
    if v == "繁體中文":
        current_lang = LANG_ZH
    elif v == "한국어":
        current_lang = LANG_KR
    else:
        current_lang = LANG_EN

    title_label.configure(text=current_lang["title"])
    subtitle_label.configure(text=current_lang["subtitle"])

    card1.configure(text=current_lang["card_hotkey"])
    card2.configure(text=current_lang["card_settings"])

    hotkey_label.configure(text=current_lang["hotkey"])
    detect_btn.configure(text=current_lang["detect"])
    tip_label.configure(text=current_lang["tip_hotkey"])

    mode_label.configure(text=current_lang["mode"])
    toggle_rb.configure(text=current_lang["toggle"])
    hold_rb.configure(text=current_lang["hold"])

    speed_label.configure(text=current_lang["speed"])

    output_label.configure(text=current_lang["output"])
    output_f_rb.configure(text=current_lang["output_f"])
    output_left_rb.configure(text=current_lang["output_left"])

    theme_btn.configure(text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})")
    lang_title.configure(text=current_lang["language"])

    try:
        retry_btn.configure(text=current_lang["retry"])
        mac_perm_btn.configure(text=current_lang["mac_perm"])
    except:
        pass

    update_hotkey_info()
    check_self_trigger_warning()
    _refresh_permission_status()
    schedule_save()

def apply_theme():
    theme = DARK_THEME if theme_var.get() else LIGHT_THEME
    root.style.theme_use(theme)
    schedule_save()

# ======================
# Fullscreen / Maximize
# ======================
def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    root.attributes("-fullscreen", fullscreen)
    schedule_save()

def exit_fullscreen(event=None):
    global fullscreen
    fullscreen = False
    root.attributes("-fullscreen", False)
    schedule_save()

def toggle_maximize(event=None):
    try:
        root.state("zoomed" if root.state() != "zoomed" else "normal")
    except:
        pass
    schedule_save()

# ======================
# Build UI
# ======================
default_w = int(_loaded_settings.get("window_w", 820))
default_h = int(_loaded_settings.get("window_h", 620))
default_w = max(580, min(2200, default_w))
default_h = max(460, min(1600, default_h))

root = ttk.Window(title=APP_NAME, themename=LIGHT_THEME, size=(default_w, default_h))
root.attributes("-alpha", 1.0)
root.resizable(True, True)
root.minsize(580, 460)

MAIN_THREAD = threading.current_thread()

for n in FONT_NAMES:
    try:
        f = tkfont.nametofont(n)
        base_font_sizes[n] = int(f.cget("size"))
    except:
        pass

root.bind("<F11>", toggle_fullscreen)
root.bind("<Escape>", exit_fullscreen)
root.bind("<Control-m>", toggle_maximize)
root.bind("<Configure>", on_root_resize)

# ---------- Frame 0: Logo ----------
logo_frame = tk.Frame(root, bg="white")
logo_label = tk.Label(logo_frame, text="w1te macro", bg="white", fg="black", font=("Segoe UI", 40, "bold"))
logo_label.place(relx=0.5, rely=0.5, anchor="center")

# ---------- Frame 1: Language Picker ----------
lang_frame = ttk.Frame(root)
lang_bg = ttk.Frame(lang_frame, padding=26)
lang_bg.pack(fill=BOTH, expand=True)

lang_canvas = tk.Canvas(lang_bg, highlightthickness=0, bd=0)
lang_canvas.pack(fill=BOTH, expand=True)

lang_content = ttk.Frame(lang_canvas, padding=24)
ttk.Label(lang_content, text="Select Language", font=("Segoe UI", 22, "bold")).pack()
ttk.Label(lang_content, text="언어 선택 • 語言選擇", bootstyle="secondary").pack(pady=(6, 18))

btn_area = ttk.Frame(lang_content)
btn_area.pack(fill=X)
btn_area.grid_columnconfigure(0, weight=1)
btn_area.grid_columnconfigure(1, weight=1)
btn_area.grid_columnconfigure(2, weight=1)

lang_btns = {}

def _update_lang_btn_colors():
    c = root.style.colors
    border = getattr(c, "border", "#d8d8d8")
    primary = getattr(c, "primary", "#2b7fff")
    info = getattr(c, "info", "#17a2b8")
    success = getattr(c, "success", "#28a745")
    lang_btns["zh"].set_palette(info, _shade(info, 0.90), border)
    lang_btns["en"].set_palette(primary, _shade(primary, 0.90), border)
    lang_btns["kr"].set_palette(success, _shade(success, 0.90), border)

def make_lang_round(col, key, title, desc, choice):
    wrap = ttk.Frame(btn_area)
    wrap.grid(row=0, column=col, padx=10, sticky="nsew")
    wrap.grid_columnconfigure(0, weight=1)
    btn = RoundLangButton(wrap, title=title, desc=desc, command=lambda: go_main_with_language(choice),
                          width=240, height=86)
    btn.grid(row=0, column=0, sticky="ew")
    lang_btns[key] = btn

def draw_lang_card():
    lang_canvas.delete("all")
    w = lang_canvas.winfo_width()
    h = lang_canvas.winfo_height()
    if w <= 10 or h <= 10:
        return
    colors = root.style.colors
    bg = getattr(colors, "bg", "#f5f5f5")
    card = getattr(colors, "light", "#ffffff")
    border = getattr(colors, "border", "#d8d8d8")
    lang_canvas.configure(background=bg)

    card_w = min(820, max(600, int(w * 0.74)))
    card_h = min(460, max(380, int(h * 0.62)))
    x1 = (w - card_w) // 2
    y1 = (h - card_h) // 2
    x2 = x1 + card_w
    y2 = y1 + card_h

    _round_rect(lang_canvas, x1, y1, x2, y2, r=30, fill=card, outline=border, width=2)
    lang_canvas.create_window((x1 + x2)//2, (y1 + y2)//2, window=lang_content, anchor="center")
    _update_lang_btn_colors()

lang_canvas.bind("<Configure>", lambda e: draw_lang_card())

make_lang_round(0, "zh", "繁體中文", "台灣 / 繁中介面", "繁體中文")
make_lang_round(1, "en", "English", "Default / International", "English")
make_lang_round(2, "kr", "한국어", "한국어 UI", "한국어")

ttk.Label(lang_content, text="Tip: You can change language later in settings.", bootstyle="secondary").pack(pady=(18, 0))

def lang_shortcut(choice):
    try:
        if lang_frame.winfo_ismapped():
            go_main_with_language(choice)
    except:
        pass

root.bind("1", lambda e: lang_shortcut("繁體中文"))
root.bind("2", lambda e: lang_shortcut("English"))
root.bind("3", lambda e: lang_shortcut("한국어"))

# ---------- Frame 2: Main ----------
main_frame = ttk.Frame(root)

scroll_wrap = VScrollable(main_frame)
scroll_wrap.pack(fill=BOTH, expand=True)

container = ttk.Frame(scroll_wrap.inner, padding=18)
container.pack(fill=BOTH, expand=True)

header = ttk.Frame(container)
header.pack(fill=X)

title_label = ttk.Label(header, text=current_lang["title"], font=("Segoe UI", 18, "bold"))
title_label.pack(anchor=W)

subtitle_label = ttk.Label(header, text=current_lang["subtitle"], bootstyle="secondary")
subtitle_label.pack(anchor=W, pady=(2, 0))

theme_row = ttk.Frame(header)
theme_row.pack(anchor=E, pady=(8, 0), fill=X)

theme_var = ttk.BooleanVar(value=bool(_loaded_settings.get("theme_dark", False)))

theme_btn = ttk.Checkbutton(
    theme_row,
    text="Theme (Light / Dark)",
    variable=theme_var,
    command=apply_theme,
    bootstyle="round-toggle"
)
theme_btn.pack(anchor=E)

ttk.Separator(container).pack(fill=X, pady=14)

# Card 1: Hotkey
card1 = ttk.Labelframe(container, text=current_lang["card_hotkey"], padding=14, bootstyle="primary")
card1.pack(fill=X, pady=(0, 12))

row1 = ttk.Frame(card1)
row1.pack(fill=X)

hotkey_label = ttk.Label(row1, text=current_lang["hotkey"])
hotkey_label.pack(side=LEFT)

hotkey_entry = ttk.Entry(row1, width=16)
hotkey_entry.pack(side=LEFT, padx=10)
hotkey_entry.insert(0, _format_hotkey_text())

detect_btn = ttk.Button(row1, text=current_lang["detect"], bootstyle="primary", command=start_capture_hotkey)
detect_btn.pack(side=LEFT)

tip_label = ttk.Label(card1, text=current_lang["tip_hotkey"], bootstyle="secondary")
tip_label.pack(anchor=W, pady=(8, 0))

hotkey_info_var = ttk.StringVar(value="")
hotkey_info_label = ttk.Label(card1, textvariable=hotkey_info_var, bootstyle="info")
hotkey_info_label.pack(anchor=W, pady=(8, 0))

# Card 2: Settings
card2 = ttk.Labelframe(container, text=current_lang["card_settings"], padding=14, bootstyle="secondary")
card2.pack(fill=BOTH, expand=True)

grid = ttk.Frame(card2)
grid.pack(fill=BOTH, expand=True)
grid.grid_columnconfigure(0, weight=0)
grid.grid_columnconfigure(1, weight=1)
grid.grid_columnconfigure(2, weight=0)
grid.grid_columnconfigure(3, weight=1)

# Output (ONLY TWO)
output_label = ttk.Label(grid, text=current_lang["output"])
output_label.grid(row=0, column=0, sticky=W, pady=(0, 6))

output_var = ttk.StringVar(value=output_choice)

output_f_rb = ttk.Radiobutton(
    grid, text=current_lang["output_f"], variable=output_var, value="F",
    command=lambda: (apply_all_settings(), schedule_save()),
    bootstyle="info-toolbutton"
)
output_f_rb.grid(row=0, column=1, sticky=W, padx=(10, 2))

output_left_rb = ttk.Radiobutton(
    grid, text=current_lang["output_left"], variable=output_var, value="MOUSE_LEFT",
    command=lambda: (apply_all_settings(), schedule_save()),
    bootstyle="info-toolbutton"
)
output_left_rb.grid(row=0, column=2, sticky=W, padx=(2, 0))

# Mode
mode_label = ttk.Label(grid, text=current_lang["mode"])
mode_label.grid(row=1, column=0, sticky=W, pady=10)

mode_var = ttk.StringVar(
    value=_loaded_settings.get("mode", "toggle")
    if _loaded_settings.get("mode") in ("toggle", "hold") else "toggle"
)

toggle_rb = ttk.Radiobutton(grid, text=current_lang["toggle"], variable=mode_var, value="toggle",
                            command=on_mode_change, bootstyle="success-toolbutton")
toggle_rb.grid(row=1, column=1, sticky=W, padx=(10, 2))

hold_rb = ttk.Radiobutton(grid, text=current_lang["hold"], variable=mode_var, value="hold",
                          command=on_mode_change, bootstyle="warning-toolbutton")
hold_rb.grid(row=1, column=2, sticky=W, padx=(2, 0))

# CPS
speed_label = ttk.Label(grid, text=current_lang["speed"])
speed_label.grid(row=2, column=0, sticky=W, pady=10)

cps_var = ttk.StringVar(value=str(int(_loaded_settings.get("cps", 100))))
cps_combo = ttk.Combobox(
    grid, textvariable=cps_var, width=10,
    values=["10", "20", "30", "40", "50", "75", "100", "150", "200", "250", "300"],
    state="readonly"
)
cps_combo.grid(row=2, column=1, sticky=W, padx=10)
cps_combo.bind("<<ComboboxSelected>>", apply_all_settings)
ttk.Label(grid, text="CPS", bootstyle="secondary").grid(row=2, column=2, sticky=W)

# Jitter
jitter_var = ttk.BooleanVar(value=bool(_loaded_settings.get("jitter_on", jitter_on)))
jitter_pct_var = ttk.DoubleVar(value=float(_loaded_settings.get("jitter_pct", jitter_pct)))
micro_pause_var = ttk.BooleanVar(value=bool(_loaded_settings.get("micro_pause_on", micro_pause_on)))

def _fmt_pct():
    try:
        return f"{int(float(jitter_pct_var.get()) * 100)}%"
    except:
        return "0%"

def on_jitter_change(*_):
    global running
    running = False
    pressed_keys.clear()
    try:
        jitter_value_label.configure(text=_fmt_pct())
    except:
        pass
    _refresh_permission_status()
    schedule_save()

jitter_label = ttk.Label(grid, text="Humanize (Jitter)")
jitter_label.grid(row=3, column=0, sticky=W, pady=(6, 0))

jitter_chk = ttk.Checkbutton(grid, text="ON / OFF", variable=jitter_var,
                             command=on_jitter_change, bootstyle="round-toggle")
jitter_chk.grid(row=3, column=1, sticky=W, padx=(10, 0), pady=(6, 0))

jitter_amt_label = ttk.Label(grid, text="Jitter Amount", bootstyle="secondary")
jitter_amt_label.grid(row=4, column=0, sticky=W, pady=(6, 0))

jitter_scale = ttk.Scale(grid, from_=0.0, to=0.30, variable=jitter_pct_var, command=lambda v: on_jitter_change())
jitter_scale.grid(row=4, column=1, sticky="ew", padx=(10, 10), pady=(6, 0))

jitter_value_label = ttk.Label(grid, text=_fmt_pct(), bootstyle="info")
jitter_value_label.grid(row=4, column=2, sticky=W, pady=(6, 0))

micro_pause_chk = ttk.Checkbutton(grid, text="Micro Pause", variable=micro_pause_var,
                                  command=on_jitter_change, bootstyle="secondary")
micro_pause_chk.grid(row=4, column=3, sticky=W, pady=(6, 0))

ttk.Separator(container).pack(fill=X, pady=14)

# Footer
footer = ttk.Frame(container)
footer.pack(fill=X)

status_var = ttk.StringVar(value=current_lang["status_wait"])
status_badge = ttk.Label(footer, textvariable=status_var, bootstyle="secondary", padding=(10, 6))
status_badge.pack(side=LEFT)

right_box = ttk.Frame(footer)
right_box.pack(side=RIGHT)

mac_perm_btn = ttk.Button(
    right_box,
    text=current_lang["mac_perm"],
    bootstyle="secondary",
    command=lambda: show_macos_permission_help() if _is_macos() else messagebox.showinfo("Info", "This button is for macOS permissions.")
)
mac_perm_btn.pack(side=RIGHT, padx=(8, 0))

retry_btn = ttk.Button(right_box, text=current_lang["retry"], bootstyle="primary", command=retry_listeners)
retry_btn.pack(side=RIGHT, padx=(8, 0))

lang_title = ttk.Label(right_box, text=current_lang["language"], bootstyle="secondary")
lang_title.pack(side=RIGHT, padx=(0, 8))

lang_var = ttk.StringVar(
    value=_loaded_settings.get("lang", "English")
    if _loaded_settings.get("lang") in ("English", "繁體中文", "한국어") else "English"
)
lang_menu = ttk.Combobox(right_box, textvariable=lang_var, values=["English", "繁體中文", "한국어"], width=12, state="readonly")
lang_menu.pack(side=RIGHT)
lang_menu.bind("<<ComboboxSelected>>", lambda e: update_language())

# ======================
# Navigation (logo/lang/main)
# ======================
def go_main_direct():
    show_frame(main_frame)
    update_language()
    apply_theme()
    apply_all_settings()
    update_hotkey_info()
    check_self_trigger_warning()
    start_listeners()
    _refresh_permission_status()
    schedule_save()

def go_language_picker():
    show_frame(lang_frame)
    root.after(0, draw_lang_card)

def after_logo():
    has_lang = bool(_loaded_settings.get("lang"))
    def swap():
        if has_lang:
            go_main_direct()
        else:
            go_language_picker()
        fade_to(1.0)
    fade_to(0.0, on_done=swap)

def go_main_with_language(lang_choice: str):
    lang_var.set(lang_choice)
    schedule_save()
    def swap():
        go_main_direct()
        fade_to(1.0)
    fade_to(0.0, on_done=swap)

# ======================
# Close handler
# ======================
def on_close():
    global running, fullscreen
    running = False
    fullscreen = False
    try:
        root.attributes("-fullscreen", False)
    except:
        pass
    try:
        write_settings_now()
    except:
        pass
    try:
        stop_listeners()
    except:
        pass
    try:
        root.destroy()
    except:
        pass

root.protocol("WM_DELETE_WINDOW", on_close)

# ======================
# Start up
# ======================
root.after(0, lambda: apply_scale(min(root.winfo_width() / BASE_W, root.winfo_height() / BASE_H)))

show_frame(logo_frame)
root.after(LOGO_SECONDS * 1000, after_logo)

threading.Thread(target=autoclicker_thread, daemon=True).start()

root.after(
    0,
    lambda: (
        update_language(),
        apply_theme(),
        apply_all_settings(),
        update_hotkey_info(),
        check_self_trigger_warning(),
        on_jitter_change(),
        start_listeners(),
        _refresh_permission_status(),
        schedule_save()
    )
)

root.mainloop()
