
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import math
import os
import time
from typing import Dict, List, Optional
import numpy as np
import cv2
from enum import Enum, auto

from config import AnnotationMode, AnnotationStage
from exceptions import MessageBoxException
from models import Label, LabeledImage, Value


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    IDLE = auto()
    CREATE = auto()


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
        self.preview_figure = None # TODO: self.preview_figure: Figure = None
        self.show_label_names = False
        self.max_action_time_sec = 10
        self.min_movement_to_create = 5
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
        self.labels_by_hotkey: Dict[str, Label] = {label.hotkey: label for label in Label.all()}
        self.labels_by_name: Dict[str, Label] = {label.name: label for label in Label.all()}
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

    def save_state(self): # TODO: Save values as a batch
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
        label = self.labels_by_hotkey.get(label_hotkey)
        if label is not None:
            self.active_label = label
            
            if self.selected_figure_id is not None:
                fig = self.figures[self.selected_figure_id]
                if fig.label.type == label.type:
                    fig.label = self.active_label.name
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
    

