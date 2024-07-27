import src.uicomponents as uicomponents
import src.variables as variables
import src.settings as settings
import src.console as console

from PIL import Image, ImageTk
from tkinter import filedialog
from tkinter import ttk
import traceback
import tkinter
import sv_ttk
import numpy
import cv2
import os

def Initialize():
    width = settings.Get("UI", "width", 1000)
    height = settings.Get("UI", "height", 600)
    x = settings.Get("UI", "x", 0)
    y = settings.Get("UI", "y", 0)
    variables.THEME = settings.Get("UI", "theme", "dark")
    resizable = settings.Get("UI", "resizable", False)

    variables.ROOT = tkinter.Tk()
    variables.ROOT.title(variables.WINDOWNAME)
    variables.ROOT.geometry(f"{width}x{height}+{x}+{y}")
    variables.ROOT.update()
    sv_ttk.set_theme(variables.THEME, variables.ROOT)
    variables.ROOT.protocol("WM_DELETE_WINDOW", Close)
    variables.ROOT.resizable(resizable, resizable)
    variables.HWND = variables.ROOT.winfo_id()

    if os.name == "nt":
        from ctypes import windll, byref, sizeof, c_int
        variables.HWND = windll.user32.GetParent(variables.ROOT.winfo_id())
        windll.dwmapi.DwmSetWindowAttribute(variables.HWND, 35, byref(c_int(0xE7E7E7 if variables.THEME == "light" else 0x2F2F2F)), sizeof(c_int))
        if variables.THEME == "light":
            variables.ROOT.iconbitmap(default=f"{variables.PATH}assets/icon_light.ico")
        else:
            variables.ROOT.iconbitmap(default=f"{variables.PATH}assets/icon_dark.ico")

    global background
    background = numpy.zeros((variables.ROOT.winfo_height() - 40, variables.ROOT.winfo_width(), 3), numpy.uint8)
    background[:] = ((250, 250, 250) if variables.THEME == "light" else (28, 28, 28))

def Close():
    settings.Set("UI", "width", variables.ROOT.winfo_width())
    settings.Set("UI", "height", variables.ROOT.winfo_height())
    settings.Set("UI", "x", variables.ROOT.winfo_x())
    settings.Set("UI", "y", variables.ROOT.winfo_y())
    console.RestoreConsole()
    console.CloseConsole()
    variables.ROOT.destroy()
    variables.BREAK = True


def CreateUI():
    style = ttk.Style()
    style.layout("Tab",[('Notebook.tab',{'sticky':'nswe','children':[('Notebook.padding',{'side':'top','sticky':'nswe','children':[('Notebook.label',{'side':'top','sticky':''})],})],})])

    global tabControl
    tabControl = ttk.Notebook(variables.ROOT)
    tabControl.pack(expand = 1, fill="both")

    tab_annotate = ttk.Frame(tabControl)
    tab_annotate.grid_rowconfigure(0, weight=1)
    tab_annotate.grid_columnconfigure(0, weight=1)
    tabControl.add(tab_annotate, text='Annotate')

    tab_overview = ttk.Frame(tabControl)
    tabControl.add(tab_overview, text='Overview')

    tab_settings = ttk.Frame(tabControl)
    tabControl.add(tab_settings, text='Settings')


    global tk_frame
    tk_frame = tkinter.Label(tab_annotate, image=ImageTk.PhotoImage(Image.fromarray(background)))
    tk_frame.grid(row=0, column=0, padx=0, pady=0, columnspan=2)


    uicomponents.MakeLabel(tab_overview, "here it should show the assigned batches for the user and maybe stats or something", row=0, column=0, padx=15, pady=10, sticky="nw", font=("Segoe UI", 11))


    uicomponents.MakeLabel(tab_settings, "Theme:", row=0, column=0, padx=15, pady=10, sticky="nw", font=("Segoe UI", 11))
    def ChangeTheme(theme):
        variables.THEME = theme
        settings.Set("UI", "theme", variables.THEME)
        sv_ttk.set_theme(variables.THEME, variables.ROOT)
        style = ttk.Style()
        style.layout("Tab",[('Notebook.tab',{'sticky':'nswe','children':[('Notebook.padding',{'side':'top','sticky':'nswe','children':[('Notebook.label',{'side':'top','sticky':''})],})],})])
        global background
        background[:] = ((250, 250, 250) if variables.THEME == "light" else (28, 28, 28))
        if os.name == "nt":
            from ctypes import windll, byref, sizeof, c_int
            windll.dwmapi.DwmSetWindowAttribute(windll.user32.GetParent(variables.ROOT.winfo_id()), 35, byref(c_int(0xE7E7E7 if variables.THEME == "light" else 0x2F2F2F)), sizeof(c_int))
        if variables.THEME == "light":
            variables.ROOT.iconbitmap(default=f"{variables.PATH}assets/icon_light.ico")
        else:
            variables.ROOT.iconbitmap(default=f"{variables.PATH}assets/icon_dark.ico")
    theme = tkinter.StringVar(value=variables.THEME)
    ttk.Radiobutton(tab_settings, text="Light", command=lambda: ChangeTheme("light"), variable=theme, value="light").grid(row=1, column=0, padx=20, sticky="nw")
    ttk.Radiobutton(tab_settings, text="Dark", command=lambda: ChangeTheme("dark"), variable=theme, value="dark").grid(row=2, column=0, padx=20, sticky="nw")

    uicomponents.MakeLabel(tab_settings, "\nGeneral Settings", row=3, column=0, padx=15, pady=10, sticky="nw", font=("Segoe UI", 11))

    def ChangeHideConsole():
        if settings.Get("Console", "HideConsole"):
            console.HideConsole()
        else:
            console.RestoreConsole()
    uicomponents.MakeCheckButton(tab_settings, "Hide Console", "Console", "HideConsole", row=5, column=0, padx=20, pady=0, width=11, callback=lambda: ChangeHideConsole())

    def ChangeResizable():
        resizable = settings.Get("UI", "resizable", False)
        variables.ROOT.resizable(resizable, resizable)
        ChangeTheme(variables.THEME)
    uicomponents.MakeCheckButton(tab_settings, "Resizeable", "UI", "resizable", row=6, column=0, padx=20, pady=0, width=11, callback=lambda: ChangeResizable())