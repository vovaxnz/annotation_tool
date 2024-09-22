import math
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


def draw_class_selector(canvas: np.array, colors: List[Tuple[int, int, int]], text, highlight_id, center_x, center_y, edge_x, edge_y) -> np.ndarray:
    # Define the center and radius of the ring
    center = (center_x, center_y)
    outer_radius = 150
    inner_radius = int(outer_radius * 0.7)

    # Number of segments
    n_segments = len(colors)

    orig_canvas = np.copy(canvas)

    cv2.line(canvas, (center_x, center_y), (edge_x, edge_y), color=(255, 255, 255), thickness=2)

    # Draw each segment
    for i, color in enumerate(colors):
        start_angle = int(360 * (i / n_segments))
        end_angle = int(360 * ((i + 1) / n_segments))
        
        if i == highlight_id:
            sector_outer_radius = int(outer_radius * 1.1)
        else:
            sector_outer_radius = outer_radius
        cv2.ellipse(canvas, center, (sector_outer_radius, sector_outer_radius), 0, start_angle, end_angle, color, -1)
        
    # Set original image in the inner circle.
    mask = np.zeros_like(canvas)
    cv2.circle(mask, center, inner_radius, (255, 255, 255), -1)
    canvas[mask[:,:,0]>0] = orig_canvas[mask[:,:,0]>0]

    cv2.line(canvas, (center_x, center_y), (edge_x, edge_y), color=(255, 255, 255), thickness=2)

    textSize = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
    rect_h = textSize[1]
    rect_w = textSize[0]
    text_x = int(center_x - rect_w / 2)
    text_y = int(center_y + rect_h / 2)
    cv2.putText(canvas, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, colors[highlight_id], 2, cv2.LINE_AA)

    return canvas


def get_selected_sector_id(n_classes: int, center_x, center_y, edge_x, edge_y) -> int:
    # Calculate angle of the line
    line_angle = math.atan2(edge_y - center_y, edge_x - center_x)
    if line_angle < 0:
        line_angle += 2 * np.pi  # Normalize angle to be in the range 0 to 2*pi

    for i in range(n_classes):
        start_angle = int(360 * (i / n_classes))
        end_angle = int(360 * ((i + 1) / n_classes))

        # Convert angles to radians for calculation
        start_angle_rad = np.deg2rad(start_angle)
        end_angle_rad = np.deg2rad(end_angle)

        # Check if the line angle is within the segment
        line_in_sector = start_angle_rad <= line_angle < end_angle_rad
        if line_in_sector:
            return i


def create_class_selection_wheel(
        img: np.ndarray,
        classes: List[str],
        colors: List[Tuple[int, int, int]],
        center_x, 
        center_y, 
        edge_x, 
        edge_y
) -> np.ndarray:

    selected_id = get_selected_sector_id(n_classes=len(classes), center_x=center_x, center_y=center_y, edge_x=edge_x, edge_y=edge_y)

    result = draw_class_selector(
        canvas=img, 
        colors=colors, 
        center_x=center_x, 
        center_y=center_y, 
        edge_x=edge_x, 
        edge_y=edge_y,
        text=classes[selected_id],
        highlight_id=selected_id

    )
    return result
