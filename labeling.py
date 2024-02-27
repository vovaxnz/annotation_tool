
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from enum import Enum, auto

from exceptions import MessageBoxException
from models import IssueName, Label, LabeledImage, BBox, Point, ReviewLabel, Value
from config import address


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class AnnotationMode(Enum):
    OBJECT_DETECTION = "OBJECT_DETECTION"
    SEGMENTATION = "SEGMENTATION"
    REVIEW = "REVIEW"


class AnnotationStage(Enum):
    ANNOTATE = "ANNOTATE"
    REVIEW = "REVIEW"
    CORRECTION = "CORRECTION"
    DONE = "DONE"

@dataclass
class StatusData:
    selected_class: str
    class_color: str
    is_trash: bool
    annotation_mode: str
    annotation_stage: str
    speed_per_hour: float
    img_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_images: int
    figures_hidden: bool
    secondary_figures_hidden: bool


class Visualizable(ABC):

    @abstractmethod
    def draw_figures(self, canvas: np.ndarray, limage: LabeledImage) -> np.ndarray:
        raise NotImplementedError


class LabelingApp(Visualizable, ABC):

    def __init__(self, img_dir: str, annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int, secondary_visualizer: Visualizable = None):
        self.secondary_visualizer = secondary_visualizer 
        
        self.img_names = sorted(os.listdir(img_dir)) 
        
        if annotation_stage is AnnotationStage.CORRECTION:
            self.img_names = [img_name for img_name in self.img_names if len(LabeledImage.get(name=img_name).review_labels) > 0]

        for img_name in self.img_names: # Check that images from the directory are in the the database
            img_object = LabeledImage.get(name=img_name)
            if img_object is None:
                raise MessageBoxException(f"{img_name} is not found in the database") 
        
        self.project_id = project_id
        self.tick_time = time.time()
        self.show_label_names = False
        self.max_action_time_sec = 10
        self.img_dir = img_dir
        self.img_id = 0 
        self.duration_hours = 0
        self.processed_img_ids: set = set()
        self.annotation_mode: AnnotationMode = annotation_mode
        self.annotation_stage: AnnotationStage = annotation_stage
        self.orig_image: np.ndarray = None
        self.canvas: np.ndarray = None
        self.is_trash = False
        self.figures: List = list()
        self.hide_main_figures = False
        self.hide_secondary_figures = False
        self.selected_figure_id = None
        self.mode = Mode.IDLE
        self.active_label: Label = Label.first()
        self.cursor_x, self.cursor_y = 0, 0
        self.scale_factor = 1
        self.image_changed = False
        self.ready_for_export = False
        self.load_state()
        self.load_image()

    @property
    def status_data(self):
        number_of_processed = len(self.processed_img_ids)
        return StatusData(
            selected_class=f"{self.active_label.name} [{self.active_label.hotkey}]",
            class_color=self.active_label.color,
            is_trash=self.is_trash,
            annotation_mode=self.annotation_mode.name,
            annotation_stage=self.annotation_stage.name,
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            img_id=self.img_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_images=len(self.img_names),
            figures_hidden=self.hide_main_figures,
            secondary_figures_hidden=self.hide_secondary_figures
        )

    def update_time_counter(self):
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600

    @abstractmethod
    def get_selected_figure_id(self, x: int, y: int) -> Optional[int]:
        raise NotImplementedError
    
    @abstractmethod
    def draw_figure(self, canvas: np.ndarray, figure, highlight: bool = False) -> np.ndarray:
        raise NotImplementedError
    
    def draw_figures(self, canvas: np.ndarray, limage: LabeledImage) -> np.ndarray:
        figures = self.get_image_figures(image=limage)
        for figure in figures:
            canvas = self.draw_figure(canvas=canvas, figure=figure)
        return canvas
    
    def update_canvas(self): 
        self.canvas = np.copy(self.orig_image)
        if not self.hide_main_figures:
            for figure_id, figure in enumerate(self.figures):
                self.canvas = self.draw_figure(self.canvas, figure, highlight=figure_id==self.selected_figure_id)

    def update_orig_image(self):
        img_name = self.img_names[self.img_id]
        self.orig_image = cv2.imread(os.path.join(self.img_dir, img_name))
        if self.secondary_visualizer is not None and not self.hide_secondary_figures: 
            img_name = self.img_names[self.img_id]
            limage = LabeledImage.get(name=img_name)
            self.orig_image = self.secondary_visualizer.draw_figures(canvas=self.orig_image, limage=limage)

    def load_image(self):
        self.hide_main_figures = False
        self.hide_secondary_figures = False
        self.update_orig_image()
        img_name = self.img_names[self.img_id]
        image = LabeledImage.get(name=img_name)
        self.figures = list(self.get_image_figures(image))
        self.is_trash = image.trash
        self.update_canvas()

    @abstractmethod
    def save_image(self): 
        raise NotImplementedError

    def save_state(self):
        Value.update_value("img_id", self.img_id)
        Value.update_value("duration_hours", self.duration_hours)
        Value.update_value("processed_img_ids", list(self.processed_img_ids))
        Value.update_value("annotation_stage", self.annotation_stage.name)

    def load_state(self):
        annotation_stage_name = Value.get_value("annotation_stage")
        if self.annotation_stage.name != annotation_stage_name: # If annotation stage is changed
            self.img_id = 0
            self.duration_hours = 0
            self.processed_img_ids = set()
            self.image_changed = True
        else:
            img_id = Value.get_value("img_id")
            self.img_id = int(img_id) if img_id is not None else self.img_id

            duration_hours = Value.get_value("duration_hours")
            self.duration_hours = float(duration_hours) if duration_hours is not None else self.duration_hours

            processed_img_ids = Value.get_value("processed_img_ids")
            self.processed_img_ids = set(json.loads(processed_img_ids)) if processed_img_ids is not None else self.processed_img_ids

            self.image_changed = False

    def forward(self):
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        if self.img_id < len(self.img_names) - 1:
            self.img_id += 1
        self.load_image()
        self.save_state()
        
    def backward(self):
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        if self.img_id > 0:
            self.img_id -= 1
        self.load_image()
        self.save_state()

    def go_to_first_image(self):
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        self.img_id = 0
        self.load_image()
        self.save_state()

    def toggle_image_trash_tag(self):
        image = LabeledImage.get(name=self.img_names[self.img_id])
        image.trash = not image.trash
        image.save()
        self.is_trash = image.trash
        self.update_canvas()
        self.image_changed = True

    def switch_object_names_visibility(self):
        self.show_label_names = not self.show_label_names
        self.update_canvas()

    def switch_hiding_main_figures(self):
        self.hide_main_figures = not self.hide_main_figures
        self.update_canvas()

    def switch_hiding_secondary_figures(self):
        self.hide_secondary_figures = not self.hide_secondary_figures
        self.update_orig_image()
        self.update_canvas()

    def copy_figures_from_previous_image(self):
        if self.img_id > 0:
            prev_image = LabeledImage.get(name=self.img_names[self.img_id - 1])
            self.figures = [figure.copy() for figure in self.get_image_figures(prev_image)]
        self.update_canvas()
        self.image_changed = True

    def change_label(self, label_hotkey: int):
        label = Label.get_by_hotkey(label_hotkey)
        if label is not None:
            self.active_label = label
            
            if self.selected_figure_id is not None:
                self.figures[self.selected_figure_id].label = self.active_label.name
                self.update_canvas()
        self.image_changed = True

    def remove_selected_figure(self):
        if self.selected_figure_id is not None:
            figure = self.figures[self.selected_figure_id]
            figure.delete()
            self.figures.pop(self.selected_figure_id)
            self.selected_figure_id = self.get_selected_figure_id(self.cursor_x, self.cursor_y)
            self.update_canvas()
        self.image_changed = True

    @staticmethod
    @abstractmethod
    def get_image_figures(image: LabeledImage) -> List:
        raise NotImplementedError

    @abstractmethod
    def handle_left_mouse_press(self, x: int, y: int):
        pass

    @abstractmethod
    def handle_mouse_move(self, x: int, y: int):
        pass

    @abstractmethod
    def handle_mouse_hover(self, x: int, y: int):
        pass

    @abstractmethod
    def handle_left_mouse_release(self, x: int, y: int):
        pass
    


class BboxLabelingApp(LabelingApp):

    def __init__(self, img_dir: str,  annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int, secondary_visualizer: Visualizable = None):
        self.start_point: Optional[Tuple[int, int]] = None
        super().__init__(img_dir=img_dir, annotation_stage=annotation_stage, annotation_mode=annotation_mode, project_id=project_id, secondary_visualizer=secondary_visualizer)
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
        if self.mode == Mode.MOVING:
            self.move_selected_bbox(x, y)
        self.update_canvas() 

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode == Mode.MOVING:
            self.release_bbox()
            self.mode = Mode.IDLE
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.update_canvas()

    def handle_left_mouse_press(self, x: int, y: int):

        if self.mode == Mode.IDLE:
            rect_id, point_id = self.get_rect_point_id(x, y)
            if point_id is not None:
                self.selected_figure_id = rect_id
                self.figures[rect_id].active_point_id = point_id 
                self.mode = Mode.MOVING
            else:
                self.start_point = (x, y)
                self.mode = Mode.CREATE
        
        elif self.mode == Mode.CREATE:
            if abs(self.start_point[0] - x) > 5 and abs(self.start_point[1] - y) > 5:
                self.add_bbox(x, y)
            self.start_point = None
            self.mode = Mode.IDLE
            self.selected_figure_id = self.get_selected_figure_id(x, y)
            
        self.update_canvas()

    def handle_mouse_hover(self, x: int, y: int):
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.cursor_x, self.cursor_y = x, y
        self.update_canvas()


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



def get_labeling_app(img_dir: str, annotation_mode: AnnotationMode, annotation_stage: AnnotationStage, project_id: int) -> Optional[LabelingApp]:

    if annotation_stage is AnnotationStage.CORRECTION:
        review_labeling_app = ReviewLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            project_id=project_id
        )
    else:
        review_labeling_app = None


    if annotation_mode is AnnotationMode.OBJECT_DETECTION:
        labeling_app = BboxLabelingApp(
            img_dir=img_dir, 
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            secondary_visualizer=review_labeling_app,
            project_id=project_id
        )

    if annotation_stage is AnnotationStage.REVIEW:
        labeling_app.show_label_names = True
        labeling_app = ReviewLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            secondary_visualizer=labeling_app,
            project_id=project_id
        )
    
    return labeling_app