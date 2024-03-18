
from enum import Enum, auto
import json

import cv2
import numpy as np
from enums import AnnotationMode, FigureType
from models import Figure, Label, ReviewLabel, Value, FigureTypes



from typing import Dict, List, Optional, Tuple


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class ObjectFigureController:

    def __init__(self, active_label: Label):
        self.start_point: Optional[Tuple[int, int]] = None
        self.preview_figure: Figure = None
        self.selected_figure_id = None
        self.mode = Mode.IDLE
        self.active_label: Label = active_label
        self.cursor_x, self.cursor_y = 0, 0
        self.figures: List[Figure] = list()
        self.keypoint_info: Dict = json.loads(Value.get_value("keypoint_info")) # TODO: Refactor

    @property
    def current_figure_type(self) -> Figure:
        return FigureTypes[FigureType[self.active_label.type]]

    def get_figure_point_id(self, x: int, y: int) -> Tuple[Optional[int], Optional[int]]:
        for figure_id, figure in enumerate(self.figures):
            near_point_id = figure.find_nearest_point_index(x, y)
            if near_point_id is not None:
                return figure_id, near_point_id
        return None, None

    def get_selected_figure_id(self, x: int, y: int) -> Optional[int]:
        selected_figure_id, near_point_id = self.get_figure_point_id(x, y)
        return selected_figure_id

    def update_selection(self, x: int, y: int):
        self.selected_figure_id, near_point_id = self.get_figure_point_id(x, y)
        for figure in self.figures:
            figure.active_point_id = None
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = near_point_id

    def update_preview_figure(self, x: int, y: int):
        figure_type: Figure = self.current_figure_type
        if self.start_point is not None:
            self.preview_figure = figure_type.embed_to_bbox(
                label_name=self.active_label.name, 
                keypoint_info=self.keypoint_info,
                start_point=self.start_point, 
                end_point=(x, y), 
            )
        else:
            self.preview_figure = None

    def release_figure(self):
        if self.selected_figure_id is not None:
            figure = self.figures[self.selected_figure_id]
            figure.active_point_id = None
            self.selected_figure_id = None

    def move_selected_figure(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].move_active_point(x, y)

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y
        if self.mode is Mode.MOVING:
            self.move_selected_figure(x, y)

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode is Mode.MOVING:
            self.release_figure()
            self.mode = Mode.IDLE
        self.update_selection(x, y)

    def handle_left_mouse_press(self, x: int, y: int):
        if self.mode is Mode.IDLE:
            rect_id, point_id = self.get_figure_point_id(x, y)
            if point_id is not None:
                self.selected_figure_id = rect_id
                self.figures[rect_id].active_point_id = point_id
                self.mode = Mode.MOVING
            elif self.current_figure_type is ReviewLabel: # Separating ReviewLabel because it is created with 1 click, not 2
                self.figures.append(ReviewLabel(x=self.cursor_x, y=self.cursor_y, text=self.active_label.name))
                self.update_selection(x, y)
            else:
                self.start_point = (x, y)
                self.mode = Mode.CREATE

        elif self.mode is Mode.CREATE:
            if self.preview_figure is not None:
                self.figures.append(self.preview_figure)
                self.preview_figure = None
                self.start_point = None
                self.mode = Mode.IDLE
                self.update_selection(x, y)

    def handle_mouse_hover(self, x: int, y: int):
        if self.mode is Mode.CREATE:
            self.update_preview_figure(x, y)
        self.update_selection(x, y)
        self.cursor_x, self.cursor_y = x, y

    def delete_command(self):
        self.selected_figure_id, near_point_id = self.get_figure_point_id(self.cursor_x, self.cursor_y)
        if self.selected_figure_id is not None:
            figure = self.figures[self.selected_figure_id]
            figure.delete_point(near_point_id)
            if figure.point_number == 0:
                figure.delete()
                self.figures.pop(self.selected_figure_id)
                self.selected_figure_id = self.get_selected_figure_id(self.cursor_x, self.cursor_y)
            
    def change_label(self, label: Label):
        self.active_label = label
        if self.selected_figure_id is not None:
            fig = self.figures[self.selected_figure_id]
            if fig.label.type == label.type:
                fig.label = self.active_label.name

    def draw_help_lines(self, canvas: np.ndarray) -> np.ndarray:
        h, w, c = canvas.shape
        canvas = cv2.line(canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
        canvas = cv2.line(canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
        canvas = cv2.line(canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
        canvas = cv2.line(canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)
        return canvas
    

ControllerByMode = {
    AnnotationMode.OBJECT_DETECTION: ObjectFigureController,
    AnnotationMode.KEYPOINTS: ObjectFigureController,
    AnnotationMode.REVIEW: ObjectFigureController,
    # FigureType.MASK: MaskFigureController
}