from config import AnnotationMode, AnnotationStage
from labeling_app.labeling import LabelingApp, Mode, Visualizable
from models import IssueName, Label, LabeledImage, Point, ReviewLabel


import cv2
import numpy as np


from typing import List, Optional


class ReviewLabelingApp(LabelingApp):

    def __init__(self, img_dir: str,  annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int, secondary_visualizer: Visualizable = None):
        super().__init__(img_dir=img_dir, annotation_stage=annotation_stage, annotation_mode=annotation_mode, project_id=project_id, secondary_visualizer=secondary_visualizer)
        self.load_image()
        self.active_label: Label = IssueName.first()

    def draw_figure(self, canvas: np.ndarray, figure: ReviewLabel, highlight: bool = False) -> np.ndarray:

        circle_radius = max(1, int(7 / ((self.scale_factor + 1e-7) ** (1/3))))

        if highlight:
            circle_radius += 3

        label = IssueName.get_by_name(figure.text)
        if label is None:
            return canvas

        textSize = cv2.getTextSize(label.name, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]

        img_h, img_w, c = canvas.shape
        padding = 10

        rect_x_shift = 40
        rect_y_shift = 40

        rect_x1 = figure.x + rect_x_shift
        rect_y2 = figure.y - rect_y_shift

        rect_h = textSize[1] + padding * 2
        rect_w = textSize[0] + padding * 2

        rect_x2 = rect_x1 + rect_w
        rect_y1 = rect_y2 - rect_h

        if rect_x1 < 0:
            rect_x1 = max(rect_x1, 0)

        if rect_y1 < 0:
            rect_y1 += rect_y_shift * 2 + rect_h
            rect_y1 = max(rect_y1, 0)

        if rect_x2 > img_w:
            rect_x1 -= rect_x_shift * 2 + rect_w
            rect_x1 = min(rect_x1, img_w - rect_w)

        if rect_y2 > img_h:
            rect_y1 = min(rect_y1, img_h - rect_h)

        rect_x2 = rect_x1 + rect_w
        rect_y2 = rect_y1 + rect_h

        text_x = rect_x1 + padding
        text_y = rect_y2 - padding

        if abs(rect_x1 - figure.x) > abs(rect_x2 - figure.x):
            line_p2_x = rect_x2
        else:
            line_p2_x = rect_x1
        if abs(rect_y1 - figure.y) > abs(rect_y2 - figure.y):
            line_p2_y = rect_y2
        else:
            line_p2_y = rect_y1

        cv2.line(canvas, (int(figure.x), int(figure.y)), (line_p2_x, line_p2_y), (255, 255, 255), 8)
        cv2.circle(canvas, (int(figure.x), int(figure.y)), circle_radius + 4, (255, 255, 255), 2)
        cv2.rectangle(canvas, (rect_x1-4, rect_y1-4), (rect_x2+4, rect_y2+4), (255, 255, 255), 2)
        cv2.line(canvas, (int(figure.x), int(figure.y)), (line_p2_x, line_p2_y), (0, 0, 0), 4)
        cv2.circle(canvas, (int(figure.x), int(figure.y)), circle_radius, label.color_bgr, -1)
        cv2.rectangle(canvas, (rect_x1, rect_y1), (rect_x2, rect_y2), label.color_bgr, -1)
        cv2.circle(canvas, (int(figure.x), int(figure.y)), circle_radius + 1, (0, 0, 0), 2)
        cv2.rectangle(canvas, (rect_x1-2, rect_y1-2), (rect_x2+2, rect_y2+2), (0, 0, 0), 2)

        if sum(label.color_bgr) / 3 > 120:
            text_color = (0, 0, 0)
        else:
            text_color = (255, 255, 255)

        cv2.putText(canvas, label.name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)

        return canvas

    def get_selected_figure_id(self, x, y) -> Optional[int]:
        for point_id, point in enumerate(self.figures):
            if Point(point.x, point.y).close_to(self.cursor_x, self.cursor_y, distance=30):
                return point_id

    def add_point(self, x: int, y: int):
        rl = ReviewLabel(x=x, y=y, text=self.active_label.name)
        self.figures.append(rl)
        self.image_changed = True

    def move_selected_point(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].x = int(x)
            self.figures[self.selected_figure_id].y = int(y)
        self.image_changed = True

    @staticmethod
    def get_image_figures(image: LabeledImage) -> List[ReviewLabel]:
        return image.review_labels

    def save_image(self):
        if self.image_changed:
            image = LabeledImage.get(name=self.img_names[self.img_id])
            image.review_labels = self.figures
            image.reviewed = True
            image.save()

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y
        if self.mode == Mode.MOVING:
            self.move_selected_point(x, y)
        self.update_canvas()

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode == Mode.MOVING:
            self.mode = Mode.IDLE
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.update_canvas()

    def handle_left_mouse_press(self, x: int, y: int):
        if self.mode == Mode.IDLE:
            point_id = self.get_selected_figure_id(x, y)
            if point_id is not None:
                self.selected_figure_id = point_id
                self.mode = Mode.MOVING
            else:
                self.add_point(x, y)

    def handle_mouse_hover(self, x: int, y: int):
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.cursor_x, self.cursor_y = x, y
        self.update_canvas()

    def toggle_image_trash_tag(self):
        pass

    def change_label(self, label_hotkey: int):
        label = IssueName.get_by_hotkey(label_hotkey)
        if label is not None:
            self.active_label = label

            if self.selected_figure_id is not None:
                self.figures[self.selected_figure_id].text = self.active_label.name
                self.update_canvas()
        self.image_changed = True