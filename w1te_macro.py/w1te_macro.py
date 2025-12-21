# ===== macOS PyInstaller matplotlib SIGTRAP fix =====
import os
import sys
import platform

def _fix_mpl_cache():
    if platform.system().lower() != "darwin":
        return
    try:
        base = os.path.dirname(sys.argv[0])
        cache_dir = os.path.join(base, ".mplcache")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = cache_dir
    except Exception as e:
        print("MPL cache fix failed:", e)

_fix_mpl_cache()
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pynput import keyboard, mouse

# ===== Mouse button compatibility (macOS safe) =====
def get_mouse_button(name: str, fallback="left"):
    """
    name: 'left'/'right'/'middle'/'x1'/'x2'
    If x1/x2 not supported on this OS/pynput build, fallback to left/right/middle.
    """
    name = (name or "").lower()

    # Some platforms don't have x1/x2 at all
    if name in ("x1", "x2") and not hasattr(mouse.Button, name):
        name = fallback

    return getattr(mouse.Button, name, getattr(mouse.Button, fallback, mouse.Button.left))

import threading
import time
import tkinter.font as tkfont
import json
import os
import sys
import platform
import random

# ===== matplotlib for curve (optional) =====
MPL_OK = True
MPL_ERR = ""
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception as e:
    MPL_OK = False
    MPL_ERR = str(e)

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

# Hotkey storage
hotkey_kind = _loaded_settings.get("hotkey_kind", "keyboard")      # "keyboard" or "mouse"
hotkey_type = _loaded_settings.get("hotkey_type", "special")      # "char" or "special"
hotkey_char = str(_loaded_settings.get("hotkey_char", "f")).lower()[:1]
_hotkey_special_name = str(_loaded_settings.get("hotkey_special", "f1")).lower()
hotkey_special = getattr(keyboard.Key, _hotkey_special_name, keyboard.Key.f1)

# Hotkey mouse button (fallback to left if missing)
_hotkey_mouse = str(_loaded_settings.get("hotkey_mouse_btn", "x1")).lower()
hotkey_mouse_btn = get_mouse_button(_hotkey_mouse, fallback="left")

# ✅ Output storage（你原貼的版本缺這段，gather_settings 會炸）
output_kind = _loaded_settings.get("output_kind", "keyboard")      # "keyboard" or "mouse"
output_type = _loaded_settings.get("output_type", "char")         # "char" or "special"
output_char = str(_loaded_settings.get("output_char", "f")).lower()[:1]
_output_special_name = str(_loaded_settings.get("output_special", "f")).lower()
output_special = getattr(keyboard.Key, _output_special_name, keyboard.Key.f1 if _output_special_name == "f1" else keyboard.Key.f1)

# Output mouse button (fallback to left if missing)
_output_mouse = str(_loaded_settings.get("output_mouse_btn", "left")).lower()
output_mouse_btn = get_mouse_button(_output_mouse, fallback="left")

# ✅ Humanize / Jitter (persisted)
jitter_on = bool(_loaded_settings.get("jitter_on", False))
try:
    jitter_pct = float(_loaded_settings.get("jitter_pct", 0.12))
except:
    jitter_pct = 0.12
micro_pause_on = bool(_loaded_settings.get("micro_pause_on", True))

kb_listener = None
ms_listener = None

# capture target: None / "hotkey" / "output"
capture_target = None
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
# CPS Test State  (COUNT EMITTED OUTPUT)
# ======================
TEST_BIN = 0.10  # 100ms bins
test_duration = 10
test_running = False
test_start_t = 0.0

# ✅ 記錄「巨集實際輸出」的時間點（不靠偵測你按什麼鍵）
test_emit_times = []
test_lock = threading.Lock()

test_bins_t = []
test_bins_cps = []
test_avg_line = []

# (舊版 listener 兼容：保留空函式，避免你其他地方 call 了會噴錯)
def stop_test_listeners():
    pass

def start_test_listeners():
    pass

def record_test_emit():
    """✅ Record one emitted output event for CPS test."""
    global test_emit_times
    if not test_running:
        return
    t = time.perf_counter() - test_start_t
    if t < 0:
        return
    with test_lock:
        test_emit_times.append(t)

# ======================
# Languages
# ======================
LANG_EN = {
    "title": "W1te Auto Clicker PRO",
    "subtitle": "Hotkey / Mouse Side Button • Toggle / Hold • CPS • Output Key",
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
    "status_detect_output": "Detecting OUTPUT: press a key / mouse button once",
    "status_run": "Clicking",
    "status_stop": "Stopped",
    "hotkey_now": "Current hotkey:",
    "tip_hotkey": "Type: a / 1 / … or F1–F9 or XBUTTON1 / XBUTTON2",
    "theme": "Theme",
    "light": "Light",
    "dark": "Dark",
    "language": "Language",
    "warn_same_key": "⚠ Hotkey equals output key. Please use a different hotkey (e.g., F1).",

    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ Hotkey/Mouse listener blocked. Enable macOS permissions and press Retry.",
    "perm_warn_inject": "⚠ Key output blocked. Enable macOS permissions.",
    "perm_help_title": "macOS Permissions",

    "output_key": "Output Key",
    "output_now": "Current output:",
    "tip_output": "Supports: chars / F1–F9 / mouse buttons (left/right/middle/XBUTTON1/2)",

    # Jitter
    "jitter": "Humanize (Jitter)",
    "jitter_amt": "Jitter Amount",
    "jitter_tip": "Adds random delay variance to feel more natural.",
    "on_off": "ON / OFF",
    "micro_pause": "Micro Pause",

    # CPS Test
    "cps_test": "CPS Test",
    "cps_test_desc": "Test your real clicking speed",
    "choose_time": "Choose duration",
    "sec_5": "5 seconds",
    "sec_10": "10 seconds",
    "sec_15": "15 seconds",
    "start_test": "Start Test",
    "click_block": "CLICK THIS AREA",
    "time_left": "Time left",
    "result_title": "Time's up",
    "result_msg": "Your test is complete.",
    "avg_cps": "Average CPS",
    "total_clicks": "Total Clicks",
    "max_cps": "Max CPS (bin)",
    "stability": "Stability",
    "back_settings": "Back to Settings",
    "test_again": "Test Again",
    "mpl_missing": "CPS test requires matplotlib.\nInstall: pip install matplotlib",
}

LANG_ZH = {
    "title": "W1te 自動連點工具 PRO",
    "subtitle": "熱鍵 / 滑鼠側鍵 • 開關/按壓 • CPS • 輸出鍵",
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
    "status_detect_output": "偵測輸出鍵中：請按下你要輸出的鍵或滑鼠鍵一次",
    "status_run": "連點中",
    "status_stop": "已停止",
    "hotkey_now": "目前熱鍵：",
    "tip_hotkey": "可輸入：a / 1 / … 或 F1～F9 或 XBUTTON1 / XBUTTON2",
    "theme": "主題",
    "light": "白",
    "dark": "黑",
    "language": "語言",
    "warn_same_key": "⚠ 熱鍵與輸出鍵相同，可能自觸發。請換別的熱鍵（例如 F1）。",

    "retry": "重試",
    "mac_perm": "macOS 權限",
    "perm_warn_listener": "⚠ 熱鍵/滑鼠監聽被擋住。請開啟 macOS 權限後按「重試」。",
    "perm_warn_inject": "⚠ 輸出按鍵被擋住。請開啟 macOS 權限。",
    "perm_help_title": "macOS 權限",

    "output_key": "輸出鍵",
    "output_now": "目前輸出：",
    "tip_output": "支援：字母/數字、F1～F9、滑鼠鍵(左/右/中/XBUTTON1/2)",

    # Jitter
    "jitter": "人性化抖動",
    "jitter_amt": "抖動幅度",
    "jitter_tip": "讓每次間隔有隨機浮動，更像真人點擊。",
    "on_off": "開 / 關",
    "micro_pause": "偶爾小停頓",

    # CPS Test
    "cps_test": "CPS 測試",
    "cps_test_desc": "測你真實手速",
    "choose_time": "選擇時間長度",
    "sec_5": "5 秒",
    "sec_10": "10 秒",
    "sec_15": "15 秒",
    "start_test": "開始測試",
    "click_block": "點擊此區塊",
    "time_left": "剩餘時間",
    "result_title": "時間到",
    "result_msg": "測試已完成。",
    "avg_cps": "平均 CPS",
    "total_clicks": "總點擊數",
    "max_cps": "最高 CPS（區間）",
    "stability": "穩定度",
    "back_settings": "回到設定",
    "test_again": "再測一次",
    "mpl_missing": "CPS 測試需要 matplotlib。\n請安裝：pip install matplotlib",
}

LANG_KR = {
    "title": "W1te 오토 클릭커 PRO",
    "subtitle": "핫키 / 마우스 사이드 버튼 • 토글/홀드 • CPS • 출력 키",
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
    "status_detect_output": "출력 키 감지 중: 키/마우스를 한 번 누르세요",
    "status_run": "클릭 중",
    "status_stop": "정지됨",
    "hotkey_now": "현재 핫키:",
    "tip_hotkey": "입력: a / 1 / … 또는 F1~F9 또는 XBUTTON1 / XBUTTON2",
    "theme": "테마",
    "light": "라이트",
    "dark": "다크",
    "language": "언어",
    "warn_same_key": "⚠ 핫키가 출력 키와 같아요. 다른 핫키로 바꿔주세요 (예: F1).",

    "retry": "Retry",
    "mac_perm": "macOS Perm",
    "perm_warn_listener": "⚠ 리스너가 차단됨. macOS 권한을 켜고 Retry 누르세요.",
    "perm_warn_inject": "⚠ 키 출력이 차단됨. macOS 권한을 켜세요.",
    "perm_help_title": "macOS Permissions",

    "output_key": "출력 키",
    "output_now": "현재 출력:",
    "tip_output": "지원: 문자/ F1~F9 / 마우스 버튼(좌/우/중/XBUTTON1/2)",

    # Jitter
    "jitter": "휴먼라이즈(지터)",
    "jitter_amt": "지터 강도",
    "jitter_tip": "클릭 간격을 랜덤하게 흔들어 더 자연스럽게.",
    "on_off": "ON / OFF",
    "micro_pause": "Micro Pause",

    # CPS Test
    "cps_test": "CPS 테스트",
    "cps_test_desc": "실제 클릭 속도 측정",
    "choose_time": "시간 선택",
    "sec_5": "5초",
    "sec_10": "10초",
    "sec_15": "15초",
    "start_test": "테스트 시작",
    "click_block": "여기를 클릭하세요",
    "time_left": "남은 시간",
    "result_title": "시간 종료",
    "result_msg": "테스트가 완료되었습니다.",
    "avg_cps": "평균 CPS",
    "total_clicks": "총 클릭 수",
    "max_cps": "최대 CPS(구간)",
    "stability": "안정성",
    "back_settings": "설정으로",
    "test_again": "다시 테스트",
    "mpl_missing": "CPS 테스트는 matplotlib 필요.\nInstall: pip install matplotlib",
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
    """Canvas + inner Frame + right scrollbar + mousewheel."""
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

def _mouse_btn_to_str(btn):
    if btn == mouse.Button.left: return "left"
    if btn == mouse.Button.right: return "right"
    if btn == mouse.Button.middle: return "middle"
    # x1/x2 might not exist on mac; guard with hasattr
    if hasattr(mouse.Button, "x1") and btn == mouse.Button.x1: return "x1"
    if hasattr(mouse.Button, "x2") and btn == mouse.Button.x2: return "x2"
    return "left"

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

        "output_kind": output_kind,
        "output_type": output_type,
        "output_char": output_char,
        "output_special": str(output_special).replace("Key.", ""),
        "output_mouse_btn": _mouse_btn_to_str(output_mouse_btn),

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
        s = _mouse_btn_to_str(hotkey_mouse_btn).upper()
        if s == "X1": return "XBUTTON1"
        if s == "X2": return "XBUTTON2"
        return s
    else:
        if hotkey_type == "char":
            return hotkey_char.upper()
        return _key_to_display(hotkey_special)

def _format_output_text():
    if output_kind == "mouse":
        s = _mouse_btn_to_str(output_mouse_btn).upper()
        if s == "X1": s = "XBUTTON1"
        if s == "X2": s = "XBUTTON2"
        if s in ("LEFT", "RIGHT", "MIDDLE"):
            return f"MOUSE_{s}"
        return s
    else:
        if output_type == "char":
            return output_char.upper()
        return _key_to_display(output_special)

def update_hotkey_info():
    def _():
        hotkey_info_var.set(f"{current_lang['hotkey_now']} {_format_hotkey_text()}")
    ui(_)

def update_output_info():
    def _():
        output_info_var.set(f"{current_lang['output_now']} {_format_output_text()}")
    ui(_)

def check_self_trigger_warning():
    conflict = False
    if hotkey_kind == "keyboard" and output_kind == "keyboard":
        if hotkey_type == "char" and output_type == "char":
            conflict = hotkey_char.lower() == output_char.lower()
        elif hotkey_type == "special" and output_type == "special":
            conflict = hotkey_special == output_special
    if conflict and (not capture_target) and (not running):
        set_status(current_lang["warn_same_key"], "warning")

def _is_macos():
    return platform.system().lower() == "darwin"

def show_macos_permission_help():
    msg = (
        "macOS 需要允許權限，否則會造成：\n"
        "• 熱鍵/滑鼠側鍵偵測無效\n"
        "• 輸出按鍵被擋住\n\n"
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
    if _is_macos():
        if not listeners_ok:
            set_status(current_lang["perm_warn_listener"], "warning")
            return
        if not inject_ok:
            set_status(current_lang["perm_warn_inject"], "warning")
            return

    if capture_target == "hotkey":
        set_status(current_lang["status_detect_hotkey"], "warning")
    elif capture_target == "output":
        set_status(current_lang["status_detect_output"], "warning")
    elif running:
        set_status(current_lang["status_run"], "success")
    else:
        set_status(current_lang["status_wait"], "secondary")

# ======================
# Click Thread (Auto Clicker)
# ======================
def autoclicker_thread():
    global running, selected_cps, inject_ok, inject_error_text
    mouse_controller = mouse.Controller()
    keyboard_controller = keyboard.Controller()

    while True:
        if running:
            try:
                if output_kind == "mouse":
                    mouse_controller.click(output_mouse_btn)
                else:
                    if output_type == "char":
                        keyboard_controller.press(output_char)
                        keyboard_controller.release(output_char)
                    else:
                        keyboard_controller.press(output_special)
                        keyboard_controller.release(output_special)

                # ✅ CPS Test：統計「程式實際輸出」的次數
                record_test_emit()

                inject_ok = True
                inject_error_text = ""
            except Exception as e:
                inject_ok = False
                inject_error_text = str(e)[:250]
                running = False
                _refresh_permission_status()

            try:
                cps = max(1, int(selected_cps))
            except:
                cps = 100
            base = 1 / cps

            # humanize
            if jitter_on and jitter_pct > 0:
                factor = 1.0 + random.uniform(-jitter_pct, jitter_pct)
                delay = base * factor
            else:
                delay = base
            if jitter_on and micro_pause_on:
                if random.random() < 0.02:
                    delay += random.uniform(0.05, 0.14)

            time.sleep(max(0.001, delay))
        else:
            time.sleep(0.05)

# ======================
# Capture starters
# ======================
def start_capture_hotkey():
    global capture_target, running
    running = False
    pressed_keys.clear()
    capture_target = "hotkey"
    _refresh_permission_status()

def start_capture_output():
    global capture_target, running
    running = False
    pressed_keys.clear()
    capture_target = "output"
    _refresh_permission_status()

# ======================
# Set hotkey / output (from detected event)
# ======================
def set_hotkey_keyboard_char(ch: str):
    global hotkey_kind, hotkey_type, hotkey_char, running, capture_target
    hotkey_kind = "keyboard"
    hotkey_type = "char"
    hotkey_char = (ch or "f").lower()[:1]
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, hotkey_char.upper())
        _refresh_permission_status()
        update_hotkey_info()
        check_self_trigger_warning()
        schedule_save()
    ui(_)

def set_hotkey_keyboard_special(key_obj):
    global hotkey_kind, hotkey_type, hotkey_special, running, capture_target
    hotkey_kind = "keyboard"
    hotkey_type = "special"
    hotkey_special = key_obj
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, _key_to_display(key_obj))
        _refresh_permission_status()
        update_hotkey_info()
        schedule_save()
    ui(_)

def set_hotkey_mouse(btn):
    global hotkey_kind, hotkey_mouse_btn, running, capture_target
    hotkey_kind = "mouse"
    hotkey_mouse_btn = btn
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        hotkey_entry.delete(0, "end")
        hotkey_entry.insert(0, _format_hotkey_text())
        _refresh_permission_status()
        update_hotkey_info()
        schedule_save()
    ui(_)

def set_output_keyboard_char(ch: str):
    global output_kind, output_type, output_char, running, capture_target
    output_kind = "keyboard"
    output_type = "char"
    output_char = (ch or "f").lower()[:1]
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        update_output_info()
        _refresh_permission_status()
        check_self_trigger_warning()
        schedule_save()
    ui(_)

def set_output_keyboard_special(key_obj):
    global output_kind, output_type, output_special, running, capture_target
    output_kind = "keyboard"
    output_type = "special"
    output_special = key_obj
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        update_output_info()
        _refresh_permission_status()
        check_self_trigger_warning()
        schedule_save()
    ui(_)

def set_output_mouse(btn):
    global output_kind, output_mouse_btn, running, capture_target
    output_kind = "mouse"
    output_mouse_btn = btn
    running = False
    capture_target = None
    pressed_keys.clear()

    def _():
        update_output_info()
        _refresh_permission_status()
        check_self_trigger_warning()
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

    schedule_save()
    _refresh_permission_status()

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
    return key == hotkey_special

# ======================
# Keyboard / Mouse Listeners (Main)
# ======================
def on_press(key):
    global running, capture_target
    if not listeners_ok:
        return

    # Capture HOTKEY
    if capture_target == "hotkey":
        try:
            if key in {keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3, keyboard.Key.f4, keyboard.Key.f5,
                       keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9,
                       keyboard.Key.space, keyboard.Key.enter, keyboard.Key.shift,
                       keyboard.Key.ctrl, keyboard.Key.alt}:
                set_hotkey_keyboard_special(key); return
            ch = key.char
            if ch:
                set_hotkey_keyboard_char(ch); return
        except:
            set_hotkey_keyboard_special(key); return
        return

    # Capture OUTPUT
    if capture_target == "output":
        try:
            if key in {keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3, keyboard.Key.f4, keyboard.Key.f5,
                       keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9,
                       keyboard.Key.space, keyboard.Key.enter, keyboard.Key.shift,
                       keyboard.Key.ctrl, keyboard.Key.alt}:
                set_output_keyboard_special(key); return
            ch = key.char
            if ch:
                set_output_keyboard_char(ch); return
        except:
            set_output_keyboard_special(key); return
        return

    # Normal run
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
    global running, capture_target
    if not listeners_ok:
        return

    # Capture by mouse
    if pressed and capture_target == "hotkey":
        set_hotkey_mouse(button); return
    if pressed and capture_target == "output":
        set_output_mouse(button); return

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
    _refresh_permission_status()

def retry_listeners():
    start_listeners()
    update_language()

# ======================
# Rounded shapes (Canvas) + Language card buttons
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
    for f in (logo_frame, lang_frame, main_frame, test_home_frame, test_pick_frame, test_run_frame, test_result_frame):
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

    # main header
    title_label.configure(text=current_lang["title"])
    subtitle_label.configure(text=current_lang["subtitle"])
    card1.configure(text=current_lang["card_hotkey"])
    card2.configure(text=current_lang["card_settings"])
    hotkey_label.configure(text=current_lang["hotkey"])
    detect_btn.configure(text=current_lang["detect"])
    tip_label.configure(text=current_lang["tip_hotkey"])
    output_key_label.configure(text=current_lang["output_key"])
    output_detect_btn.configure(text=current_lang["detect"])
    output_tip_label.configure(text=current_lang["tip_output"])
    mode_label.configure(text=current_lang["mode"])
    toggle_rb.configure(text=current_lang["toggle"])
    hold_rb.configure(text=current_lang["hold"])
    speed_label.configure(text=current_lang["speed"])
    theme_btn.configure(text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})")
    lang_title.configure(text=current_lang["language"])
    try:
        retry_btn.configure(text=current_lang["retry"])
        mac_perm_btn.configure(text=current_lang["mac_perm"])
    except:
        pass

    # jitter labels
    try:
        jitter_label.configure(text=current_lang["jitter"])
        jitter_amt_label.configure(text=current_lang["jitter_amt"])
        jitter_tip.configure(text=current_lang["jitter_tip"])
        jitter_chk.configure(text=current_lang["on_off"])
        micro_pause_chk.configure(text=current_lang["micro_pause"])
    except:
        pass

    # cps test UI
    try:
        cps_test_btn.configure(text=current_lang["cps_test"])
        test_home_title.configure(text=current_lang["cps_test"])
        test_home_desc.configure(text=current_lang["cps_test_desc"])
        test_pick_title.configure(text=current_lang["choose_time"])
        btn_5.configure(text=current_lang["sec_5"])
        btn_10.configure(text=current_lang["sec_10"])
        btn_15.configure(text=current_lang["sec_15"])
        test_pick_start.configure(text=current_lang["start_test"])
        test_result_back.configure(text=current_lang["back_settings"])
        test_result_again.configure(text=current_lang["test_again"])
        result_label_avg_t.configure(text=current_lang["avg_cps"])
        result_label_total_t.configure(text=current_lang["total_clicks"])
        result_label_max_t.configure(text=current_lang["max_cps"])
        result_label_stable_t.configure(text=current_lang["stability"])
    except:
        pass

    update_hotkey_info()
    update_output_info()
    check_self_trigger_warning()
    _refresh_permission_status()
    schedule_save()

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

# ======================
# CPS Test Flow (MEASURE EMITTED OUTPUT)
# ======================
def go_test_home():
    global running
    running = False
    pressed_keys.clear()

    if not MPL_OK:
        messagebox.showwarning("CPS Test", current_lang.get("mpl_missing", "pip install matplotlib"))
        return

    show_frame(test_home_frame)

def go_test_pick():
    global running
    running = False
    pressed_keys.clear()
    show_frame(test_pick_frame)

def set_test_duration(sec: int):
    global test_duration
    test_duration = int(sec)
    for b in (btn_5, btn_10, btn_15):
        b.configure(bootstyle="secondary")
    if sec == 5:
        btn_5.configure(bootstyle="success")
    elif sec == 10:
        btn_10.configure(bootstyle="success")
    else:
        btn_15.configure(bootstyle="success")

def _compute_bins():
    global test_bins_t, test_bins_cps, test_avg_line
    n_bins = int(test_duration / TEST_BIN)
    counts = [0] * (n_bins + 1)

    with test_lock:
        times = list(test_emit_times)

    for t in times:
        idx = int(min(n_bins, max(0, t / TEST_BIN)))
        counts[idx] += 1

    test_bins_t = [i * TEST_BIN for i in range(n_bins + 1)]
    test_bins_cps = [c / TEST_BIN for c in counts]

    avg = []
    s = 0
    for i, c in enumerate(counts):
        s += c
        sec = max(0.001, (i + 1) * TEST_BIN)
        avg.append((s / sec))
    test_avg_line = avg

def _stability_score(cps_list):
    if not cps_list:
        return 0
    mean = sum(cps_list) / len(cps_list)
    if mean <= 0:
        return 0
    var = sum((x - mean) ** 2 for x in cps_list) / max(1, (len(cps_list) - 1))
    std = var ** 0.5
    ratio = std / mean
    score = int(max(0, min(100, 100 - ratio * 160)))
    return score

def start_cps_test():
    global test_running, test_start_t, test_bins_t, test_bins_cps, test_avg_line
    global running, test_emit_times, capture_target

    if not MPL_OK:
        messagebox.showwarning("CPS Test", current_lang.get("mpl_missing", "pip install matplotlib"))
        return

    # ✅ CPS 測試要用「啟動熱鍵」觸發巨集，所以主 listeners 不能停
    running = False
    pressed_keys.clear()

    # 避免還在偵測模式卡住
    capture_target = None
    _refresh_permission_status()

    test_running = True
    with test_lock:
        test_emit_times = []

    test_bins_t = []
    test_bins_cps = []
    test_avg_line = []
    test_start_t = time.perf_counter()

    # UI reset
    hk = _format_hotkey_text()
    out = _format_output_text()
    test_run_time_var.set(f"{current_lang['time_left']}: {test_duration:.0f}s")
    test_run_big_count_var.set("0.0")

    # ✅ 按熱鍵啟動 → 計數輸出
    test_run_big.configure(text=f"PRESS HOTKEY: {hk}\nCOUNTING OUTPUT: {out}")

    _reset_plot()
    show_frame(test_run_frame)

    _tick_test()

def _tick_test():
    global test_running
    if not test_running:
        return

    elapsed = time.perf_counter() - test_start_t
    left = max(0.0, test_duration - elapsed)
    test_run_time_var.set(f"{current_lang['time_left']}: {left:.1f}s")

    _update_plot_live(elapsed)

    if elapsed >= test_duration:
        test_running = False
        finish_cps_test()
        return

    root.after(50, _tick_test)

def on_test_click(event=None):
    # ✅ 不再用手動點擊計數（避免誤差/灌水）
    return

def finish_cps_test():
    global running
    stop_test_listeners()

    # ✅ 測試結束自動停掉巨集
    running = False
    pressed_keys.clear()
    _refresh_permission_status()

    _compute_bins()

    with test_lock:
        total = len(test_emit_times)

    avg_cps = total / max(0.001, test_duration)
    mx = max(test_bins_cps) if test_bins_cps else 0
    stable = _stability_score(test_bins_cps)

    messagebox.showinfo(
        current_lang["result_title"],
        f"{current_lang['result_msg']}\n\n"
        f"{current_lang['avg_cps']}: {avg_cps:.1f}\n"
        f"{current_lang['total_clicks']}: {total}"
    )

    result_avg_var.set(f"{avg_cps:.1f}")
    result_total_var.set(str(total))
    result_max_var.set(f"{mx:.1f}")
    result_stable_var.set(f"{stable}/100")

    _render_result_plot()
    show_frame(test_result_frame)

def back_to_settings():
    global running, test_running
    test_running = False
    running = False
    pressed_keys.clear()
    show_frame(main_frame)
    update_language()
    apply_theme()
    apply_all_settings()
    update_hotkey_info()
    update_output_info()
    start_listeners()
    _refresh_permission_status()
    schedule_save()

def test_again():
    global running, test_running
    test_running = False
    running = False
    pressed_keys.clear()
    go_test_pick()

# ======================
# Plot helpers
# ======================
fig = None
ax = None
line_cps = None
line_avg = None
canvas_plot = None

fig2 = None
ax2 = None
line2_cps = None
line2_avg = None
canvas_plot2 = None

def _make_plot(parent):
    f = Figure(figsize=(6, 3.0), dpi=100)
    a = f.add_subplot(111)
    a.set_xlabel("Time (s)")
    a.set_ylabel("CPS")
    a.grid(True, alpha=0.25)
    c = FigureCanvasTkAgg(f, master=parent)
    c.get_tk_widget().pack(fill=BOTH, expand=True)
    return f, a, c

def _reset_plot():
    ax.clear()
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CPS")
    ax.grid(True, alpha=0.25)
    ax.set_xlim(0, max(5, test_duration))
    ax.set_ylim(0, 300)
    global line_cps, line_avg
    line_cps, = ax.plot([], [], linewidth=1.8)
    line_avg, = ax.plot([], [], linewidth=2.0)
    canvas_plot.draw()

def _update_plot_live(elapsed):
    with test_lock:
        times = list(test_emit_times)

    total = len(times)
    avg_now = total / max(0.001, elapsed)
    test_run_big_count_var.set(f"{avg_now:.1f}")

    if elapsed < 0.05:
        return

    tmp = [t for t in times if t <= elapsed]
    if not tmp:
        line_cps.set_data([], [])
        line_avg.set_data([], [])
        canvas_plot.draw_idle()
        return

    n_bins = int(max(1, elapsed / TEST_BIN))
    counts = [0] * (n_bins + 1)
    for t in tmp:
        idx = int(min(n_bins, max(0, t / TEST_BIN)))
        counts[idx] += 1

    xs = [i * TEST_BIN for i in range(n_bins + 1)]
    ys = [c / TEST_BIN for c in counts]

    avg = []
    s = 0
    for i, c in enumerate(counts):
        s += c
        sec = max(0.001, (i + 1) * TEST_BIN)
        avg.append(s / sec)

    peak = max(10, max(ys) if ys else 10, max(avg) if avg else 10)
    ax.set_ylim(0, min(500, max(50, peak * 1.25)))
    ax.set_xlim(0, max(5, test_duration))

    line_cps.set_data(xs, ys)
    line_avg.set_data(xs, avg)
    canvas_plot.draw_idle()

def _render_result_plot():
    ax2.clear()
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("CPS")
    ax2.grid(True, alpha=0.25)

    xs = test_bins_t
    ys = test_bins_cps
    avg = test_avg_line

    peak = max(10, max(ys) if ys else 10, max(avg) if avg else 10)
    ax2.set_ylim(0, min(500, max(50, peak * 1.25)))
    ax2.set_xlim(0, max(5, test_duration))

    ax2.plot(xs, ys, linewidth=1.8)
    ax2.plot(xs, avg, linewidth=2.0)
    canvas_plot2.draw()

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
    text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})",
    variable=theme_var,
    command=apply_theme,
    bootstyle="round-toggle"
)
theme_btn.pack(anchor=E)

ttk.Separator(container).pack(fill=X, pady=14)

# Card 1
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

# Card 2
card2 = ttk.Labelframe(container, text=current_lang["card_settings"], padding=14, bootstyle="secondary")
card2.pack(fill=BOTH, expand=True)

grid = ttk.Frame(card2)
grid.pack(fill=BOTH, expand=True)
grid.grid_columnconfigure(0, weight=0)
grid.grid_columnconfigure(1, weight=1)
grid.grid_columnconfigure(2, weight=0)
grid.grid_columnconfigure(3, weight=1)

# Output detect
output_key_label = ttk.Label(grid, text=current_lang["output_key"])
output_key_label.grid(row=0, column=0, sticky=W, pady=(0, 6))

output_detect_btn = ttk.Button(grid, text=current_lang["detect"], bootstyle="primary", command=start_capture_output)
output_detect_btn.grid(row=0, column=2, sticky=W, padx=(10, 0))

output_info_var = ttk.StringVar(value=f"{current_lang['output_now']} {_format_output_text()}")
output_info_label = ttk.Label(grid, textvariable=output_info_var, bootstyle="info")
output_info_label.grid(row=1, column=0, columnspan=4, sticky=W, pady=(6, 6))

output_tip_label = ttk.Label(grid, text=current_lang["tip_output"], bootstyle="secondary")
output_tip_label.grid(row=2, column=0, columnspan=4, sticky=W, pady=(0, 10))

# Mode
mode_label = ttk.Label(grid, text=current_lang["mode"])
mode_label.grid(row=3, column=0, sticky=W, pady=6)

mode_var = ttk.StringVar(
    value=_loaded_settings.get("mode", "toggle")
    if _loaded_settings.get("mode") in ("toggle", "hold") else "toggle"
)

toggle_rb = ttk.Radiobutton(grid, text=current_lang["toggle"], variable=mode_var, value="toggle",
                            command=on_mode_change, bootstyle="success-toolbutton")
toggle_rb.grid(row=3, column=1, sticky=W, padx=(10, 2))

hold_rb = ttk.Radiobutton(grid, text=current_lang["hold"], variable=mode_var, value="hold",
                          command=on_mode_change, bootstyle="warning-toolbutton")
hold_rb.grid(row=3, column=2, sticky=W, padx=(2, 0))

# CPS
speed_label = ttk.Label(grid, text=current_lang["speed"])
speed_label.grid(row=4, column=0, sticky=W, pady=10)

cps_var = ttk.StringVar(value=str(_loaded_settings.get("cps", "100")))
cps_combo = ttk.Combobox(
    grid, textvariable=cps_var, width=10,
    values=["10", "20", "30", "40", "50", "100", "150", "200", "250", "300", "350", "450", "500"],
    state="readonly"
)
cps_combo.grid(row=4, column=1, sticky=W, padx=10)
cps_combo.bind("<<ComboboxSelected>>", apply_all_settings)
ttk.Label(grid, text="CPS", bootstyle="secondary").grid(row=4, column=2, sticky=W)

# CPS Test button (入口)
cps_test_btn = ttk.Button(grid, text=current_lang["cps_test"], bootstyle="info", command=go_test_home)
cps_test_btn.grid(row=4, column=3, sticky=E, padx=(10, 0))
if not MPL_OK:
    cps_test_btn.configure(state="disabled")

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
    global jitter_on, jitter_pct, micro_pause_on, running
    running = False
    pressed_keys.clear()
    jitter_on = bool(jitter_var.get())
    try:
        jitter_pct = float(jitter_pct_var.get())
    except:
        jitter_pct = 0.12
        jitter_pct_var.set(0.12)
    micro_pause_on = bool(micro_pause_var.get())
    try:
        jitter_value_label.configure(text=_fmt_pct())
    except:
        pass
    _refresh_permission_status()
    schedule_save()

jitter_label = ttk.Label(grid, text=current_lang["jitter"])
jitter_label.grid(row=5, column=0, sticky=W, pady=(6, 0))

jitter_chk = ttk.Checkbutton(grid, text=current_lang["on_off"], variable=jitter_var,
                             command=on_jitter_change, bootstyle="round-toggle")
jitter_chk.grid(row=5, column=1, sticky=W, padx=(10, 0), pady=(6, 0))

jitter_amt_label = ttk.Label(grid, text=current_lang["jitter_amt"], bootstyle="secondary")
jitter_amt_label.grid(row=6, column=0, sticky=W, pady=(6, 0))

jitter_scale = ttk.Scale(grid, from_=0.0, to=0.30, variable=jitter_pct_var, command=lambda v: on_jitter_change())
jitter_scale.grid(row=6, column=1, sticky="ew", padx=(10, 10), pady=(6, 0))

jitter_value_label = ttk.Label(grid, text=_fmt_pct(), bootstyle="info")
jitter_value_label.grid(row=6, column=2, sticky=W, pady=(6, 0))

micro_pause_chk = ttk.Checkbutton(grid, text=current_lang["micro_pause"], variable=micro_pause_var,
                                  command=on_jitter_change, bootstyle="secondary")
micro_pause_chk.grid(row=6, column=3, sticky=W, pady=(6, 0))

jitter_tip = ttk.Label(grid, text=current_lang["jitter_tip"], bootstyle="secondary")
jitter_tip.grid(row=7, column=0, columnspan=4, sticky=W, pady=(6, 0))

ttk.Separator(container).pack(fill=X, pady=14)

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

# ---------- Frame 3: CPS Test Home ----------
test_home_frame = ttk.Frame(root)
th = ttk.Frame(test_home_frame, padding=22)
th.pack(fill=BOTH, expand=True)

test_home_title = ttk.Label(th, text=current_lang["cps_test"], font=("Segoe UI", 26, "bold"))
test_home_title.pack(anchor=W)

test_home_desc = ttk.Label(th, text=current_lang["cps_test_desc"], bootstyle="secondary")
test_home_desc.pack(anchor=W, pady=(6, 18))

ttk.Button(th, text=current_lang["choose_time"], bootstyle="success", command=go_test_pick).pack(anchor=W)
ttk.Button(th, text=current_lang["back_settings"], bootstyle="secondary", command=back_to_settings).pack(anchor=W, pady=(10, 0))

# ---------- Frame 4: Pick Duration ----------
test_pick_frame = ttk.Frame(root)
tp = ttk.Frame(test_pick_frame, padding=22)
tp.pack(fill=BOTH, expand=True)

test_pick_title = ttk.Label(tp, text=current_lang["choose_time"], font=("Segoe UI", 24, "bold"))
test_pick_title.pack(anchor=W)

pick_row = ttk.Frame(tp)
pick_row.pack(fill=X, pady=(16, 10))
btn_5 = ttk.Button(pick_row, text=current_lang["sec_5"], bootstyle="secondary", command=lambda: set_test_duration(5))
btn_10 = ttk.Button(pick_row, text=current_lang["sec_10"], bootstyle="success", command=lambda: set_test_duration(10))
btn_15 = ttk.Button(pick_row, text=current_lang["sec_15"], bootstyle="secondary", command=lambda: set_test_duration(15))
btn_5.pack(side=LEFT, padx=(0, 10))
btn_10.pack(side=LEFT, padx=(0, 10))
btn_15.pack(side=LEFT)

test_pick_start = ttk.Button(tp, text=current_lang["start_test"], bootstyle="primary", command=start_cps_test)
test_pick_start.pack(anchor=W, pady=(10, 0))

ttk.Button(tp, text=current_lang["back_settings"], bootstyle="secondary", command=back_to_settings).pack(anchor=W, pady=(14, 0))

# default duration highlight
set_test_duration(test_duration)

# ---------- Frame 5: Running Test ----------
test_run_frame = ttk.Frame(root)
tr = ttk.Frame(test_run_frame, padding=18)
tr.pack(fill=BOTH, expand=True)

topbar = ttk.Frame(tr)
topbar.pack(fill=X)

test_run_time_var = ttk.StringVar(value=f"{current_lang['time_left']}: {test_duration}s")
ttk.Label(topbar, textvariable=test_run_time_var, bootstyle="secondary").pack(side=LEFT)

test_run_big_count_var = ttk.StringVar(value="0.0")
ttk.Label(topbar, textvariable=test_run_big_count_var, font=("Segoe UI", 24, "bold")).pack(side=RIGHT)

# Click area (提示用)
click_area = ttk.Frame(tr, padding=0)
click_area.pack(fill=X, pady=(12, 10))

test_run_big = ttk.Label(
    click_area,
    text=current_lang["click_block"],
    anchor="center",
    font=("Segoe UI", 28, "bold"),
    bootstyle="success",
    padding=24
)
test_run_big.pack(fill=X)

# Plot area
plot_holder = ttk.Frame(tr)
plot_holder.pack(fill=BOTH, expand=True)

if MPL_OK:
    fig, ax, canvas_plot = _make_plot(plot_holder)
    _reset_plot()
else:
    ttk.Label(plot_holder, text=current_lang.get("mpl_missing", "pip install matplotlib"), bootstyle="danger").pack(pady=20)

# ---------- Frame 6: Result ----------
test_result_frame = ttk.Frame(root)
rr = ttk.Frame(test_result_frame, padding=18)
rr.pack(fill=BOTH, expand=True)

result_top = ttk.Frame(rr)
result_top.pack(fill=X)

test_result_back = ttk.Button(result_top, text=current_lang["back_settings"], bootstyle="secondary", command=back_to_settings)
test_result_back.pack(side=LEFT)

test_result_again = ttk.Button(result_top, text=current_lang["test_again"], bootstyle="primary", command=test_again)
test_result_again.pack(side=LEFT, padx=(10, 0))

result_big = ttk.Label(rr, text="0.0", font=("Segoe UI", 48, "bold"))
result_big.pack(anchor=W, pady=(12, 6))

stats = ttk.Frame(rr)
stats.pack(fill=X, pady=(0, 10))

result_avg_var = ttk.StringVar(value="0.0")
result_total_var = ttk.StringVar(value="0")
result_max_var = ttk.StringVar(value="0.0")
result_stable_var = ttk.StringVar(value="0/100")

def _bind_result_big(*_):
    result_big.configure(text=result_avg_var.get())
result_avg_var.trace_add("write", lambda *_: _bind_result_big())

rowa = ttk.Frame(stats); rowa.pack(fill=X, pady=2)
result_label_avg_t = ttk.Label(rowa, text=current_lang["avg_cps"], width=16)
result_label_avg_t.pack(side=LEFT)
ttk.Label(rowa, textvariable=result_avg_var, bootstyle="info").pack(side=LEFT)

rowb = ttk.Frame(stats); rowb.pack(fill=X, pady=2)
result_label_total_t = ttk.Label(rowb, text=current_lang["total_clicks"], width=16)
result_label_total_t.pack(side=LEFT)
ttk.Label(rowb, textvariable=result_total_var, bootstyle="info").pack(side=LEFT)

rowc = ttk.Frame(stats); rowc.pack(fill=X, pady=2)
result_label_max_t = ttk.Label(rowc, text=current_lang["max_cps"], width=16)
result_label_max_t.pack(side=LEFT)
ttk.Label(rowc, textvariable=result_max_var, bootstyle="info").pack(side=LEFT)

rowd = ttk.Frame(stats); rowd.pack(fill=X, pady=2)
result_label_stable_t = ttk.Label(rowd, text=current_lang["stability"], width=16)
result_label_stable_t.pack(side=LEFT)
ttk.Label(rowd, textvariable=result_stable_var, bootstyle="info").pack(side=LEFT)

plot_holder2 = ttk.Frame(rr)
plot_holder2.pack(fill=BOTH, expand=True)

if MPL_OK:
    fig2, ax2, canvas_plot2 = _make_plot(plot_holder2)
else:
    ttk.Label(plot_holder2, text=current_lang.get("mpl_missing", "pip install matplotlib"), bootstyle="danger").pack(pady=20)

# ======================
# Navigation (logo/lang/main)
# ======================
def go_main_direct():
    show_frame(main_frame)
    update_language()
    apply_theme()
    apply_all_settings()
    update_hotkey_info()
    update_output_info()
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
    global running, fullscreen, test_running
    test_running = False
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

# 先做 UI 初始化（不要在這裡啟動 listeners）
root.after(
    0,
    lambda: (
        update_language(),
        apply_theme(),
        apply_all_settings(),
        update_hotkey_info(),
        update_output_info(),
        check_self_trigger_warning(),
        on_jitter_change(),
        _refresh_permission_status(),
        schedule_save()
    )
)

# ✅ 安全延遲啟動 listeners（macOS 避免 trace trap）
def safe_start_listeners():
    try:
        start_listeners()
    except Exception as e:
        print("Listener start failed:", e)

if platform.system().lower() == "darwin":
    root.after(2000, safe_start_listeners)  # mac 延遲 2 秒
else:
    root.after(0, safe_start_listeners)     # 其他平台立即啟動

root.mainloop()

