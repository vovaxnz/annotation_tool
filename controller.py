
from abc import ABC, abstractmethod
from enum import Enum, auto
import json

import cv2
import numpy as np
from config import ColorBGR
from enums import AnnotationMode, FigureType
from masks_encoding import get_empty_rle
from models import Figure, Label, Mask, Point, ReviewLabel, Value, FigureTypes



from typing import Dict, List, Optional, Tuple


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class FigureController(ABC):

    def __init__(self, active_label: Label):
        self.start_point: Optional[Tuple[int, int]] = None
        self.preview_figure: Figure = None
        self.selected_figure_id = None
        self.mode = Mode.IDLE
        self.active_label: Label = active_label
        self.cursor_x, self.cursor_y = 0, 0
        self.figures: List[Figure] = list()
        self.img_height, self.img_width = None, None
        self.shift_mode = False
        

    @abstractmethod
    def handle_mouse_move(self, x: int, y: int):
        raise NotImplementedError

    @abstractmethod
    def handle_left_mouse_release(self, x: int, y: int):
        raise NotImplementedError

    @abstractmethod
    def handle_left_mouse_press(self, x: int, y: int):
        raise NotImplementedError

    @abstractmethod
    def handle_mouse_hover(self, x: int, y: int):
        raise NotImplementedError

    @abstractmethod
    def delete_command(self):
        raise NotImplementedError

    @abstractmethod
    def change_label(self, label: Label):
        raise NotImplementedError

    @abstractmethod
    def draw_additional_elements(self, canvas: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def handle_space(self):
        raise NotImplementedError

    @abstractmethod
    def handle_esc(self):
        raise NotImplementedError


class ObjectFigureController:

    def __init__(self, active_label: Label):
        self.start_point: Optional[Tuple[int, int]] = None
        self.preview_figure: Figure = None
        self.selected_figure_id = None
        self.mode = Mode.IDLE
        self.active_label: Label = active_label
        self.cursor_x, self.cursor_y = 0, 0
        self.figures: List[Figure] = list()
        self.img_height, self.img_width = None, None
        self.shift_mode = False
        
    @property
    def current_figure_type(self) -> Figure:
        return FigureTypes[FigureType[self.active_label.type]]

    def get_selected_figure_id_and_point_id(self, x: int, y: int) -> Tuple[Optional[int], Optional[int]]:
        selected_figure_id, selected_point_id = None, None
        for figure_id, figure in enumerate(self.figures):
            near_point_id = figure.find_nearest_point_index(x, y)
            contains_point = figure.contains_point(Point(x, y))
            if contains_point:
                selected_figure_id = figure_id
            if near_point_id is not None:
                selected_figure_id, selected_point_id = figure_id, near_point_id
                break
        return selected_figure_id, selected_point_id

    def update_selection(self, x: int, y: int):
        for figure in self.figures:
            figure.active_point_id = None
            figure.selected = False
        self.selected_figure_id, near_point_id = self.get_selected_figure_id_and_point_id(x, y)
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = near_point_id
            self.figures[self.selected_figure_id].selected = True

    def update_preview_figure(self, x: int, y: int):
        figure_type: Figure = self.current_figure_type
        if self.start_point is not None:
            self.preview_figure = figure_type.embed_to_bbox(
                start_point=self.start_point, 
                end_point=(x, y), 
                label=self.active_label, 
                figure=self.preview_figure,
            )
        else:
            self.preview_figure = None

    def move_selected_figure(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].move_active_point(x, y)

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y
        if self.mode is Mode.MOVING:
            self.move_selected_figure(x, y)

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode is Mode.MOVING:
            self.mode = Mode.IDLE
        self.update_selection(x, y)

    def handle_left_mouse_press(self, x: int, y: int):
        if self.mode is Mode.IDLE:
            rect_id, point_id = self.get_selected_figure_id_and_point_id(x, y)
            if point_id is not None:
                self.selected_figure_id = rect_id
                self.figures[rect_id].active_point_id = point_id
                self.mode = Mode.MOVING
            elif self.current_figure_type is ReviewLabel: # Separating ReviewLabel because it is created with 1 click, not 2
                self.figures.append(ReviewLabel(x=self.cursor_x, y=self.cursor_y, label=self.active_label.name))
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
        self.selected_figure_id, near_point_id = self.get_selected_figure_id_and_point_id(self.cursor_x, self.cursor_y)
        if self.selected_figure_id is not None:
            figure = self.figures[self.selected_figure_id]
            figure.delete_point(near_point_id)
            if figure.point_number == 0:
                figure.delete()
                self.figures.pop(self.selected_figure_id)
                self.selected_figure_id, near_point_id = self.get_selected_figure_id_and_point_id(self.cursor_x, self.cursor_y)
            
    def change_label(self, label: Label):
        self.active_label = label
        if self.selected_figure_id is not None:
            fig: Figure = self.figures[self.selected_figure_id]
            if fig.figure_type == label.type:
                fig.label = self.active_label.name

    def draw_additional_elements(self, canvas: np.ndarray) -> np.ndarray:

        # Draw vertical and horizontal lines (black and white). Show only for bboxes
        if self.active_label.type == FigureType.BBOX.name:
            h, w, c = canvas.shape
            canvas = cv2.line(canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
            canvas = cv2.line(canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
            canvas = cv2.line(canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
            canvas = cv2.line(canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)
        return canvas

    def handle_space(self):
        pass

    def handle_esc(self):
        pass

class MaskFigureController(FigureController):

    def __init__(self, active_label: Label):
        self.adding_mask = True
        self.start_point: Optional[Tuple[int, int]] = None
        self.preview_figure: Figure = None
        self.selected_figure_id = None
        self.mode = Mode.IDLE
        self.active_label: Label = active_label
        self.cursor_x, self.cursor_y = 0, 0
        self.figures_dict = dict()
        self.img_height, self.img_width = None, None
        self.shift_mode = False
        self.lock_distance = 4

    @property
    def figures(self) -> List[Figure]:
        result_list = list()
        last_figure = None
        for label_name in self.figures_dict.keys():
            if label_name == self.active_label.name:
                last_figure = self.figures_dict[label_name]
            else:
                result_list.append(self.figures_dict[label_name])
        
        if last_figure is not None:
            result_list.append(last_figure)
        
        return result_list

    @figures.setter
    def figures(self, figures: List[Mask]):
        self.figures_dict = {figure.label: figure for figure in figures}
        if len(self.figures_dict) < len(figures):
            raise RuntimeError(f"Number of masks {len(figures)} are larger than the number of classes {len(self.figures_dict)}. Annotations are incorrect. Ask to fix initial annotations")

    @property
    def addition_mode(self) -> bool:
        return not self.shift_mode

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode is Mode.MOVING:
            self.mode = Mode.IDLE

    def handle_left_mouse_press(self, x: int, y: int):
        if self.mode is Mode.IDLE:
            self.mode = Mode.CREATE
            self.polygon = [(x, y), (x, y)]
        elif self.mode is Mode.CREATE:
            if self.check_cursor_on_polygon_start():
                self.edit_mask(adding=self.addition_mode)
                self.polygon = list()
                self.mode = Mode.IDLE
            else:
                self.polygon.append((x, y))

    def handle_mouse_hover(self, x: int, y: int):
        if self.mode == Mode.CREATE:
            self.polygon[-1] = (x, y)
        self.cursor_x, self.cursor_y = x, y

    def edit_mask(self, adding: bool):
        self.polygon[-1] = self.polygon[0]
        figure = self.figures_dict.get(self.active_label.name)
        if figure is None:
            figure = Mask(
                label=self.active_label.name,
                rle=get_empty_rle(height=self.img_height, width=self.img_width),
                height=self.img_height,
                width=self.img_width,
            )
            self.figures_dict[self.active_label.name] = figure

        # Define your polygon points
        polygon = np.array(self.polygon, np.int32).reshape((-1, 1, 2))

        # Use polygon points to remove/add part of class mask
        figure.mask = cv2.fillPoly(figure.mask, [polygon], color=1 if adding else 0)

        # Update figure rle
        figure.encode_mask()

    def handle_space(self):
        if self.mode is Mode.CREATE:
            self.edit_mask(adding=self.addition_mode)
            self.polygon = list()
            self.mode = Mode.IDLE

    def handle_esc(self):
        if self.mode == Mode.CREATE:
            self.polygon = list()
            self.mode = Mode.IDLE

    def delete_command(self):
        # Delete class with active label (does not matter where is cursor)
        self.figures_dict[self.active_label.name].delete()
        self.figures_dict[self.active_label.name] = Mask(
            label=self.active_label.name,
            rle=get_empty_rle(height=self.img_height, width=self.img_width),
            height=self.img_height,
            width=self.img_width,
        )

    def change_label(self, label: Label):
        self.active_label = label

    def check_cursor_on_polygon_start(self) -> bool:
        return len(self.polygon) > 2 and Point(*self.polygon[0]).close_to(self.cursor_x, self.cursor_y, distance=self.lock_distance)

    def draw_additional_elements(self, canvas: np.ndarray) -> np.ndarray:
        if self.mode is Mode.CREATE:
            for i in range(len(self.polygon) - 1):
                p1 = self.polygon[i]
                p2 = self.polygon[i+1]

                if self.addition_mode:
                    line_color = ColorBGR.white
                else:
                    line_color = ColorBGR.red
                canvas = cv2.line(canvas, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), line_color, 1)

            if self.check_cursor_on_polygon_start():
                cv2.circle(canvas, self.polygon[0], self.lock_distance, (255, 255, 255), 1)
            
        return canvas
        

ControllerByMode = {
    AnnotationMode.OBJECT_DETECTION: ObjectFigureController,
    AnnotationMode.KEYPOINTS: ObjectFigureController,
    AnnotationMode.SEGMENTATION: MaskFigureController
}