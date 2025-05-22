
from abc import ABC, abstractmethod
from enum import Enum, auto
import json
import random

from annotation_widgets.image.models import Label

from .figure_types import FigureTypes
from .models import Figure, Point, ReviewLabel
import numpy as np

from typing import Dict, List, Optional, Tuple

from enums import FigureType
from utils import HistoryBuffer

import cv2


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class AbstractFigureController(ABC):

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
        self.history: HistoryBuffer = HistoryBuffer(length=10)
        self.serialized_figures_buffer: List[Dict] = list()
        self.label_wheel_xc, self.label_wheel_yc = None, None

    def take_snapshot(self):
        self.history.add(
            [
                {"kwargs": figure.serialize(), "type": type(figure)}
                for figure in self.figures
            ]
        )

    def clear_history(self):
        self.history.clear()

    def update_figures_from_serialized(self, serialized):
        for figure in self.figures:
            figure.delete()
        self.figures = [value["type"](**value["kwargs"]) for value in serialized]

    def undo(self):
        serialized = self.history.get_previous()
        if serialized is None:
            return 
        self.update_figures_from_serialized(serialized)

    def redo(self):
        serialized = self.history.get_next()
        if serialized is None:
            return 
        self.update_figures_from_serialized(serialized)

    def update_label_wheel_coordinates(self):
        self.label_wheel_xc, self.label_wheel_yc = self.cursor_x, self.cursor_y

    @abstractmethod
    def copy(self):
        raise NotImplementedError

    @abstractmethod
    def paste(self):
        raise NotImplementedError

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
    def draw_additional_elements(self, canvas: np.ndarray, scale_factor: float = None) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def handle_space(self):
        raise NotImplementedError

    @abstractmethod
    def handle_esc(self):
        raise NotImplementedError


class ObjectFigureController(AbstractFigureController):

    def undo(self):
        super().undo()
        self.preview_figure = None
        self.start_point = None
        self.mode = Mode.IDLE
        self.update_selection(self.cursor_x, self.cursor_y)

    def redo(self):
        super().redo()
        self.preview_figure = None
        self.start_point = None
        self.mode = Mode.IDLE
        self.update_selection(self.cursor_x, self.cursor_y)

    def copy(self):
        self.serialized_figures_buffer = list()
        
        if self.selected_figure_id is not None:
            figures_to_add = [self.figures[self.selected_figure_id]]
        else:
            figures_to_add = [figure for figure in self.figures]
            
        for figure in figures_to_add:
            self.serialized_figures_buffer.append(
                {
                    "kwargs": figure.serialize(),
                    "type": type(figure)
                }
            )

    def paste(self):
        for figure in self.serialized_figures_buffer:
            self.figures.append(figure["type"](**figure["kwargs"]))
        self.take_snapshot()

    @property
    def current_figure_type(self) -> Figure:
        return FigureTypes[FigureType[self.active_label.type]]

    def get_selected_figure_id_and_point_id(self, x: int, y: int) -> Tuple[Optional[int], Optional[int]]:
        selected_figure_id, selected_point_id = None, None
        for figure_id, figure in sorted(enumerate(self.figures), key=lambda x: x[1].surface, reverse=True):
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
        figure: Figure = self.current_figure_type
        if self.start_point is not None:
            if self.preview_figure is not None and self.preview_figure.figure_type == figure.figure_type:
                figure_to_embed = self.preview_figure
            else:
                figure_to_embed = None
            self.preview_figure = figure.embed_to_bbox(
                start_point=self.start_point,
                end_point=(x, y),
                label=self.active_label,
                figure=figure_to_embed
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
            self.take_snapshot()
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
                self.take_snapshot()

    def handle_mouse_hover(self, x: int, y: int):
        if self.mode is Mode.CREATE:
            self.update_preview_figure(x, y)
        else:
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
            self.take_snapshot()

    def change_label(self, label: Label):
        self.active_label = label
        if self.selected_figure_id is not None:
            fig: Figure = self.figures[self.selected_figure_id]
            if fig.figure_type != label.type: # Disable active figure if figure types are different
                self.preview_figure = None
                self.start_point = None
                self.mode = Mode.IDLE
                self.selected_figure_id = None
                for figure in self.figures:
                    figure.active_point_id = None
                    figure.selected = False
            else:
                fig.label = self.active_label.name
            self.take_snapshot()

    def draw_additional_elements(self, canvas: np.ndarray, scale_factor: float = None) -> np.ndarray:
        if self.active_label.type == FigureType.BBOX.name:
            h, w, c = canvas.shape
            if scale_factor < 3:
                canvas = cv2.line(canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
                canvas = cv2.line(canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
                canvas = cv2.line(canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
                canvas = cv2.line(canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)
            else:
                canvas = cv2.line(canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (150, 150, 150), 1)
                canvas = cv2.line(canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (150, 150, 150), 1)
        return canvas

    def handle_space(self):
        pass

    def handle_esc(self):
        pass


