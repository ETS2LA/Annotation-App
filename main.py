import src.localserver as localserver
import src.variables as variables
import src.settings as settings
import src.console as console
import src.utils as utils
import src.ui as ui

import numpy as np
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

images = localserver.LoadLocalImages()
ui.Initialize()
ui.CreateUI()

last_frame = None
last_inputs = None
current_tab = None
last_theme = variables.THEME

def MouseHandler():
    global last_middle_clicked, last_right_clicked, middle_clicked, right_clicked, last_mouse_x, last_mouse_y, mouse_x, mouse_y, move_start
    last_middle_clicked = False
    last_right_clicked = False
    middle_clicked = False
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

        # Detect middle click for movement and right click for other actions
        middle_clicked = ctypes.windll.user32.GetKeyState(0x04) & 0x8000 != 0 and window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height
        right_clicked = ctypes.windll.user32.GetKeyState(0x02) & 0x8000 != 0 and window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height

        # If mouse is within the window
        if window_x <= mouse_x <= window_x + window_width and window_y <= mouse_y <= window_y + window_height:
            with pynput.mouse.Events() as events:
                event = events.get()
                # Handle zoom with mouse scroll
                if isinstance(event, pynput.mouse.Events.Scroll):
                    # Get canvas coordinates for proper zoom
                    canvas_x = (mouse_x - window_x - variables.POSITION[0]) / variables.ZOOM
                    canvas_y = (mouse_y - window_y - variables.POSITION[1]) / variables.ZOOM
                    # Adjust zoom, with upper and lower limits
                    if variables.ZOOM < 10000:
                        variables.ZOOM = variables.ZOOM * 1.1 if event.dy > 0 else variables.ZOOM / 1.1
                    elif event.dy < 0:
                        variables.ZOOM /= 1.1
                    # Adjust the position so zoom is centered on mouse location
                    variables.POSITION = (mouse_x - window_x - canvas_x * variables.ZOOM, mouse_y - window_y - canvas_y * variables.ZOOM)

            # Handle movement with middle click
            if middle_clicked:
                if not last_middle_clicked:
                    # Store the starting point of the movement
                    move_start = mouse_x - variables.POSITION[0], mouse_y - variables.POSITION[1]
                else:
                    # Update the position based on movement
                    variables.POSITION = (mouse_x - move_start[0], mouse_y - move_start[1])

        last_mouse_x, last_mouse_y = mouse_x, mouse_y
        last_middle_clicked, last_right_clicked = middle_clicked, right_clicked

        time_to_sleep = 1/variables.FPS - (time.time() - start)
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
threading.Thread(target=MouseHandler, daemon=True).start()

def KeyHandler():
    global pressed_keys
    pressed_keys = []
    keyshortcuts_back = settings.Get("Keybinds", "Back", "ctrl+z")
    keyshortcuts_forward = settings.Get("Keybinds", "Forward", "ctrl+y")
    keyshortcuts_classes = [settings.Get("Keybinds", classname, str(i + 1)) if len(str(i + 1)) == 1 else settings.Get("Keybinds", classname, chr(i + 88).lower()) for i, classname in enumerate(variables.CLASSES)]
    def check_key_combination(combination):
        special_keys = {
            "ctrl": 0x11,   # VK_CONTROL
            "shift": 0x10,  # VK_SHIFT
            "alt": 0x12     # VK_MENU
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

class Button:
    def __init__(self, text: str, x1: int, y1: int, x2: int, y2: int, fontsize: int, window_name : str, round_corners: int = 5,
                 text_color: tuple = (255, 255, 255), button_color: tuple = (40, 40, 40),
                 button_hover_color: tuple = (50, 50, 50), button_selected_color: tuple = (30, 30, 30)) -> None:
        self.text = text
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.fontsize = fontsize
        self.window_name = window_name
        self.round_corners = round_corners
        self.text_color = text_color
        self.button_color = button_color
        self.button_hover_color = button_hover_color
        self.button_selected_color = button_selected_color
        self.button_selected = False
        self.button_hovered = False

        self.text, self.text_fontscale, self.text_thickness, self.text_width, self.text_height = utils.get_text_size(text, x2 - x1, fontsize)

    def render(self, frame):
        rect = win32gui.GetClientRect(variables.HWND)
        tl = win32gui.ClientToScreen(variables.HWND, (rect[0], rect[1]))
        window_x, window_y = tl[0], tl[1] + 40

        relative_mouse_x, relative_mouse_y = utils.get_mouse_pos(window_x, window_y)
        mouse_clicked = mouse.is_pressed(button="left")
        
        if self._is_mouse_inside_button(relative_mouse_x, relative_mouse_y):
            if mouse_clicked:
                self._select_button()
            else:
                self._hover_button()
        else:
            self._reset_button()

        self._draw_button(frame)

    def _select_button(self):
        self.button_hovered = False
        self.button_selected = True
        
    def _hover_button(self):
        self.button_hovered = True
        self.button_selected = False

    def _reset_button(self):
        self.button_hovered = False
        self.button_selected = False

    def _is_mouse_inside_button(self, mouse_x, mouse_y):
        return self.x1 <= mouse_x <= self.x2 and self.y1 <= mouse_y <= self.y2

    def _draw_button(self, frame: np.ndarray):
        button_color = self._get_button_color()
        cv2.rectangle(frame, (round(self.x1 + self.round_corners / 2), round(self.y1 + self.round_corners / 2)),
                      (round(self.x2 - self.round_corners / 2), round(self.y2 - self.round_corners / 2)),
                      button_color, self.round_corners, cv2.LINE_AA)
        cv2.rectangle(frame, (round(self.x1 + self.round_corners / 2), round(self.y1 + self.round_corners / 2)),
                      (round(self.x2 - self.round_corners / 2), round(self.y2 - self.round_corners / 2)),
                      button_color, -1, cv2.LINE_AA)
        cv2.putText(frame, self.text, 
                    (round(self.x1 + (self.x2 - self.x1) / 2 - self.text_width / 2),
                     round(self.y1 + (self.y2 - self.y1) / 2 + self.text_height / 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, self.text_fontscale, self.text_color, self.text_thickness, cv2.LINE_AA)

    def _get_button_color(self):
        if self.button_selected:
            return self.button_selected_color
        if self.button_hovered:
            return self.button_hover_color
        return self.button_color

    def hovered(self):
        return self.button_hovered

    def selected(self):
        return self.button_selected

window_width = settings.Get("UI", "width", 1280)
window_height = settings.Get("UI", "height", 720)

back_button = Button("<-", 0, window_height / 2 - 50, 50, window_height / 2 + 50, 20, variables.WINDOWNAME, 5, (255, 255, 255), (40, 40, 40), (50, 50, 50), (30, 30, 30))
forward_button = Button("->", window_width - 50, window_height / 2 - 50, window_width, window_height / 2 + 50, 20, variables.WINDOWNAME, 5, (255, 255, 255), (40, 40, 40), (50, 50, 50), (30, 30, 30))
back_button_clicked_last = False
forward_button_clicked_last = False

index = 0
cached_zoom = None
resized_overlay_img = None

while not variables.BREAK:
    start = time.time()

    current_tab = ui.tabControl.tab(ui.tabControl.select(), "text")
    inputs = [variables.POSITION, variables.ZOOM, middle_clicked, right_clicked, pressed_keys]

    if current_tab == "Annotate":
        if ui.background.shape != (variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3):
            if variables.THEME == "dark":
                ui.background = ui.numpy.zeros((variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3), ui.numpy.uint8)
            else:
                ui.background = ui.numpy.ones((variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3), ui.numpy.uint8)

        frame = ui.background.copy()

        POSITION = variables.POSITION
        ZOOM = variables.ZOOM

        # Resize image only when ZOOM changes (caching mechanism)
        if ZOOM != cached_zoom:
            overlay_img = images[index][1]
            overlay_height, overlay_width = overlay_img.shape[:2]
            try:
                resized_overlay_img = cv2.resize(overlay_img, (int(overlay_width * ZOOM), int(overlay_height * ZOOM)))
                cached_zoom = ZOOM
            except:
                pass

        new_overlay_height, new_overlay_width = resized_overlay_img.shape[:2]

        # Calculate top-left placement of the image considering zoom level
        image_x = round(-new_overlay_width // 2 + (POSITION[0] * 1 / ZOOM) * ZOOM)
        image_y = round(-new_overlay_height // 2 + (POSITION[1] * 1 / ZOOM) * ZOOM)

        # Calculate visible bounds to avoid processing unnecessary parts
        x_offset = max(0, -image_x)
        y_offset = max(0, -image_y)
        visible_width = min(new_overlay_width - x_offset, frame.shape[1] - max(0, image_x))
        visible_height = min(new_overlay_height - y_offset, frame.shape[0] - max(0, image_y))

        # Only overlay visible portions
        if visible_width > 0 and visible_height > 0:
            frame[max(0, image_y):max(0, image_y) + visible_height, max(0, image_x):max(0, image_x) + visible_width] = \
                resized_overlay_img[y_offset:y_offset + visible_height, x_offset:x_offset + visible_width]

        # Render UI elements
        back_button.render(frame)
        forward_button.render(frame)

        if back_button.selected() and not back_button_clicked_last:
            index = max(0, index - 1)
            back_button_clicked_last = True
        else:
            back_button_clicked_last = False

        if forward_button.selected() and not forward_button_clicked_last:
            index = min(len(images) - 1, index + 1)
            forward_button_clicked_last = True
        else:
            forward_button_clicked_last = False

        # Update the UI only if the frame changes
        new_frame = ui.ImageTk.PhotoImage(ui.Image.fromarray(frame))
        if last_frame != new_frame:
            ui.tk_frame.configure(image=new_frame)
            ui.tk_frame.image = new_frame
            last_frame = new_frame

        last_inputs = inputs
        last_theme = variables.THEME

    variables.ROOT.update()

    # FPS regulation
    time_to_sleep = 1 / variables.FPS - (time.time() - start)
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)


if settings.Get("Console", "HideConsole", False):
    console.RestoreConsole()
    console.CloseConsole()