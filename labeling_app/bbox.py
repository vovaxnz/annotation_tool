from controller import Mode
from enums import AnnotationMode, AnnotationStage
from labeling import LabelingApp
from models import BBox, Label, LabeledImage, Point


import cv2
import numpy as np


from typing import List, Optional, Tuple


class BboxLabelingApp(LabelingApp):

    def __init__(self, img_dir: str,  annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int):
        self.start_point: Optional[Tuple[int, int]] = None
        super().__init__(img_dir=img_dir, annotation_stage=annotation_stage, annotation_mode=annotation_mode, project_id=project_id)
        self.load_image()


    def draw_figure(self, canvas: np.ndarray, figure: BBox, highlight: bool = False) -> np.ndarray:
        """Drawing the bbox on the canvas"""

        line_width = max(1, int(5 / ((self.scale_factor + 1e-7) ** (1/3))))

        if highlight:
            if self.scale_factor < 3:
                line_width += 2
            else:
                line_width += 1

        label = Label.get_by_name(figure.label)

        for layer_id in range(line_width):
            canvas = cv2.rectangle(canvas, (int(figure.x1 - layer_id), int(figure.y1 - layer_id)), (int(figure.x2 + layer_id), int(figure.y2 + layer_id)), label.color_bgr, 1)

        if self.show_label_names:
            textSize = cv2.getTextSize(label.name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            padding = 5
            rect_x1 = figure.x1
            rect_y2 = figure.y1
            rect_h = textSize[1] + padding * 2
            rect_w = textSize[0] + padding * 2
            rect_x2 = rect_x1 + rect_w
            rect_y1 = rect_y2 - rect_h
            if rect_y1 < 0:
                rect_y1 = figure.y2
                rect_y2 = rect_y1 + rect_h
            text_x = rect_x1 + padding
            text_y = rect_y2 - padding
            cv2.rectangle(canvas, (rect_x1, rect_y1), (rect_x2, rect_y2), label.color_bgr, -1)
            if sum(label.color_bgr) / 3 > 120:
                text_color = (0, 0, 0)
            else:
                text_color = (255, 255, 255)
            cv2.putText(canvas, label.name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1, cv2.LINE_AA)

        for point in figure.points:
            if point.close_to(self.cursor_x, self.cursor_y):
                circle_radius = max(1, int(10 / ((self.scale_factor + 1e-7) ** (1/3))))
                cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (255, 255, 255), -1)
                cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (0, 0, 0), 2)

        return canvas

    def update_canvas(self):
        super().update_canvas()

        h, w, c = self.canvas.shape

        # Draw vertical and horizontal lines (black and white)
        self.canvas = cv2.line(self.canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
        self.canvas = cv2.line(self.canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
        self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
        self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)

        if self.start_point is not None:
            x1, x2 = sorted([self.cursor_x, self.start_point[0]])
            y1, y2 = sorted([self.cursor_y, self.start_point[1]])
            cv2.rectangle(self.canvas, (int(x1), int(y1)), (int(x2), int(y2)), self.active_label.color_bgr, 1)

    def get_rect_point_id(self, x: int, y: int) -> Tuple[Optional[int], Optional[int]]:
        for bbox_id, bbox in enumerate(self.figures):
            near_point_id = bbox.find_nearest_point_index(x, y)
            if near_point_id is not None:
                return bbox_id, near_point_id
        return None, None

    def get_selected_figure_id(self, x, y) -> Optional[int]:
        for bbox_id, bbox in enumerate(self.figures):
            if bbox.contains_point(Point(x, y)):
                return bbox_id
        bbox_id, near_point_id = self.get_rect_point_id(x, y)
        return bbox_id

    def add_bbox(self, x: int, y: int):
        if self.start_point is not None:
            x1 = min(self.start_point[0], x)
            y1 = min(self.start_point[1], y)
            x2 = max(self.start_point[0], x)
            y2 = max(self.start_point[1], y)
            bbox = BBox(x1, y1, x2, y2, self.active_label.name)
            self.figures.append(bbox)
        self.image_changed = True

    def release_bbox(self):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = None
            self.selected_figure_id = None
        self.image_changed = True

    def move_selected_bbox(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].move_active_point(x, y)
        self.image_changed = True

    @staticmethod
    def get_image_figures(image: LabeledImage) -> List[BBox]:
        return image.bboxes

    def save_image(self):
        if self.image_changed:
            image = LabeledImage.get(name=self.img_names[self.img_id])
            image.bboxes = self.figures
            image.trash = self.is_trash
            image.save()

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y
        if self.mode is Mode.MOVING:
            self.move_selected_bbox(x, y)
        self.update_canvas()

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode is Mode.MOVING:
            self.release_bbox()
            self.mode = Mode.IDLE
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.update_canvas()

    def handle_left_mouse_press(self, x: int, y: int):

        if self.mode is Mode.IDLE:
            rect_id, point_id = self.get_rect_point_id(x, y)
            if point_id is not None:
                self.selected_figure_id = rect_id
                self.figures[rect_id].active_point_id = point_id
                self.mode = Mode.MOVING
            else:
                self.start_point = (x, y)
                self.mode = Mode.CREATE

        elif self.mode is Mode.CREATE:
            if abs(self.start_point[0] - x) > self.min_movement_to_create and abs(self.start_point[1] - y) > self.min_movement_to_create:
                self.add_bbox(x, y)
            self.start_point = None
            self.mode = Mode.IDLE
            self.selected_figure_id = self.get_selected_figure_id(x, y)

        self.update_canvas()

    def handle_mouse_hover(self, x: int, y: int):
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.cursor_x, self.cursor_y = x, y
        self.update_canvas()