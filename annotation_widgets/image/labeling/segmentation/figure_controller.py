from annotation_widgets.image.models import Label
import cv2
from annotation_widgets.image.labeling.models import Figure
from annotation_widgets.image.labeling.segmentation.models import Mask
from config import ColorBGR
from annotation_widgets.image.labeling.figure_controller import AbstractFigureController, Mode
from annotation_widgets.image.labeling.segmentation.masks_encoding import get_empty_rle
from annotation_widgets.image.labeling.models import Point


import numpy as np


from typing import List


class MaskFigureController(AbstractFigureController):

    def __init__(self, active_label: Label):
        super().__init__(active_label)

        self.adding_mask = True
        self.figures_dict = dict()
        self.lock_distance = 4

    def undo(self):
        super().undo()
        self.mode = Mode.IDLE
        self.polygon = list()

    def redo(self):
        super().redo()
        self.mode = Mode.IDLE
        self.polygon = list()

    def copy(self):
        if self.figures_dict.get(self.active_label.name) is not None:
            self.serialized_figures_buffer = [{
                "kwargs": self.figures_dict[self.active_label.name].serialize(),
                "type": type(self.figures_dict[self.active_label.name])
            }]

    def paste(self):
        for figure in self.serialized_figures_buffer:
            fig_type = figure["type"]
            fig_kwargs = figure["kwargs"]
            label = fig_kwargs["label"]
            self.figures_dict[label] = fig_type(**fig_kwargs)
        self.take_snapshot()

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
        self.polygon.append((self.cursor_x, self.cursor_y))
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

        self.take_snapshot()

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
        if self.figures_dict.get(self.active_label.name) is not None:
            self.figures_dict[self.active_label.name].delete()
            self.figures_dict[self.active_label.name] = Mask(
                label=self.active_label.name,
                rle=get_empty_rle(height=self.img_height, width=self.img_width),
                height=self.img_height,
                width=self.img_width,
            )
            self.take_snapshot()

    def change_label(self, label: Label):
        self.active_label = label

    def check_cursor_on_polygon_start(self) -> bool:
        return len(self.polygon) > 2 and Point(*self.polygon[0]).close_to(self.cursor_x, self.cursor_y, distance=self.lock_distance)

    def draw_additional_elements(self, canvas: np.ndarray, scale_factor: float = None) -> np.ndarray:
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