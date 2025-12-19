import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pynput import keyboard, mouse
import threading
import time

# ======================
# App Config
# ======================
LIGHT_THEME = "flatly"   # white
DARK_THEME = "darkly"    # black

# ======================
# Globals
# ======================
running = False
selected_cps = 100
output_key = "f"  # while running, it presses this key repeatedly
keyboard_controller = keyboard.Controller()

# Hotkey supports: keyboard char / special(F1~F9) / mouse side buttons
hotkey_kind = "keyboard"      # "keyboard" or "mouse"
hotkey_type = "char"          # "char" or "special"
hotkey_char = "f"
hotkey_special = keyboard.Key.f1
hotkey_mouse_btn = mouse.Button.x1

kb_listener = None
ms_listener = None

capture_mode = False
pressed_keys = set()

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
}

current_lang = LANG_EN  # actual content language (set by splash selection)

# ======================
# UI Helpers
# ======================
def apply_theme():
    theme = DARK_THEME if theme_var.get() else LIGHT_THEME
    root.style.theme_use(theme)

def set_status(text, style):
    status_var.set(text)
    status_badge.configure(bootstyle=style)

def update_hotkey_info():
    if hotkey_kind == "mouse":
        if hotkey_mouse_btn == mouse.Button.x1:
            hotkey_info_var.set(f"{current_lang['hotkey_now']} Mouse XBUTTON1")
        elif hotkey_mouse_btn == mouse.Button.x2:
            hotkey_info_var.set(f"{current_lang['hotkey_now']} Mouse XBUTTON2")
        else:
            hotkey_info_var.set(f"{current_lang['hotkey_now']} Mouse {hotkey_mouse_btn}")
        return

    if hotkey_type == "char":
        hotkey_info_var.set(f"{current_lang['hotkey_now']} Keyboard '{hotkey_char.upper()}'")
    else:
        name = str(hotkey_special).replace("Key.", "").upper()
        hotkey_info_var.set(f"{current_lang['hotkey_now']} Keyboard {name}")

def update_language():
    global current_lang

    v = lang_var.get()
    if v == "繁體中文":
        current_lang = LANG_ZH
    elif v == "한국어":
        current_lang = LANG_KR
    else:
        current_lang = LANG_EN

    # Header
    title_label.configure(text=current_lang["title"])
    subtitle_label.configure(text=current_lang["subtitle"])

    # Cards
    card1.configure(text=current_lang["card_hotkey"])
    card2.configure(text=current_lang["card_settings"])

    # Hotkey section
    hotkey_label.configure(text=current_lang["hotkey"])
    detect_btn.configure(text=current_lang["detect"])
    tip_label.configure(text=current_lang["tip_hotkey"])

    # Settings section
    mode_label.configure(text=current_lang["mode"])
    toggle_rb.configure(text=current_lang["toggle"])
    hold_rb.configure(text=current_lang["hold"])
    speed_label.configure(text=current_lang["speed"])

    # Footer
    theme_btn.configure(text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})")
    lang_title.configure(text=current_lang["language"])

    # Status text: keep state
    if capture_mode:
        set_status(current_lang["status_detect"], "warning")
    elif running:
        set_status(current_lang["status_run"], "success")
    else:
        set_status(current_lang["status_wait"], "secondary")

    update_hotkey_info()

# ======================
# Click Thread
# ======================
def autoclicker_thread():
    global running, selected_cps
    while True:
        if running:
            keyboard_controller.press(output_key)
            keyboard_controller.release(output_key)
            time.sleep(1 / max(1, selected_cps))
        else:
            time.sleep(0.01)

# ======================
# Hotkey Setters
# ======================
def set_hotkey_keyboard_char(ch: str):
    global hotkey_kind, hotkey_type, hotkey_char, running
    hotkey_kind = "keyboard"
    hotkey_type = "char"
    hotkey_char = (ch or "f").lower()[:1]
    running = False
    pressed_keys.clear()

    hotkey_entry.delete(0, "end")
    hotkey_entry.insert(0, hotkey_char)

    set_status(current_lang["status_wait"], "secondary")
    update_hotkey_info()

def set_hotkey_keyboard_special(key_obj):
    global hotkey_kind, hotkey_type, hotkey_special, running
    hotkey_kind = "keyboard"
    hotkey_type = "special"
    hotkey_special = key_obj
    running = False
    pressed_keys.clear()

    txt = str(key_obj).replace("Key.", "").upper()
    hotkey_entry.delete(0, "end")
    hotkey_entry.insert(0, txt)

    set_status(current_lang["status_wait"], "secondary")
    update_hotkey_info()

def set_hotkey_mouse(btn):
    global hotkey_kind, hotkey_mouse_btn, running
    hotkey_kind = "mouse"
    hotkey_mouse_btn = btn
    running = False
    pressed_keys.clear()

    if btn == mouse.Button.x1:
        txt = "XBUTTON1"
    elif btn == mouse.Button.x2:
        txt = "XBUTTON2"
    else:
        txt = str(btn).upper()

    hotkey_entry.delete(0, "end")
    hotkey_entry.insert(0, txt)

    set_status(current_lang["status_wait"], "secondary")
    update_hotkey_info()

# ======================
# Detect Mode
# ======================
def start_capture():
    global capture_mode, running
    running = False
    pressed_keys.clear()
    capture_mode = True
    set_status(current_lang["status_detect"], "warning")

# ======================
# Apply Settings (manual input)
# ======================
def apply_all_settings(event=None):
    global selected_cps, running
    running = False
    pressed_keys.clear()

    hk = hotkey_entry.get().strip()
    hkl = hk.lower()

    # CPS
    try:
        selected_cps = int(cps_var.get())
    except:
        selected_cps = 100
        cps_var.set("100")

    # Mouse aliases
    x1_alias = {"xbutton1", "xbottom1", "xbtn1", "x1", "mouse4", "mb4"}
    x2_alias = {"xbutton2", "xbottom2", "xbtn2", "x2", "mouse5", "mb5"}
    if hkl in x1_alias:
        set_hotkey_mouse(mouse.Button.x1)
        return
    if hkl in x2_alias:
        set_hotkey_mouse(mouse.Button.x2)
        return

    # F1~F9
    f_map = {
        "f1": keyboard.Key.f1, "f2": keyboard.Key.f2, "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4, "f5": keyboard.Key.f5, "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7, "f8": keyboard.Key.f8, "f9": keyboard.Key.f9,
    }
    if hkl in f_map:
        set_hotkey_keyboard_special(f_map[hkl])
        return

    # fallback: first char
    if len(hkl) >= 1:
        set_hotkey_keyboard_char(hkl[0])
    else:
        set_hotkey_keyboard_char("f")

def on_mode_change():
    global running
    running = False
    pressed_keys.clear()
    set_status(current_lang["status_wait"], "secondary")

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

    # Detect mode: capture F1~F9 or char
    if capture_mode:
        if key in {
            keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3,
            keyboard.Key.f4, keyboard.Key.f5, keyboard.Key.f6,
            keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9
        }:
            capture_mode = False
            set_hotkey_keyboard_special(key)
            return
        try:
            ch = key.char
        except:
            return
        if ch:
            capture_mode = False
            set_hotkey_keyboard_char(ch)
        return

    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "hold":
        if is_hotkey_pressed(key):
            if "HOTKEY" in pressed_keys:
                return
            pressed_keys.add("HOTKEY")
            running = True
            set_status(current_lang["status_run"], "success")
            return

    if mode_var.get() == "toggle":
        if is_hotkey_pressed(key):
            running = not running
            set_status(current_lang["status_run"], "success" if running else "danger")

def on_release(key):
    global running
    if hotkey_kind != "keyboard":
        return

    if mode_var.get() == "hold":
        if is_hotkey_pressed(key):
            pressed_keys.discard("HOTKEY")
            running = False
            set_status(current_lang["status_stop"], "danger")

def on_click(x, y, button, pressed):
    global running, capture_mode

    # Detect mode: capture mouse button
    if capture_mode and pressed:
        capture_mode = False
        set_hotkey_mouse(button)
        return

    if hotkey_kind != "mouse":
        return
    if button != hotkey_mouse_btn:
        return

    if mode_var.get() == "hold":
        if pressed:
            running = True
            set_status(current_lang["status_run"], "success")
        else:
            running = False
            set_status(current_lang["status_stop"], "danger")
        return

    if mode_var.get() == "toggle":
        if pressed:
            running = not running
            set_status(current_lang["status_run"], "success" if running else "danger")

def start_listeners():
    global kb_listener, ms_listener
    kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    kb_listener.start()
    ms_listener = mouse.Listener(on_click=on_click)
    ms_listener.start()

# ======================
# Splash Animation (fade transition)
# ======================
def fade_to(alpha_target, step=0.06, delay=12, on_done=None):
    """Fade window alpha to target (0.0~1.0)."""
    try:
        cur = float(root.attributes("-alpha"))
    except:
        cur = 1.0

    if alpha_target < cur:
        cur = max(alpha_target, cur - step)
    else:
        cur = min(alpha_target, cur + step)

    root.attributes("-alpha", cur)

    if abs(cur - alpha_target) <= 0.001:
        if on_done:
            root.after(delay, on_done)
        return

    root.after(delay, lambda: fade_to(alpha_target, step, delay, on_done))

def go_main_with_language(lang_choice: str):
    """
    lang_choice in {"English","繁體中文","한국어"}
    Fade out -> swap frames -> fade in
    """
    # lock buttons
    for b in splash_buttons:
        b.configure(state=DISABLED)

    # set language var now
    lang_var.set(lang_choice)

    def swap_to_main():
        splash_frame.pack_forget()
        main_frame.pack(fill=BOTH, expand=True)

        # apply language + theme + initial state
        update_language()
        apply_theme()
        apply_all_settings()
        update_hotkey_info()
        set_status(current_lang["status_wait"], "secondary")

        # fade back in
        fade_to(1.0, on_done=None)

    # fade out then swap
    fade_to(0.0, on_done=swap_to_main)

# ======================
# Build UI
# ======================
root = ttk.Window(
    title="W1te Auto Clicker PRO",
    themename=LIGHT_THEME,
    size=(580, 460)
)
root.resizable(False, False)
root.attributes("-alpha", 1.0)

# ---------- Splash Frame ----------
splash_frame = ttk.Frame(root, padding=22)
splash_frame.pack(fill=BOTH, expand=True)

splash_card = ttk.Frame(splash_frame, padding=26, bootstyle="secondary")
splash_card.place(relx=0.5, rely=0.5, anchor="center")

ttk.Label(
    splash_card,
    text="Select Language",
    font=("Segoe UI", 18, "bold")
).pack(pady=(0, 6))

ttk.Label(
    splash_card,
    text="언어 선택 • 語言選擇",
    bootstyle="secondary"
).pack(pady=(0, 18))

btn_row = ttk.Frame(splash_card)
btn_row.pack()

# three buttons (each in its own language)
splash_buttons = []

b_zh = ttk.Button(btn_row, text="繁體中文", width=14, bootstyle="secondary-outline",
                  command=lambda: go_main_with_language("繁體中文"))
b_zh.grid(row=0, column=0, padx=8, pady=6)
splash_buttons.append(b_zh)

b_en = ttk.Button(btn_row, text="English", width=14, bootstyle="primary",
                  command=lambda: go_main_with_language("English"))
b_en.grid(row=0, column=1, padx=8, pady=6)
splash_buttons.append(b_en)

b_kr = ttk.Button(btn_row, text="한국어", width=14, bootstyle="secondary-outline",
                  command=lambda: go_main_with_language("한국어"))
b_kr.grid(row=0, column=2, padx=8, pady=6)
splash_buttons.append(b_kr)

ttk.Label(
    splash_card,
    text="Tip: You can change it later in settings.",
    bootstyle="secondary"
).pack(pady=(14, 0))

# ---------- Main Frame ----------
main_frame = ttk.Frame(root)  # will be packed after selection

container = ttk.Frame(main_frame, padding=18)
container.pack(fill=BOTH, expand=True)

# Header
header = ttk.Frame(container)
header.pack(fill=X)

title_label = ttk.Label(header, text=current_lang["title"], font=("Segoe UI", 18, "bold"))
title_label.pack(anchor=W)

subtitle_label = ttk.Label(header, text=current_lang["subtitle"], bootstyle="secondary")
subtitle_label.pack(anchor=W, pady=(2, 0))

# Theme toggle
theme_row = ttk.Frame(header)
theme_row.pack(anchor=E, pady=(8, 0), fill=X)

theme_var = ttk.BooleanVar(value=False)  # False=Light, True=Dark
theme_btn = ttk.Checkbutton(
    theme_row,
    text=f"{current_lang['theme']} ({current_lang['light']} / {current_lang['dark']})",
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
hotkey_entry.insert(0, "F1")
hotkey_entry.bind("<KeyRelease>", apply_all_settings)

detect_btn = ttk.Button(row1, text=current_lang["detect"], bootstyle="primary", command=start_capture)
detect_btn.pack(side=LEFT)

tip_label = ttk.Label(card1, text=current_lang["tip_hotkey"], bootstyle="secondary")
tip_label.pack(anchor=W, pady=(8, 0))

hotkey_info_var = ttk.StringVar(value="")
hotkey_info_label = ttk.Label(card1, textvariable=hotkey_info_var, bootstyle="info")
hotkey_info_label.pack(anchor=W, pady=(8, 0))

# Card 2: Settings
card2 = ttk.Labelframe(container, text=current_lang["card_settings"], padding=14, bootstyle="secondary")
card2.pack(fill=X)

grid = ttk.Frame(card2)
grid.pack(fill=X)

mode_label = ttk.Label(grid, text=current_lang["mode"])
mode_label.grid(row=0, column=0, sticky=W, pady=6)

mode_var = ttk.StringVar(value="toggle")
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

cps_var = ttk.StringVar(value="100")
cps_combo = ttk.Combobox(
    grid,
    textvariable=cps_var,
    width=10,
    values=["50", "100", "150", "200", "250", "300", "350", "450", "500"]
)

cps_combo.grid(row=1, column=1, sticky=W, padx=10)
cps_combo.bind("<<ComboboxSelected>>", apply_all_settings)

ttk.Label(grid, text="CPS", bootstyle="secondary").grid(row=1, column=2, sticky=W)

ttk.Separator(container).pack(fill=X, pady=14)

# Footer: Status + Language switch
footer = ttk.Frame(container)
footer.pack(fill=X)

status_var = ttk.StringVar(value=current_lang["status_wait"])
status_badge = ttk.Label(footer, textvariable=status_var, bootstyle="secondary", padding=(10, 6))
status_badge.pack(side=LEFT)

lang_title = ttk.Label(footer, text=current_lang["language"], bootstyle="secondary")
lang_title.pack(side=RIGHT, padx=(0, 8))

lang_var = ttk.StringVar(value="English")  # default for main screen
lang_menu = ttk.Combobox(footer, textvariable=lang_var, values=["English", "繁體中文", "한국어"], width=12)
lang_menu.pack(side=RIGHT)
lang_menu.bind("<<ComboboxSelected>>", lambda e: update_language())

# Start background systems
threading.Thread(target=autoclicker_thread, daemon=True).start()
start_listeners()

root.mainloop()

