from config import ColorBGR
import cv2
import numpy as np


from typing import Dict, List, Optional, Tuple


def draw_text_label(canvas, text: str, x: int, y: int, color_bgr: Tuple[int, int, int], padding = 5, under_point: bool = True):
    textSize = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    rect_x1 = x
    rect_w = textSize[0] + padding * 2
    rect_x2 = rect_x1 + rect_w
    text_x = rect_x1 + padding
    
    rect_h = textSize[1] + padding * 2

    if under_point:
        rect_y2 = y
        rect_y1 = rect_y2 - rect_h
    else:
        rect_y1 = y
        rect_y2 = rect_y1 + rect_h

    text_y = rect_y2 - padding

    cv2.rectangle(canvas, (rect_x1, rect_y1), (rect_x2, rect_y2), color_bgr, -1)
    if sum(color_bgr) / 3 > 120:
        text_color = (0, 0, 0)
    else:
        text_color = (255, 255, 255)
    cv2.putText(canvas, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1, cv2.LINE_AA)