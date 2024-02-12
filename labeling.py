
from dataclasses import dataclass
import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from enum import Enum, auto

from tqdm import tqdm
from models import Label, LabeledImage, BBox, Point, Value
from utils import open_json, save_json


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class AnnotationMode(Enum):
    BBOXES = "BBOXES"
    SEGMENTATION = "SEGMENTATION"


@dataclass
class StatusData:
    selected_class: str
    class_color: str
    is_trash: bool
    annotation_mode: str
    speed_per_hour: float
    processed_percent: float
    img_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_images: int
    figures_hidden: bool


class LabelingApp:

    def __init__(self, img_dir: str, export_path: str, annotation_mode: AnnotationMode, review_mode: bool = False):    
        
        self.img_names = sorted(os.listdir(img_dir))
        for img_name in self.img_names: # Check that images from the directory are in the the database
            img_object = LabeledImage.get(name=img_name)
            assert img_object is not None, f"{img_name} is not found in the database"

        self.tick_time = time.time()
        self.max_action_time_sec = 10

        self.img_dir = img_dir
        self.export_path = export_path if export_path is not None else "result.json"

        self.img_id = 0 
        self.duration_hours = 0
        self.processed_img_ids: set = set()
        self.load_state()

        self.orig_image: np.ndarray = None
        self.canvas: np.ndarray = None
        self.is_trash = False
        self.figures: List = list()

        self.hide_figures = False

        self.selected_figure_id = None

        self.mode = Mode.IDLE

        self.active_label: Label = Label.first()

        self.annotation_mode: AnnotationMode = annotation_mode # TODO: Get annotation mode from the database
        self.review_mode: bool = review_mode # TODO: If review mode - user can not edit figures and only adds the points to the images. This points cannot be edited in non-review mode. User only can hide them.

        self.cursor_x, self.cursor_y = 0, 0

        self.scale_factor = 1

        self.load_image()

    @property
    def status_data(self):
        number_of_processed = len(self.processed_img_ids)
        return StatusData(
            selected_class=self.active_label.name,
            class_color=self.active_label.color,
            is_trash=self.is_trash,
            annotation_mode=self.annotation_mode.name,
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            img_id=self.img_id,
            processed_percent=round(number_of_processed / (len(self.img_names) + 1e-7) * 100, 2),
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_images=len(self.img_names),
            figures_hidden=self.hide_figures
        )

    def update_time_counter(self):
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600

    def get_selected_figure_id(self, x: int, y: int) -> Optional[int]:
        raise NotImplementedError
    
    def draw_figure(self, canvas: np.ndarray, figure, highlight: bool = False) -> np.ndarray:
        raise NotImplementedError

    def update_canvas(self): # TODO: Implement in the child classes. Create visualizer class and move to it the logic of visualization.
        self.canvas = np.copy(self.orig_image)

        if not self.hide_figures:
            for figure_id, figure in enumerate(self.figures):
                self.canvas = self.draw_figure(self.canvas, figure, highlight=figure_id==self.selected_figure_id)

        if self.annotation_mode == AnnotationMode.BBOXES:
            h, w, c = self.canvas.shape

            # Draw vertical and horizontal lines (black and white)
            self.canvas = cv2.line(self.canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
            self.canvas = cv2.line(self.canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
            self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
            self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)


    def load_image(self):
        img_name = self.img_names[self.img_id]
        self.orig_image = cv2.imread(os.path.join(self.img_dir, img_name))
        image = LabeledImage.get(name=img_name)
        self.figures = list(self.get_image_figures(image))
        self.is_trash = image.trash
        self.update_canvas()

    def save_image(self): 
        raise NotImplementedError

    def save_state(self):
        Value.update_value("img_id", self.img_id)
        Value.update_value("duration_hours", self.duration_hours)
        Value.update_value("processed_img_ids", list(self.processed_img_ids))

    def load_state(self):
        img_id = Value.get_value("img_id")
        self.img_id = int(img_id) if img_id is not None else self.img_id

        duration_hours = Value.get_value("duration_hours")
        self.duration_hours = float(duration_hours) if duration_hours is not None else self.duration_hours

        processed_img_ids = Value.get_value("processed_img_ids")
        self.processed_img_ids = set(json.loads(processed_img_ids)) if processed_img_ids is not None else self.processed_img_ids

    def forward(self):
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        if self.img_id < len(self.img_names) - 1:
            self.img_id += 1
        self.load_image()
        self.hide_figures = False
        self.save_state()
        
    def backward(self):
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        if self.img_id > 0:
            self.img_id -= 1
        self.load_image()
        self.hide_figures = False
        self.save_state()

    def complete_project(self):

        self.save_image()

        result = dict()
        for image_name in tqdm(self.img_names, desc=f"Exporting data to {self.export_path}"):
            image = LabeledImage.get(name=image_name)
            result[image.name] = {
                "trash": image.trash, 
                "bboxes": [{"x1": bbox.x1, "y1": bbox.y1, "x2": bbox.x2, "y2": bbox.y2, "label": bbox.label} for bbox in image.bboxes],
                # "masks": [{"rle": mask.rle,  "label": mask.label} for mask in image.masks]
            }

        save_json(result, self.export_path) 

        # TODO: Send json to eg-ml via api (via ssh for now) and mark project as sent for review via api 
        ...

    def toggle_image_trash_tag(self):
        image = LabeledImage.get(name=self.img_names[self.img_id])
        if image.trash:
            image.trash = False
        else:
            image.trash = True
        image.save()
        self.is_trash = image.trash
        self.update_canvas()

    def switch_hiding_figures(self):
        if self.hide_figures:
            self.hide_figures = False
        else:
            self.hide_figures = True
        self.update_canvas()

    def copy_figures_from_previous_image(self):
        if self.img_id > 0:
            prev_image = LabeledImage.get(name=self.img_names[self.img_id - 1])
            self.figures = [figure.copy() for figure in self.get_image_figures(prev_image)]
        self.update_canvas()

    def change_label(self, label_hotkey: int):
        label = Label.get_by_hotkey(label_hotkey)
        if label is not None:
            self.active_label = label
            
            if self.selected_figure_id is not None:
                self.figures[self.selected_figure_id].label = self.active_label.name
                self.figures[self.selected_figure_id].save()
                self.update_canvas()

    def remove_selected_figure(self):
        if self.selected_figure_id is not None:
            self.figures.pop(self.selected_figure_id)
            self.selected_figure_id = self.get_selected_figure_id(self.cursor_x, self.cursor_y)
            self.update_canvas()


    @staticmethod
    def get_image_figures(image: LabeledImage) -> List:
        raise NotImplementedError



    def handle_left_mouse_press(self, x: int, y: int):
        pass

    def handle_right_mouse_press(self, x: int, y: int):
        pass


    def handle_mouse_move(self, x: int, y: int):
        pass

    def handle_mouse_hover(self, x: int, y: int):
        pass

    def handle_left_mouse_release(self, x: int, y: int):
        pass
    
    def handle_right_mouse_release(self, x: int, y: int):
        pass



class BboxLabelingApp(LabelingApp):

    def __init__(self, img_dir: str, export_path: str, annotation_mode: AnnotationMode, review_mode: bool = False):
        self.start_point: Optional[Tuple[int, int]] = None
        super().__init__(img_dir, export_path, annotation_mode, review_mode)
        self.figures: List[BBox] = list()
        self.load_image()

    def draw_figure(self, canvas: np.ndarray, figure: BBox, highlight: bool = False) -> np.ndarray:
        """Drawing the bbox on the canvas"""

        line_width = max(1, int(4 / ((self.scale_factor + 1e-7) ** (1/3))))

        if highlight:
            line_width += 1

        label = Label.get_by_name(figure.label)

        for layer_id in range(line_width):
            canvas = cv2.rectangle(canvas, (int(figure.x1 - layer_id), int(figure.y1 - layer_id)), (int(figure.x2 + layer_id), int(figure.y2 + layer_id)), label.color_bgr, 1)

        for point in figure.points:
            if point.close_to(self.cursor_x, self.cursor_y):
                circle_radius = max(1, int(4 / ((self.scale_factor + 1e-7) ** (1/3))))
                cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (255, 255, 255), -1)
                cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (0, 0, 0), 2)

        return canvas
    
    def update_canvas(self):
        super().update_canvas()
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

    def release_bbox(self):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = None 
            self.selected_figure_id = None

    def move_selected_bbox(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].move_active_point(x, y)

    @staticmethod
    def get_image_figures(image: LabeledImage) -> List[BBox]:
        return image.bboxes

    def save_image(self): 
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
        elif self.mode == Mode.CREATE:
            if abs(self.start_point[0] - x) > 5 and abs(self.start_point[1] - y) > 5:
                self.add_bbox(x, y)
            self.start_point = None
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

    
    def handle_mouse_hover(self, x: int, y: int):
        self.selected_figure_id = self.get_selected_figure_id(x, y)
        self.cursor_x, self.cursor_y = x, y
        self.update_canvas()



def get_labeling_app(img_dir: str, export_path: str, review_mode: bool, annotation_mode: AnnotationMode) -> Optional[LabelingApp]:
    if annotation_mode == AnnotationMode.BBOXES:
        labeling_app = BboxLabelingApp(
            img_dir=img_dir, 
            export_path=export_path, 
            review_mode=review_mode, 
            annotation_mode=annotation_mode
        )
    return labeling_app