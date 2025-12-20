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
selected_cps = 100
output_key = "f"
keyboard_controller = keyboard.Controller()

hotkey_kind = "keyboard"      # "keyboard" or "mouse"
hotkey_type = "char"          # "char" or "special"
hotkey_char = "f"
hotkey_special = keyboard.Key.f1
hotkey_mouse_btn = mouse.Button.x1

kb_listener = None
ms_listener = None

capture_mode = False
pressed_keys = set()

LOCK_HOLD = "HOLD_LOCK"
LOCK_TOGGLE = "TOGGLE_LOCK"
LOCK_MOUSE_TOGGLE = "MOUSE_TOGGLE_LOCK"

fullscreen = False

# Listener / permission status
listeners_ok = True
listener_error_text = ""
inject_ok = True
inject_error_text = ""

# ======================
# Languages
# ======================
LANG_EN = {
    "title": "W1te Auto Clicker PRO",
    "subtitle": "Hotkey / Mouse Side Button • Toggle / Hold • CPS",
    "card_hotkey": " HOTKEY ",
    "card_settings": " SETTINGS ",
    "hotkey": "Hotkey",
    "detect": "Detect",
    "mode": "Mode",
    "speed": "Speed (CPS)",
    "toggle": "Toggle",
    "hold": "Hold",
    "status_wait": "Waiting",
    "status_detect": "Detecting: press a key / mouse button once",
    "status_run": "Clicking",
    "status_stop": "Stopped",
    "hotkey_now": "Current hotkey:",
    "tip_hotkey": "Type: a / 1 / … or F1–F9 or XBUTTON1 / XBUTTON2",
    "theme": "Theme",
    "light": "Light",
    "dark": "Dark",
    "language": "Language",
    "warn_same_key": "⚠ Hotkey equals output key. Please use a different hotkey (e.g., F1).",

    # Added
    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ Hotkey/Mouse listener blocked. Enable macOS permissions and press Retry.",
    "perm_warn_inject": "⚠ Key output blocked. Enable macOS permissions.",
    "perm_help_title": "macOS Permissions",
}

LANG_ZH = {
    "title": "W1te 自動連點工具 PRO",
    "subtitle": "熱鍵 / 滑鼠側鍵 • 開關/按壓 • CPS",
    "card_hotkey": " 熱鍵 ",
    "card_settings": " 設定 ",
    "hotkey": "啟動熱鍵",
    "detect": "偵測",
    "mode": "模式",
    "speed": "速度 (CPS)",
    "toggle": "開關式",
    "hold": "按壓式",
    "status_wait": "等待設定",
    "status_detect": "偵測中：請按下你要的鍵或滑鼠鍵",
    "status_run": "連點中",
    "status_stop": "已停止",
    "hotkey_now": "目前熱鍵：",
    "tip_hotkey": "可輸入：a / 1 / … 或 F1～F9 或 XBUTTON1 / XBUTTON2",
    "theme": "主題",
    "light": "白",
    "dark": "黑",
    "language": "語言",
    "warn_same_key": "⚠ 熱鍵與輸出鍵相同，可能自觸發。請換別的熱鍵（例如 F1）。",

    # Added
    "retry": "重試",
    "mac_perm": "macOS 權限",
    "perm_warn_listener": "⚠ 熱鍵/滑鼠監聽被擋住。請開啟 macOS 權限後按「重試」。",
    "perm_warn_inject": "⚠ 輸出按鍵被擋住。請開啟 macOS 權限。",
    "perm_help_title": "macOS 權限",
}

LANG_KR = {
    "title": "W1te 오토 클릭커 PRO",
    "subtitle": "핫키 / 마우스 사이드 버튼 • 토글/홀드 • CPS",
    "card_hotkey": " 핫키 ",
    "card_settings": " 설정 ",
    "hotkey": "시작 키",
    "detect": "감지",
    "mode": "모드",
    "speed": "속도 (CPS)",
    "toggle": "토글식",
    "hold": "홀드식",
    "status_wait": "대기",
    "status_detect": "감지 중: 키/마우스를 한 번 누르세요",
    "status_run": "클릭 중",
    "status_stop": "정지됨",
    "hotkey_now": "현재 핫키:",
    "tip_hotkey": "입력: a / 1 / … 또는 F1~F9 또는 XBUTTON1 / XBUTTON2",
    "theme": "테마",
    "light": "라이트",
    "dark": "다크",
    "language": "언어",
    "warn_same_key": "⚠ 핫키가 출력 키와 같아요. 다른 핫키로 바꿔주세요 (예: F1).",

    # Added
    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ 리스너가 차단됨. macOS 권한을 켜고 Retry 누르세요.",
    "perm_warn_inject": "⚠ 키 출력이 차단됨. macOS 권한을 켜세요.",
    "perm_help_title": "macOS Permissions",
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

def _mouse_btn_to_str(btn):
    if btn == mouse.Button.x1:
        return "x1"
    if btn == mouse.Button.x2:
        return "x2"
    return str(btn)

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

    try:
        hotkey_text = hotkey_entry.get().strip()
    except:
        hotkey_text = _loaded_settings.get("hotkey_text", "F1")

    lang_default = _loaded_settings.get("lang", "English")
    theme_default = bool(_loaded_settings.get("theme_dark", False))
    mode_default = _loaded_settings.get("mode", "toggle")
    cps_default = str(_loaded_settings.get("cps", "100"))

    data = {
        "lang": _safe_get(globals().get("lang_var"), lang_default),
        "theme_dark": bool(_safe_get(globals().get("theme_var"), theme_default)),
        "mode": _safe_get(globals().get("mode_var"), mode_default),
        "cps": str(_safe_get(globals().get("cps_var"), cps_default)),
        "hotkey_text": hotkey_text,

        "hotkey_kind": hotkey_kind,
        "hotkey_type": hotkey_type,
        "hotkey_char": hotkey_char,
        "hotkey_special": str(hotkey_special).replace("Key.", ""),
        "hotkey_mouse_btn": _mouse_btn_to_str(hotkey_mouse_btn),

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

def update_hotkey_info():
    if hotkey_kind == "mouse":
        if hotkey_mouse_btn == mouse.Button.x1:
            txt = f"{current_lang['hotkey_now']} Mouse XBUTTON1"
        elif hotkey_mouse_btn == mouse.Button.x2:
            txt = f"{current_lang['hotkey_now']} Mouse XBUTTON2"
        else:
            txt = f"{current_lang['hotkey_now']} Mouse {hotkey_mouse_btn}"
    else:
        if hotkey_type == "char":
            txt = f"{current_lang['hotkey_now']} Keyboard '{hotkey_char.upper()}'"
        else:
            name = str(hotkey_special).replace("Key.", "").upper()
            txt = f"{current_lang['hotkey_now']} Keyboard {name}"

    def _():
        hotkey_info_var.set(txt)
    ui(_)

def check_self_trigger_warning():
    conflict = (hotkey_kind == "keyboard" and hotkey_type == "char"
                and hotkey_char.lower() == output_key.lower())
    if conflict and (not capture_mode) and (not running):
        set_status(current_lang["warn_same_key"], "warning")

def _is_macos():
    return platform.system().lower() == "darwin"

def show_macos_permission_help():
    # macOS: 通常需要「輔助使用(Accessibility)」+「輸入監控(Input Monitoring)」
    msg = (
        "macOS 需要允許權限，否則會造成：\n"
        "• 熱鍵/滑鼠側鍵偵測無效（看起來像壞掉）\n"
        "• 輸出按鍵被擋住（不會真的在遊戲/應用裡觸發）\n\n"
        "請到：\n"
        "系統設定 → 隱私權與安全性 →\n"
        "✅ 輔助使用 (Accessibility)\n"
        "✅ 輸入監控 (Input Monitoring)\n\n"
        "如果你用 Terminal 跑：允許 Terminal\n"
        "如果你打包成 App：允許你的 App\n\n"
        "開完後回到程式按「重試」。"
    )
    messagebox.showinfo(current_lang["perm_help_title"], msg)

def _refresh_permission_status():
    # 依照目前狀態決定 status bar 顯示
    if _is_macos():
        # 監聽不行優先提示（因為你會以為熱鍵壞掉）
        if not listeners_ok:
            set_status(current_lang["perm_warn_listener"], "warning")
            return
        # 輸出不行也要提示（你會以為連點壞掉）
        if not inject_ok:
            set_status(current_lang["perm_warn_inject"], "warning")
            return

    # 正常狀態回到原本邏輯
    if capture_mode:
        set_status(current_lang["status_detect"], "warning")
    elif running:
        set_status(current_lang["status_run"], "success")
    else:
        set_status(current_lang["status_wait"], "secondary")

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

    theme_btn.configure(text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})")
    lang_title.configure(text=current_lang["language"])

    # Footer buttons text
    try:
        retry_btn.configure(text=current_lang["retry"])
        mac_perm_btn.configure(text=current_lang["mac_perm"])
    except:
        pass

    update_hotkey_info()
    check_self_trigger_warning()
    _refresh_permission_status()
    schedule_save()

# ======================
# Click Thread
# ======================
def autoclicker_thread():
    global running, selected_cps, inject_ok, inject_error_text
    while True:
        if running:
            try:
                keyboard_controller.press(output_key)
                keyboard_controller.release(output_key)
                inject_ok = True
                inject_error_text = ""
            except Exception as e:
                # macOS 權限不足時，這裡很常直接失敗
                inject_ok = False
                inject_error_text = str(e)[:250]
                running = False
                _refresh_permission_status()

            # sleep
            try:
                cps = max(1, int(selected_cps))
            except:
                cps = 100
            time.sleep(1 / cps)
        else:
            time.sleep(0.05)

# ======================
# Hotkey Setters
# ======================
def set_hotkey_keyboard_char(ch: str):
    global hotkey_kind, hotkey_type, hotkey_char, running, capture_mode
    hotkey_kind = "keyboard"
    hotkey_type = "char"
    hotkey_char = (ch or "f").lower()[:1]
    running = False
    capture_mode = False
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, hotkey_char)
        _refresh_permission_status()
        update_hotkey_info()
        check_self_trigger_warning()
        schedule_save()
    ui(_)

def set_hotkey_keyboard_special(key_obj):
    global hotkey_kind, hotkey_type, hotkey_special, running, capture_mode
    hotkey_kind = "keyboard"
    hotkey_type = "special"
    hotkey_special = key_obj
    running = False
    capture_mode = False
    pressed_keys.clear()

    txt = str(key_obj).replace("Key.", "").upper()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, txt)
        _refresh_permission_status()
        update_hotkey_info()
        schedule_save()
    ui(_)

def set_hotkey_mouse(btn):
    global hotkey_kind, hotkey_mouse_btn, running, capture_mode
    hotkey_kind = "mouse"
    hotkey_mouse_btn = btn
    running = False
    capture_mode = False
    pressed_keys.clear()

    if btn == mouse.Button.x1:
        txt = "XBUTTON1"
    elif btn == mouse.Button.x2:
        txt = "XBUTTON2"
    else:
        txt = str(btn).upper()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, txt)
        _refresh_permission_status()
        update_hotkey_info()
        schedule_save()
    ui(_)

# ======================
# Detect Mode
# ======================
def start_capture():
    global capture_mode, running
    running = False
    pressed_keys.clear()
    capture_mode = True
    _refresh_permission_status()

# ======================
# Apply Settings
# ======================
def apply_all_settings(event=None):
    global selected_cps, running
    running = False
    pressed_keys.clear()

    hk = hotkey_entry.get().strip()
    hkl = hk.lower()

    try:
        selected_cps = int(cps_var.get())
    except:
        selected_cps = 100
        cps_var.set("100")

    x1_alias = {"xbutton1", "xbottom1", "xbtn1", "x1", "mouse4", "mb4"}
    x2_alias = {"xbutton2", "xbottom2", "xbtn2", "x2", "mouse5", "mb5"}
    if hkl in x1_alias:
        set_hotkey_mouse(mouse.Button.x1)
        return
    if hkl in x2_alias:
        set_hotkey_mouse(mouse.Button.x2)
        return

    f_map = {
        "f1": keyboard.Key.f1, "f2": keyboard.Key.f2, "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4, "f5": keyboard.Key.f5, "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7, "f8": keyboard.Key.f8, "f9": keyboard.Key.f9,
    }
    if hkl in f_map:
        set_hotkey_keyboard_special(f_map[hkl])
        return

    if len(hkl) >= 1:
        set_hotkey_keyboard_char(hkl[0])
    else:
        set_hotkey_keyboard_char("f")

    schedule_save()

def on_mode_change():
    global running
    running = False
    pressed_keys.clear()
    _refresh_permission_status()
    schedule_save()

def is_hotkey_pressed(key):
    if hotkey_kind != "keyboard":
        return False
    if hotkey_type == "char":
        try:
            return key.char and key.char.lower() == hotkey_char
        except:
            return False
    else:
        return key == hotkey_special

# ======================
# Keyboard / Mouse Listeners
# ======================
def on_press(key):
    global running, capture_mode

    if not listeners_ok:
        return

    if capture_mode:
        if key in {
            keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3,
            keyboard.Key.f4, keyboard.Key.f5, keyboard.Key.f6,
            keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9
        }:
            set_hotkey_keyboard_special(key)
            return
        try:
            ch = key.char
        except:
            return
        if ch:
            set_hotkey_keyboard_char(ch)
        return

    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "hold":
        if is_hotkey_pressed(key):
            if LOCK_HOLD in pressed_keys:
                return
            pressed_keys.add(LOCK_HOLD)
            running = True
            _refresh_permission_status()
        return

    if mode_var.get() == "toggle":
        if is_hotkey_pressed(key):
            if LOCK_TOGGLE in pressed_keys:
                return
            pressed_keys.add(LOCK_TOGGLE)
            running = not running
            _refresh_permission_status()

def on_release(key):
    global running
    if not listeners_ok:
        return
    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "toggle":
        if is_hotkey_pressed(key):
            pressed_keys.discard(LOCK_TOGGLE)
        return

    if mode_var.get() == "hold":
        if is_hotkey_pressed(key):
            pressed_keys.discard(LOCK_HOLD)
            running = False
            _refresh_permission_status()

def on_click(x, y, button, pressed):
    global running, capture_mode

    if not listeners_ok:
        return

    if capture_mode and pressed:
        set_hotkey_mouse(button)
        return

    if hotkey_kind != "mouse":
        return
    if button != hotkey_mouse_btn:
        return

    if mode_var.get() == "hold":
        if pressed:
            running = True
        else:
            running = False
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
    """
    ✅ 整合：macOS 權限不足時，至少在狀態列顯示提示
    """
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

    _refresh_permission_status()

def retry_listeners():
    start_listeners()
    # 同步刷新顯示（避免你按了重試但文字沒變）
    update_language()

# ======================
# Rounded shapes (Canvas)
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
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
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

        _round_rect(
            self,
            pad, pad, w - pad, h - pad,
            r=min(self.radius, int(h * 0.35)),
            fill=fill,
            outline=self.outline,
            width=2
        )

        self.create_text(
            w / 2, h * 0.42,
            text=self.title,
            fill=self.text_color,
            font=("Segoe UI", 16, "bold")
        )
        self.create_text(
            w / 2, h * 0.72,
            text=self.desc,
            fill=self.text_color,
            font=("Segoe UI", 10)
        )

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

def go_main_direct():
    show_frame(main_frame)
    update_language()
    apply_theme()
    apply_all_settings()
    update_hotkey_info()
    start_listeners()            # ✅ 整合：帶 try/except 的 listener 啟動
    _refresh_permission_status() # ✅ 整合：mac 權限提示
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

root = ttk.Window(
    title=APP_NAME,
    themename=LIGHT_THEME,
    size=(default_w, default_h)
)
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
logo_label = tk.Label(
    logo_frame,
    text="w1te macro",
    bg="white",
    fg="black",
    font=("Segoe UI", 40, "bold")
)
logo_label.place(relx=0.5, rely=0.5, anchor="center")

# ---------- Frame 1: Language Picker (你的版本：rounded card + rounded big buttons) ----------
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

    btn = RoundLangButton(
        wrap,
        title=title,
        desc=desc,
        command=lambda: go_main_with_language(choice),
        width=240,
        height=86
    )
    btn.grid(row=0, column=0, sticky="ew")
    lang_btns[key] = btn

make_lang_round(0, "zh", "繁體中文", "台灣 / 繁中介面", "繁體中文")
make_lang_round(1, "en", "English", "Default / International", "English")
make_lang_round(2, "kr", "한국어", "한국어 UI", "한국어")

ttk.Label(lang_content, text="Tip: You can change language later in settings.", bootstyle="secondary").pack(pady=(18, 0))

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
container = ttk.Frame(main_frame, padding=18)
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

def apply_theme():
    theme = DARK_THEME if theme_var.get() else LIGHT_THEME
    root.style.theme_use(theme)
    try:
        if lang_frame.winfo_ismapped():
            draw_lang_card()
        else:
            _update_lang_btn_colors()
    except:
        pass
    schedule_save()

theme_btn = ttk.Checkbutton(
    theme_row,
    text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})",
    variable=theme_var,
    command=apply_theme,
    bootstyle="round-toggle"
)
theme_btn.pack(anchor=E)

ttk.Separator(container).pack(fill=X, pady=14)

card1 = ttk.Labelframe(container, text=current_lang["card_hotkey"], padding=14, bootstyle="primary")
card1.pack(fill=X, pady=(0, 12))

row1 = ttk.Frame(card1)
row1.pack(fill=X)

hotkey_label = ttk.Label(row1, text=current_lang["hotkey"])
hotkey_label.pack(side=LEFT)

hotkey_entry = ttk.Entry(row1, width=16)
hotkey_entry.pack(side=LEFT, padx=10)

detect_btn = ttk.Button(row1, text=current_lang["detect"], bootstyle="primary", command=start_capture)
detect_btn.pack(side=LEFT)

tip_label = ttk.Label(card1, text=current_lang["tip_hotkey"], bootstyle="secondary")
tip_label.pack(anchor=W, pady=(8, 0))

hotkey_info_var = ttk.StringVar(value="")
hotkey_info_label = ttk.Label(card1, textvariable=hotkey_info_var, bootstyle="info")
hotkey_info_label.pack(anchor=W, pady=(8, 0))

card2 = ttk.Labelframe(container, text=current_lang["card_settings"], padding=14, bootstyle="secondary")
card2.pack(fill=BOTH, expand=True)

grid = ttk.Frame(card2)
grid.pack(fill=BOTH, expand=True)

mode_label = ttk.Label(grid, text=current_lang["mode"])
mode_label.grid(row=0, column=0, sticky=W, pady=6)

mode_var = ttk.StringVar(
    value=_loaded_settings.get("mode", "toggle")
    if _loaded_settings.get("mode") in ("toggle", "hold") else "toggle"
)

toggle_rb = ttk.Radiobutton(
    grid, text=current_lang["toggle"], variable=mode_var, value="toggle",
    command=on_mode_change, bootstyle="success-toolbutton"
)
toggle_rb.grid(row=0, column=1, sticky=W, padx=10)

hold_rb = ttk.Radiobutton(
    grid, text=current_lang["hold"], variable=mode_var, value="hold",
    command=on_mode_change, bootstyle="warning-toolbutton"
)
hold_rb.grid(row=0, column=2, sticky=W)

speed_label = ttk.Label(grid, text=current_lang["speed"])
speed_label.grid(row=1, column=0, sticky=W, pady=10)

cps_var = ttk.StringVar(value=str(_loaded_settings.get("cps", "100")))
cps_combo = ttk.Combobox(
    grid,
    textvariable=cps_var,
    width=10,
    values=["10", "20", "30", "40", "50", "100", "150", "200", "250", "300", "350", "450", "500"]
)
cps_combo.grid(row=1, column=1, sticky=W, padx=10)
cps_combo.bind("<<ComboboxSelected>>", apply_all_settings)

ttk.Label(grid, text="CPS", bootstyle="secondary").grid(row=1, column=2, sticky=W)

ttk.Separator(container).pack(fill=X, pady=14)

footer = ttk.Frame(container)
footer.pack(fill=X)

status_var = ttk.StringVar(value=current_lang["status_wait"])
status_badge = ttk.Label(footer, textvariable=status_var, bootstyle="secondary", padding=(10, 6))
status_badge.pack(side=LEFT)

# ✅ 右側：macOS 權限 / 重試 / 語言
right_box = ttk.Frame(footer)
right_box.pack(side=RIGHT)

mac_perm_btn = ttk.Button(
    right_box,
    text=current_lang["mac_perm"],
    bootstyle="secondary",
    command=lambda: show_macos_permission_help() if _is_macos() else messagebox.showinfo("Info", "This button is for macOS permissions.")
)
mac_perm_btn.pack(side=RIGHT, padx=(8, 0))

retry_btn = ttk.Button(
    right_box,
    text=current_lang["retry"],
    bootstyle="primary",
    command=retry_listeners
)
retry_btn.pack(side=RIGHT, padx=(8, 0))

lang_title = ttk.Label(right_box, text=current_lang["language"], bootstyle="secondary")
lang_title.pack(side=RIGHT, padx=(0, 8))

lang_var = ttk.StringVar(value=_loaded_settings.get("lang", "English") if _loaded_settings.get("lang") in ("English", "繁體中文", "한국어") else "English")
lang_menu = ttk.Combobox(right_box, textvariable=lang_var, values=["English", "繁體中文", "한국어"], width=12)
lang_menu.pack(side=RIGHT)
lang_menu.bind("<<ComboboxSelected>>", lambda e: update_language())

hotkey_entry.insert(0, str(_loaded_settings.get("hotkey_text", "F1")))
hotkey_entry.bind("<KeyRelease>", apply_all_settings)

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

# 先跑一次：避免第一次進主畫面時狀態不對
root.after(0, lambda: (update_language(), apply_theme(), apply_all_settings(), update_hotkey_info(), check_self_trigger_warning()))

root.mainloop()
