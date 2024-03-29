
from abc import ABC, abstractmethod
from ast import Tuple
from dataclasses import dataclass
import json
import math
import os
import time
from typing import Dict, List, Optional
import numpy as np
import cv2

from controller import ControllerByMode, ObjectFigureController
from enums import AnnotationMode, AnnotationStage, FigureType
from exceptions import MessageBoxException
from models import Figure, Label, LabeledImage, ReviewLabel, Value


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
    review_labels_hidden: bool


class LabelingApp(ABC):

    def __init__(self, img_dir: str, annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int):
    
        self.img_names = sorted(os.listdir(img_dir)) 
        
        if annotation_stage is AnnotationStage.CORRECTION:
            self.img_names = [img_name for img_name in self.img_names if len(LabeledImage.get(name=img_name).review_labels) > 0]

        for img_name in self.img_names: # Check that images from the directory are in the the database
            img_object = LabeledImage.get(name=img_name)
            if img_object is None:
                raise MessageBoxException(f"{img_name} is not found in the database") 
            
        keypoint_connections = Value.get_value("keypoint_connections")
        self.keypoint_connections: List = json.loads(keypoint_connections) if keypoint_connections is not None else None
        keypoint_info = Value.get_value("keypoint_info")
        self.keypoint_info: Dict = json.loads(keypoint_info) if keypoint_info is not None else None

        self.figures: List[Figure] = list()
        self.review_labels: List[ReviewLabel] = list()
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
        self.hide_figures = False
        self.hide_review_labels = False
        self.scale_factor = 1
        self.image_changed = False
        self.ready_for_export = False

        if annotation_stage is AnnotationStage.REVIEW:
            labels = Label.get_review_labels()
        else:
            labels = Label.get_figure_labels()

        self.labels_by_hotkey: Dict[str, Label] = {label.hotkey: label for label in labels}
        self.all_labels_by_name: Dict[str, Label] = {label.name: label for label in Label.all()}

        if self.annotation_stage is AnnotationStage.REVIEW:
            self.controller = ObjectFigureController(active_label=labels[0])
        else:
            self.controller = ControllerByMode[annotation_mode](active_label=labels[0])

        self.load_state()
        self.load_image()

    @property
    def status_data(self):
        number_of_processed = len(self.processed_img_ids)
        active_label = self.controller.active_label
        return StatusData(
            selected_class=f"{active_label.name} [{active_label.hotkey}]",
            class_color=active_label.color,
            is_trash=self.is_trash,
            annotation_mode=self.annotation_mode.name,
            annotation_stage=self.annotation_stage.name,
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            img_id=self.img_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_images=len(self.img_names),
            figures_hidden=self.hide_figures,
            review_labels_hidden=self.hide_review_labels
        )

    def update_time_counter(self):
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600
    
    def update_canvas(self): 
        self.canvas = np.copy(self.orig_image)
        if not self.hide_figures:
            if self.annotation_stage is AnnotationStage.REVIEW:
                # review_labels was edited and figures stored unchanged
                figures = self.figures 
                review_labels = self.controller.figures 
            else:
                # figures was edited and review_labels stored unchanged
                figures = self.controller.figures
                review_labels = self.review_labels 

            if not self.hide_review_labels:
                result_figures = figures + review_labels
            else:
                result_figures = figures

            for figure_id, figure in enumerate(result_figures):
                self.canvas = figure.draw_figure(
                    canvas=self.canvas, 
                    elements_scale_factor=self.scale_factor, 
                    keypoint_connections=self.keypoint_connections,
                    keypoint_info=self.keypoint_info,
                    show_label_names=self.show_label_names,
                    label=self.all_labels_by_name[figure.label]
                )
        
        self.canvas = self.controller.draw_additional_elements(self.canvas)

        if self.controller.preview_figure is not None:
            self.canvas = self.controller.preview_figure.draw_figure(
                canvas=self.canvas, 
                elements_scale_factor=self.scale_factor, 
                keypoint_connections=self.keypoint_connections,
                keypoint_info=self.keypoint_info,
                show_label_names=False,
                label=self.all_labels_by_name[self.controller.preview_figure.label]
            )

    def load_image(self):
        self.hide_figures = False
        self.hide_review_labels = False
        img_name = self.img_names[self.img_id]
        self.orig_image = cv2.imread(os.path.join(self.img_dir, img_name))
        self.labeled_image = LabeledImage.get(name=img_name)
        self.review_labels = list(self.labeled_image.review_labels)
        self.figures = list(self.labeled_image.bboxes + self.labeled_image.kgroups + self.labeled_image.masks)
        if self.annotation_stage is AnnotationStage.REVIEW:
            self.controller.figures = self.review_labels # Can edit only review labels
        else:
            self.controller.figures = self.figures # Can edit only figures

        h, w, c = self.orig_image.shape
        self.controller.img_height, self.controller.img_width = h, w
        self.labeled_image.height = h
        self.labeled_image.width = w
    
        self.is_trash = self.labeled_image.trash

    def save_image(self):
        if self.image_changed:

            if self.annotation_stage is AnnotationStage.REVIEW: 
                # Update only review labels when review
                review_labels = self.controller.figures
                self.labeled_image.review_labels = review_labels
            else:
                # Update only figures without review labels when annotation
                bboxes = list()
                kgroups = list()
                masks = list()
                for figure in self.controller.figures:
                    figure_type = self.all_labels_by_name[figure.label].type
                    if figure_type == FigureType.BBOX.name:
                        bboxes.append(figure)
                    elif figure_type == FigureType.KGROUP.name:
                        kgroups.append(figure)
                    elif figure_type == FigureType.MASK.name:
                        masks.append(figure)
                    else:
                        raise RuntimeError(f"Unknown figure type {figure_type}")
                    
                self.labeled_image.kgroups =  kgroups
                self.labeled_image.bboxes = bboxes
                self.labeled_image.masks = masks
                self.labeled_image.trash = self.is_trash

            self.labeled_image.save()

    def save_state(self):  # TODO: Save values as a batch
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
        if self.annotation_stage is AnnotationStage.REVIEW:
            return
        self.labeled_image.trash = not self.labeled_image.trash
        self.labeled_image.save()
        self.is_trash = self.labeled_image.trash
        self.image_changed = True

    def switch_object_names_visibility(self):
        self.show_label_names = not self.show_label_names

    def switch_hiding_figures(self):
        self.hide_figures = not self.hide_figures

    def switch_hiding_review_labels(self):
        self.hide_review_labels = not self.hide_review_labels

    def copy_figures_from_previous_image(self):
        if self.img_id > 0:
            prev_image = LabeledImage.get(name=self.img_names[self.img_id - 1])

            self.labeled_image.kgroups =  [kgroup.copy() for kgroup in prev_image.kgroups]
            self.labeled_image.bboxes = [bbox.copy() for bbox in prev_image.bboxes]
            self.labeled_image.masks = [mask.copy() for mask in prev_image.masks]

            self.labeled_image.save()
        self.load_image()
        self.image_changed = True


    def change_label(self, label_hotkey: int):
        label = self.labels_by_hotkey.get(label_hotkey)
        if label is not None:
            self.controller.change_label(label)
            self.image_changed = True

    def delete_command(self):
        self.controller.delete_command()
        self.image_changed = True

    def handle_left_mouse_press(self, x: int, y: int):
        self.controller.handle_left_mouse_press(x, y)
        self.image_changed = True

    def handle_mouse_move(self, x: int, y: int):
        self.controller.handle_mouse_move(x, y)
        self.image_changed = True

    def handle_mouse_hover(self, x: int, y: int):
        self.controller.handle_mouse_hover(x, y)

    def handle_left_mouse_release(self, x: int, y: int):
        self.controller.handle_left_mouse_release(x, y)

    def handle_space(self):
        self.controller.handle_space()

    def handle_esc(self):
        self.controller.handle_esc()

    def on_shift_press(self):
        self.controller.shift_mode = not self.controller.shift_mode
    