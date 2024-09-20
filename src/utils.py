import mouse
import cv2

def get_text_size(text: str = "NONE", text_width: int = 100, fontsize: int = 11):
    fontscale = 1
    textsize, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, 1)
    width_current_text, height_current_text = textsize
    max_attempts = 3
    
    while (width_current_text != text_width or height_current_text > fontsize) and max_attempts > 0:
        scale_width = text_width / width_current_text if width_current_text != text_width else 1
        scale_height = fontsize / height_current_text if height_current_text > fontsize else 1
        fontscale *= min(scale_width, scale_height)
        textsize, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, 1)
        width_current_text, height_current_text = textsize
        max_attempts -= 1
    
    thickness = max(round(fontscale * 2), 1)
    return text, fontscale, thickness, width_current_text, height_current_text

def get_mouse_pos(window_x: int, window_y: int, window_relative: bool = True):
    mouse_x, mouse_y = mouse.get_position()
    if window_relative:
        return mouse_x - window_x, mouse_y - window_y
    return mouse_x, mouse_y