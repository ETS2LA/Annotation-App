import src.variables as variables
import src.settings as settings
import src.console as console
import src.utils as utils
import src.ui as ui

import traceback
import threading
import requests
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

text, text_fontscale, text_thickness, text_width, text_height = utils.get_text_size(text = "Here is the cv2 frame to display the stuff",
                                                                                    text_width = 0.3 * ui.background.shape[1],
                                                                                    max_text_height = ui.background.shape[0])
cv2.putText(ui.background, text, (round(0.5 * ui.background.shape[1] - text_width / 2), round(0.5 * ui.background.shape[0] - text_height / 2)), cv2.FONT_HERSHEY_SIMPLEX, text_fontscale, (0, 255, 0), text_thickness)

while variables.BREAK == False:
    start = time.time()

    current_tab = ui.tabControl.tab(ui.tabControl.select(), "text")

    if current_tab == "Annotate":
        if ui.background.shape != (variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3):
            ui.background = ui.numpy.zeros((variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3), ui.numpy.uint8)
            ui.background[:] = ((250, 250, 250) if variables.THEME == "light" else (28, 28, 28))
        frame = ui.background.copy()

        frame = ui.ImageTk.PhotoImage(ui.Image.fromarray(frame))
        if last_frame != frame:
            ui.tk_frame.configure(image=frame)
            ui.tk_frame.image = frame
            last_frame = frame

    variables.ROOT.update()

    time_to_sleep = 1/variables.FPS - (time.time() - start)
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)

if settings.Get("Console", "HideConsole", False):
    console.RestoreConsole()
    console.CloseConsole()