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
bounding_boxes = [] * len(images)

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
    
class BoundingBoxPlotter:
    def __init__(self, window_name: str, region_coords: tuple[int, int, int, int], updater_fps: int = 30, box_color: tuple = (0, 255, 0), box_thickness: int = 2) -> None:
        if not os.name == 'nt':
            raise UnsupportedOS('BoundingBoxPlotter is only supported on Windows.')

        self.window_x, self.window_y = 0, 0
        self.region_x1, self.region_y1, self.region_x2, self.region_y2 = region_coords
        self.window_name = window_name
        self.box_color = box_color
        self.temp_box_color = (144, 238, 144)  # Lighter green for temporary bounding box
        self.box_thickness = box_thickness
        self.updater_fps = updater_fps

        self.bounding_boxes = []  # List to store pairs of points for multiple bounding boxes
        self.redo_stack = []
        self.running = True
        self.mouse_x, self.mouse_y = (0, 0)
        self.mouse_clicked = False
        self.last_mouse_clicked = False

        self.zoom = 1.0  # Default zoom level
        self.offset_x, self.offset_y = 0, 0  # Image position offset

        self.update_thread = threading.Thread(target=self.update)
        self.update_thread.daemon = True
        self.update_thread.start()

    def set_zoom_and_position(self, zoom: float, offset_x: int, offset_y: int):
        """Set the current zoom level and image position (offset)."""
        self.zoom = zoom
        self.offset_x = offset_x
        self.offset_y = offset_y

    def _apply_zoom_and_offset(self, x: int, y: int) -> tuple[int, int]:
        """Adjust coordinates according to the current zoom level and position."""
        return int((x - self.offset_x) / self.zoom), int((y - self.offset_y) / self.zoom)

    def _reverse_zoom_and_offset(self, x: int, y: int) -> tuple[int, int]:
        """Reverse zoom and offset to calculate actual image coordinates."""
        return int(x * self.zoom + self.offset_x), int(y * self.zoom + self.offset_y)

    def change_region(self, region_coords: tuple[int, int, int, int]):
        self.region_x1, self.region_y1, self.region_x2, self.region_y2 = region_coords

    def _mouse_in_bounds(self) -> bool:
        return self.region_x1 <= self.mouse_x <= self.region_x2 and self.region_y1 <= self.mouse_y <= self.region_y2

    def _region_relative(self, x: int, y: int) -> tuple[int, int]:
        return x - self.region_x1, y - self.region_y1

    def _window_relative(self, x: int, y: int) -> tuple[int, int]:
        return x + self.region_x1, y + self.region_y1

    def _draw_bounding_boxes(self, frame):
        # Scale the box thickness based on the zoom level
        scaled_thickness = max(1, int(self.box_thickness * self.zoom))  # Ensure thickness is at least 1 pixel
        # Draw all bounding boxes that have both points
        for box in self.bounding_boxes:
            if len(box) == 2:  # Only draw if both points are available
                (x1, y1), (x2, y2) = box
                x1, y1 = self._reverse_zoom_and_offset(x1, y1)
                x2, y2 = self._reverse_zoom_and_offset(x2, y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.box_color, scaled_thickness)

    def _draw_temporary_box(self, frame):
        # Scale the box thickness based on the zoom level
        scaled_thickness = max(1, int(self.box_thickness * self.zoom))  # Ensure thickness is at least 1 pixel
        # Draw a temporary bounding box from the first clicked point to the current mouse position
        if len(self.bounding_boxes) > 0 and len(self.bounding_boxes[-1]) == 1:
            (x1, y1) = self.bounding_boxes[-1][0]
            x1, y1 = self._reverse_zoom_and_offset(x1, y1)
            mouse_x, mouse_y = self._reverse_zoom_and_offset(self.mouse_x, self.mouse_y)
            cv2.rectangle(frame, (x1, y1), (mouse_x, mouse_y), self.temp_box_color, scaled_thickness)

    def _draw_lines_to_mouse(self, frame):
        # Reverse zoom and offset for the mouse coordinates
        mouse_x, mouse_y = self._reverse_zoom_and_offset(self.mouse_x, self.mouse_y)

        # Draw horizontal line from left (region_x1) to right (region_x2) through the mouse's y-position
        cv2.line(frame, (self.region_x1, mouse_y), (self.region_x2, mouse_y), self.box_color, 1)

        # Draw vertical line from top (region_y1) to bottom (region_y2) through the mouse's x-position
        cv2.line(frame, (mouse_x, self.region_y1), (mouse_x, self.region_y2), self.box_color, 1)

    def update(self):
        while self.running:
            # Get current mouse position and adjust for window position
            rect = win32gui.GetClientRect(variables.HWND)
            tl = win32gui.ClientToScreen(variables.HWND, (rect[0], rect[1]))
            self.window_x, self.window_y = tl[0], tl[1] + 40
            self.mouse_x, self.mouse_y = mouse.get_position()
            self.mouse_x, self.mouse_y = self.mouse_x - self.window_x, self.mouse_y - self.window_y
            self.mouse_x, self.mouse_y = self._apply_zoom_and_offset(self.mouse_x, self.mouse_y)
            self.mouse_clicked = mouse.is_pressed(button="left")
            self.foreground = ctypes.windll.user32.GetForegroundWindow() == ctypes.windll.user32.FindWindowW(None, self.window_name)

            # Handle mouse click events
            if self.mouse_clicked != self.last_mouse_clicked and self.mouse_clicked:
                if self._mouse_in_bounds() and self.foreground:
                    if len(self.bounding_boxes) == 0 or len(self.bounding_boxes[-1]) == 2:
                        self.bounding_boxes.append([(self.mouse_x, self.mouse_y)])  # Start a new bounding box
                    else:
                        self.bounding_boxes[-1].append((self.mouse_x, self.mouse_y))  # Complete the current bounding box
                    self.redo_stack.clear()

            self.last_mouse_clicked = self.mouse_clicked
            time.sleep(1 / self.updater_fps)

    def render(self, frame: np.ndarray, zoom: float, offset_x: int, offset_y: int):
        # Set zoom and position for the current frame
        self.set_zoom_and_position(zoom, offset_x, offset_y)

        # Draw bounding boxes and other elements
        self._draw_bounding_boxes(frame)
        self._draw_lines_to_mouse(frame)

        # Draw a temporary bounding box if the user is in the process of drawing one
        self._draw_temporary_box(frame)

        # Optionally draw a circle at the mouse position
        if self._mouse_in_bounds():
            mouse_x, mouse_y = self._reverse_zoom_and_offset(self.mouse_x, self.mouse_y)
            cv2.circle(frame, (mouse_x, mouse_y), 5, self.box_color, -1)

    def get_boxes(self) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        return [self._region_relative(*p) for box in self.bounding_boxes for p in box]

    def clear(self) -> None:
        self.bounding_boxes = []
        self.redo_stack.clear()

    def undo(self) -> None:
        if len(self.bounding_boxes) > 0:
            self.redo_stack.append(self.bounding_boxes.pop())

    def redo(self) -> None:
        if len(self.redo_stack) > 0:
            self.bounding_boxes.append(self.redo_stack.pop())

    def stop(self) -> None:
        self.running = False
        self.update_thread.join()

window_width = settings.Get("UI", "width", 1280)
window_height = settings.Get("UI", "height", 720)

back_button = Button("<-", 0, window_height / 2 - 50, 50, window_height / 2 + 50, 20, variables.WINDOWNAME, 5, (255, 255, 255), (40, 40, 40), (50, 50, 50), (30, 30, 30))
forward_button = Button("->", window_width - 50, window_height / 2 - 50, window_width, window_height / 2 + 50, 20, variables.WINDOWNAME, 5, (255, 255, 255), (40, 40, 40), (50, 50, 50), (30, 30, 30))
back_button_clicked_last = False
forward_button_clicked_last = False

plotter = BoundingBoxPlotter(variables.WINDOWNAME, (0, 0, 0, 0))

index = 0
cached_zoom = None
cached_position = None
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
                plotter.change_region((image_x, image_y, image_x + new_overlay_width, image_y + new_overlay_height))
            except:
                pass
        
        new_overlay_height, new_overlay_width = resized_overlay_img.shape[:2]

        # Calculate top-left placement of the image considering zoom level
        image_x = round(-new_overlay_width // 2 + (POSITION[0] * 1 / ZOOM) * ZOOM)
        image_y = round(-new_overlay_height // 2 + (POSITION[1] * 1 / ZOOM) * ZOOM)

        if POSITION != cached_position:
            cached_position = POSITION
            plotter.change_region((image_x, image_y, image_x + new_overlay_width, image_y + new_overlay_height))

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
        plotter.render(frame, ZOOM, image_x, image_y)

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