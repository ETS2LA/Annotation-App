import src.variables as variables
import src.settings as settings
import src.console as console
import src.utils as utils
import src.ui as ui

import traceback
import threading
import requests
import ctypes
import pynput
import mouse
import time
import cv2
import os

if variables.OS == "nt":
    import win32gui
    import ctypes

if settings.Get("Console", "HideConsole", False):
    console.HideConsole()

try:
    remote_version = requests.get("https://raw.githubusercontent.com/ETS2LA/Annotation-App/main/version.txt").text.strip()
except:
    print(f"{variables.RED}Failed to check for updates:{variables.NORMAL}\n" + str(traceback.format_exc()))
if remote_version != variables.VERSION and settings.Get("Update", "AutoUpdate", True):
    try:
        print(f"New version available: {remote_version}")
        os.chdir(variables.PATH)
        os.system("git stash")
        os.system("git pull")
    except:
        print(f"{variables.RED}Failed to update: {variables.NORMAL}\n" + str(traceback.format_exc()))
else:
    print("No update available, current version: " + variables.VERSION)

ui.Initialize()
ui.CreateUI()

last_frame = None
last_inputs = None
current_tab = None

def MouseHandler():
    global last_left_clicked, last_right_clicked, left_clicked, right_clicked, last_mouse_x, last_mouse_y, mouse_x, mouse_y, move_start
    last_left_clicked = False
    last_right_clicked = False
    left_clicked = False
    right_clicked = False
    last_mouse_x = 0
    last_mouse_y = 0
    mouse_x = 0
    mouse_y = 0
    move_start = 0, 0
    while variables.BREAK == False:
        if win32gui.GetForegroundWindow() != variables.HWND or current_tab != "Annotate":
            time.sleep(0.1)
            continue

        start = time.time()

        rect = win32gui.GetClientRect(variables.HWND)
        tl = win32gui.ClientToScreen(variables.HWND, (rect[0], rect[1]))
        br = win32gui.ClientToScreen(variables.HWND, (rect[2], rect[3]))
        window_x, window_y, window_width, window_height = tl[0], tl[1] + 40, br[0] - tl[0], br[1] - tl[1]
        mouse_x, mouse_y = mouse.get_position()

        left_clicked = ctypes.windll.user32.GetKeyState(0x01) & 0x8000 != 0 and window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height
        right_clicked = ctypes.windll.user32.GetKeyState(0x02) & 0x8000 != 0 and window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height

        if window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height:
            with pynput.mouse.Events() as events:
                event = events.get()
                if isinstance(event, pynput.mouse.Events.Scroll):
                    canvas_x = (mouse_x - window_x - variables.POSITION[0]) / variables.ZOOM
                    canvas_y = (mouse_y - window_y - variables.POSITION[1]) / variables.ZOOM
                    if variables.ZOOM < 10000:
                        variables.ZOOM = variables.ZOOM * 1.1 if event.dy > 0 else variables.ZOOM / 1.1
                    elif event.dy < 0:
                        variables.ZOOM /= 1.1
                    variables.POSITION = (mouse_x - window_x - canvas_x * variables.ZOOM, mouse_y - window_y - canvas_y * variables.ZOOM)

            if right_clicked == False:
                move_start = mouse_x - variables.POSITION[0], mouse_y - variables.POSITION[1]
            else:
                variables.POSITION = (mouse_x - move_start[0]), (mouse_y - move_start[1])

        last_mouse_x, last_mouse_y = mouse_x, mouse_y
        last_left_clicked, last_right_clicked = left_clicked, right_clicked

        time_to_sleep = 1/variables.FPS - (time.time() - start)
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
threading.Thread(target=MouseHandler, daemon=True).start()

def KeyHandler():
    global pressed_keys
    pressed_keys = []
    keyshortcuts_back = settings.Get("Keyboard", "Back", "ctrl+z")
    keyshortcuts_forward = settings.Get("Keyboard", "Forward", "ctrl+y")
    keyshortcuts_classes = [settings.Get("Keyboard", classname, i + 1) for i, classname in enumerate(variables.CLASSES)]
    def check_key_combination(combination):
        special_keys = {
            "ctrl": 0x11,   # VK_CONTROL
            "shift": 0x10,  # VK_SHIFT
            "alt": 0x12,    # VK_MENU
            "win": 0x5B     # VK_LWIN (left Windows key)
        }
        vk_key_codes = [
            ctypes.windll.user32.VkKeyScanA(ord(key)) & 0xFF if len(key) == 1 else special_keys.get(key.lower())
            for key in combination.split('+')
        ]
        return all(ctypes.windll.user32.GetKeyState(vk) & 0x8000 != 0 for vk in vk_key_codes)
    while variables.BREAK == False:
        if win32gui.GetForegroundWindow() != variables.HWND or current_tab != "Annotate":
            time.sleep(0.1)
            continue

        start = time.time()

        window_is_foreground = win32gui.GetWindowText(win32gui.GetForegroundWindow()) == variables.WINDOWNAME

        if window_is_foreground:
            temp_pressed_keys = []
            if check_key_combination(keyshortcuts_back):
                temp_pressed_keys.append("back")
            if check_key_combination(keyshortcuts_forward):
                temp_pressed_keys.append("forward")
            for i, keyshortcut_class in enumerate(keyshortcuts_classes):
                if check_key_combination(str(keyshortcut_class)):
                    temp_pressed_keys.append(variables.CLASSES[i])

        pressed_keys = temp_pressed_keys

        time_to_sleep = 1/variables.FPS - (time.time() - start)
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
threading.Thread(target=KeyHandler, daemon=True).start()

while variables.BREAK == False:
    start = time.time()

    current_tab = ui.tabControl.tab(ui.tabControl.select(), "text")

    inputs = [variables.POSITION,
              variables.ZOOM,
              left_clicked,
              right_clicked,
              pressed_keys]

    if current_tab == "Annotate" and last_inputs != inputs:
        if ui.background.shape != (variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3):
            ui.background = ui.numpy.zeros((variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3), ui.numpy.uint8)
            ui.background[:] = ((250, 250, 250) if variables.THEME == "light" else (28, 28, 28))
        frame = ui.background.copy()

        POSITION = variables.POSITION
        ZOOM = variables.ZOOM

        text, text_fontscale, text_thickness, text_width, text_height = utils.get_text_size(text = f"pressed shortcuts: {pressed_keys}",
                                                                                            text_width = 500 * variables.ZOOM,
                                                                                            max_text_height = ui.background.shape[0])
        text_x = round(-text_width // 2 + (POSITION[0] * 1/ZOOM) * ZOOM)
        text_y = round(-text_height // 2 + (POSITION[1] * 1/ZOOM) * ZOOM)
        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, text_fontscale, (0, 255, 0), text_thickness)

        frame = ui.ImageTk.PhotoImage(ui.Image.fromarray(frame))
        if last_frame != frame:
            ui.tk_frame.configure(image=frame)
            ui.tk_frame.image = frame
            last_frame = frame

        last_inputs = inputs

    variables.ROOT.update()

    time_to_sleep = 1/variables.FPS - (time.time() - start)
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)

if settings.Get("Console", "HideConsole", False):
    console.RestoreConsole()
    console.CloseConsole()