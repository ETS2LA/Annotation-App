import src.settings as settings
import mss
import os

ROOT = None
HWND = None
BREAK = False
PATH = os.path.dirname(__file__).replace("src", "")

OS = os.name
with open(PATH + "version.txt") as f: VERSION = f.read()

RUN = True
WINDOWNAME = "Annotation App"

WEBSERVER_URL = "https://data.ets2la.com/api"

CLASSES = ["car", "truck", "van", "bus", "stop_sign", "yield_sign", "speedlimit_sign", "info_sign", "mandatory_sign", "warning_sign", "priority_sign",
           "prohibitary_sign", "regulatory_sign", "service_sign", "railroad_sign", "additional_sing", "road_marker", "traffic_cone", "green_traffic_light",
           "yellow_traffic_light", "red_traffic_light", "road_marking"]  # THIS IS TEMPORARILY HARDCODED FOR NOW

FPS = 60
THEME = settings.Get("UI", "theme", "dark")

ZOOM = 1
POSITION = (settings.Get("UI", "width", 1280)) // 2, (settings.Get("UI", "height", 720) - 40) // 2

sct = mss.mss()
SCRENN_X = sct.monitors[1]["left"]
SCRENN_Y = sct.monitors[1]["top"]
SCREEN_WIDTH = sct.monitors[1]["width"]
SCREEN_HEIGHT = sct.monitors[1]["height"]

CONSOLENAME = None
CONSOLEHWND = None

RED = "\033[91m"
GREEN = "\033[92m"
ORANGE = "\033[93m"
NORMAL = "\033[0m"