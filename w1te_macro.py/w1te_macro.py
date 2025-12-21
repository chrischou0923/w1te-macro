import time
import threading
from pynput import keyboard

# ======================
# 設定區
# ======================
TRIGGER_KEY = "e"   # 觸發鍵（你要的 E）
OUTPUT_KEY = "f"    # 輸出鍵（維持 F）
CPS = 20            # 每秒點擊次數

# ======================
# 狀態
# ======================
running = False
kb_controller = keyboard.Controller()

# ======================
# 連點執行緒
# ======================
def click_loop():
    global running
    interval = 1.0 / CPS

    while running:
        try:
            kb_controller.press(OUTPUT_KEY)
            kb_controller.release(OUTPUT_KEY)
        except:
            pass
        time.sleep(interval)

# ======================
# 鍵盤監聽
# ======================
def on_press(key):
    global running
    try:
        if key.char == TRIGGER_KEY:
            if not running:
                running = True
                threading.Thread(target=click_loop, daemon=True).start()
    except AttributeError:
        pass

def on_release(key):
    global running
    try:
        if key.char == TRIGGER_KEY:
            running = False
    except AttributeError:
        pass

# ======================
# 主程式
# ======================
print("W1te Macro running")
print("Hold [E] to spam [F]")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

