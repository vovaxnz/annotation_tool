
import math
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from enum import Enum, auto

from tqdm import tqdm
from models import Label, LabeledImage, BBox, Point
from utils import open_json, save_json


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


class AnnotationMode(Enum):
    BBOXES = "BBOXES"
    SEGMENTATION = "SEGMENTATION"

class LabelingApp:

    def __init__(self, img_dir: str, export_path: str, annotation_mode: AnnotationMode, review_mode: bool = False):    
        
        self.img_names = sorted(os.listdir(img_dir))
        for img_name in self.img_names: # Check that images from the directory are in the the database
            img_object = LabeledImage.get(name=img_name)
            assert img_object is not None, f"{img_name} is not found in the database"

        self.img_dir = img_dir
        self.export_path = export_path if export_path is not None else "result.json"

        self.img_id = 0 # TODO Get current image id from the database
        self.orig_image: np.ndarray = None
        self.canvas: np.ndarray = None
        self.is_trash = False
        self.figures: List = list()

        self.hide_figures = False

        self.selected_figure_id = None

        self.mode = Mode.IDLE

        self.active_label: str = "person" # TODO Labels.first().name where first is selected from sorted by hotkey

        self.annotation_mode: AnnotationMode = annotation_mode # TODO: Get annotation mode from the database
        self.review_mode: bool = review_mode # TODO: If review mode - user can not edit figures and only adds the points to the images. This points cannot be edited in non-review mode. User only can hide them.

        self.cursor_x, self.cursor_y = 0, 0

        self.scale_factor = 1

        self.load_image()


    def get_selected_figure_id(self, x: int, y: int) -> Optional[int]:
        raise NotImplementedError
    
    def draw_figure(self, canvas: np.ndarray, figure, highlight: bool = False) -> np.ndarray:
        raise NotImplementedError

    def update_canvas(self):
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


        # TODO: Write trash, active class, annotation mode and other info on the status panel on the bottom of the window
        # Draw img id on image
        cv2.putText(self.canvas, str(self.img_id), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 1, cv2.LINE_AA)
        if self.is_trash: 
            self.canvas = cv2.putText(self.canvas, "TRASH", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 255), 8, cv2.LINE_AA)


    def load_image(self):
        img_name = self.img_names[self.img_id]
        self.orig_image = cv2.imread(os.path.join(self.img_dir, img_name))
        image = LabeledImage.get(name=img_name)
        self.figures = list(self.get_image_figures(image))
        self.is_trash = image.trash
        self.update_canvas()

    def save_image(self): 
        raise NotImplementedError

    def forward(self):
        self.save_image()
        if self.img_id < len(self.img_names) - 1:
            self.img_id += 1
        self.load_image()
        ... # TODO Save current image id to the database

    def backward(self):
        self.save_image()
        if self.img_id > 0:
            self.img_id -= 1
        self.load_image()
        ... # TODO Save current image id to the database

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

    def change_label(self, label_id: int):
        labels = Label.all()
        if label_id < len(labels) - 1:
            label = labels[label_id]
            self.active_label = label.name
        
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].label = self.active_label
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

        # TODO: Use color of corresponding label

        line_width = max(1, int(3 / ((self.scale_factor + 1e-7) ** (1/3))))

        if highlight:
            line_width += 1

        canvas = cv2.rectangle(canvas, (int(figure.x1), int(figure.y1)), (int(figure.x2), int(figure.y2)), (255, 255, 255), line_width)

        for point in figure.points:
            if point.close_to(self.cursor_x, self.cursor_y):
                circle_radius = max(1, int(7 / ((self.scale_factor + 1e-7) ** (1/3))))
                cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (0, 255, 0), -1)

        return canvas
    
    def update_canvas(self):
        super().update_canvas()
        if self.start_point is not None:
            x1, x2 = sorted([self.cursor_x, self.start_point[0]])
            y1, y2 = sorted([self.cursor_y, self.start_point[1]])
            cv2.rectangle(self.canvas, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 1)


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
            bbox = BBox(x1, y1, x2, y2, self.active_label)
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