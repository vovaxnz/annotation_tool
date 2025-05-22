from copy import deepcopy
import os
from collections import defaultdict
from dataclasses import dataclass
import random
from typing import Dict, List, Tuple

from annotation_widgets.image.models import Label
import cv2
import numpy as np

from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from enums import AnnotationMode, AnnotationStage, FigureType
from exceptions import MessageBoxException
from models import ProjectData
from .drawing import create_class_selection_wheel, get_selected_sector_id
from .figure_controller import Mode, ObjectFigureController
from .figure_controller_factory import ControllerByMode
from .models import Figure, LabeledImage, ReviewLabel
from .path_manager import LabelingPathManager
from config import ColorBGR, settings


@dataclass
class StatusData:
    selected_class: str
    class_color: str
    is_trash: bool
    annotation_mode: str
    annotation_stage: str
    speed_per_hour: float
    item_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_items: int
    figures_hidden: bool
    review_labels_hidden: bool


class ImageLabelingLogic(AbstractImageAnnotationLogic):

    def __init__(self, data_path: str, project_data: ProjectData):
    
        self.img_names = sorted(os.listdir(data_path)) 
        
        if project_data.stage is AnnotationStage.CORRECTION:
            self.img_names = [item.name for item in LabeledImage.all() if len(item.review_labels) > 0]
        elif project_data.stage is AnnotationStage.REVIEW:
            self.img_names = [item.name for item in LabeledImage.all() if item.requires_annotation]

        if len(self.img_names) == 0:
            raise RuntimeError(f"Project id: {project_data.id}; Stage: {project_data.stage.name}; Number of images: {len(LabeledImage.all())}; Number to annotate: 0")

        for img_name in self.img_names: # Check that images from the directory are in the the database
            img_object = LabeledImage.get(name=img_name)
            if img_object is None:
                raise MessageBoxException(f"{img_name} is not found in the database") 
            
        self.figures: List[Figure] = list()
        self.review_labels: List[ReviewLabel] = list()
        self.show_label_names = False
        self.show_object_size = False
        self.img_dir = data_path
        self.orig_image: np.ndarray = None
        self.is_trash = False
        self.hide_figures = False
        self.hide_review_labels = False
        self.scale_factor = 1
        self.selecting_class = False
        self.force_redrawing = False

        self.init_canvas = None
        self.blurred_image: np.ndarray = None
        self.prev_blur_figures = list()

        if project_data.stage is AnnotationStage.REVIEW:
            labels = Label.get_review_labels()
        else:
            labels = Label.get_figure_labels()

        self.labels_by_hotkey: Dict[str, Label] = {label.hotkey: label for label in labels}
        self.available_labels = list(labels)
        
        self.labels: Dict[str, Dict[str, Label]] = defaultdict(dict)
        for label in Label.all():
            self.labels[label.type][label.name] = label


        labels_list = list(labels)
        if len(labels_list) > 1:
            active_label = labels_list[1]
        else:
            active_label = labels_list[0]
        if project_data.stage is AnnotationStage.REVIEW:
            self.controller = ObjectFigureController(active_label=active_label)
        else:
            self.controller = ControllerByMode[project_data.mode](active_label=active_label)

        super().__init__(data_path=data_path, project_data=project_data)


    @property
    def items_number(self) -> int:
        return len(self.img_names)

    @property
    def status_data(self):
        number_of_processed = len(self.processed_item_ids)
        active_label = self.controller.active_label
        return StatusData(
            selected_class=f"{active_label.name}: {active_label.type} [{active_label.hotkey}]",
            class_color=active_label.color,
            is_trash=self.is_trash,
            annotation_mode=self.project_data.mode.name,
            annotation_stage=self.project_data.stage.name,
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            item_id=self.item_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_items=len(self.img_names),
            figures_hidden=self.hide_figures,
            review_labels_hidden=self.hide_review_labels,
        )

    @property
    def editing_blocked(self):
        if self.hide_figures:
            if self.project_data.mode != AnnotationMode.SEGMENTATION:
                return True
        return False

    def get_path_manager(self, project_id) -> LabelingPathManager:
        return LabelingPathManager(project_id)
    
    def separate_blur_and_figures(self, figures: List[Figure]) -> Tuple[List[Figure], List[Figure]]:
        blur_figures = list()
        figures_to_draw = list()
        for figure in figures:
            if figure.label == "blur":
                blur_figures.append(figure)
            else:
                figures_to_draw.append(figure)   
        return blur_figures, figures_to_draw         

    def blur_image(self, blur_figures: List[Figure], canvas: np.ndarray) -> np.ndarray:
        if self.blurred_image is None:
            small = cv2.resize(self.orig_image, (0,0), fx=0.01, fy=0.01, interpolation=cv2.INTER_AREA)
            self.blurred_image = cv2.resize(small, (self.orig_image.shape[1], self.orig_image.shape[0]), interpolation=cv2.INTER_LINEAR)
            
        mask = np.zeros_like(canvas, dtype=np.uint8)
        for figure in blur_figures:
            mask = figure.draw_figure(
                canvas=mask, 
                elements_scale_factor=self.scale_factor, 
                show_label_names=False,
                show_object_size=False,
                label=self.labels[figure.figure_type][figure.label],
                color=ColorBGR.white,
                with_border=False,
                color_fill_opacity=1,
                show_active_point=False,
            )

        m = mask[:, :, 0] > 0
        canvas[m] = self.blurred_image[m]

        return canvas

    @staticmethod
    def dicts_to_str(data: List[Dict]) -> str:
        result = [
            str([(key, d[key]) for key in sorted(d.keys())])
            for d in data
        ]
        return str(sorted(result))

    def ensure_figures_same(self, figures1: List[Figure], figures2: List[Figure]) -> bool:
        if len(figures1) != len(figures2): return False
        str1 = self.dicts_to_str([figure.serialize() for figure in figures1])
        str2 = self.dicts_to_str([figure.serialize() for figure in figures2])
        return str1 == str2
        


    def update_canvas(self): 
        assert self.orig_image is not None

        if self.project_data.stage is AnnotationStage.REVIEW:
            # review_labels was edited and figures stored unchanged
            figures = [figure for figure in self.figures]
            review_labels = self.controller.figures 
        else:
            # figures was edited and review_labels stored unchanged
            figures = [figure for figure in self.controller.figures]
            review_labels = self.review_labels 

        if not self.hide_review_labels:
            result_figures = figures + review_labels
        else:
            result_figures = [figure for figure in figures]

        if self.controller.preview_figure is not None:
            result_figures.append(self.controller.preview_figure)

        blur_figures, figures_to_draw = self.separate_blur_and_figures(result_figures)

        if not self.hide_figures:
            figures_are_same = self.ensure_figures_same(self.prev_blur_figures, blur_figures)
            if self.init_canvas is None or not figures_are_same or self.force_redrawing:
                self.init_canvas = self.blur_image(blur_figures, np.copy(self.orig_image))
                self.prev_blur_figures = deepcopy(blur_figures)
        else:
            self.init_canvas = self.orig_image
        self.canvas = np.copy(self.init_canvas)

        if self.make_image_worse:
            self.canvas = self.deteriorate_image(self.canvas)

        if not self.hide_figures:
            # Draw selected blur figure
            for figure in blur_figures:
                if figure.selected:
                    self.canvas = figure.draw_figure(
                        canvas=self.canvas, 
                        elements_scale_factor=self.scale_factor, 
                        show_label_names=False,
                        show_object_size=False,
                        label=self.labels[figure.figure_type][figure.label],
                        color_fill_opacity=0,
                        with_border=True
                    )

            for figure_id, figure in enumerate(sorted(figures_to_draw, key=lambda x: x.surface, reverse=True)):
                self.canvas = figure.draw_figure(
                    canvas=self.canvas, 
                    elements_scale_factor=self.scale_factor, 
                    show_label_names=self.show_label_names,
                    show_object_size=self.show_object_size,
                    label=self.labels[figure.figure_type][figure.label],
                    color_fill_opacity=settings.color_fill_opacity
                )
        
        self.canvas = cv2.addWeighted(self.canvas, settings.objects_opacity, self.init_canvas, max(1 - settings.objects_opacity, 0), 0)
        
        self.canvas = self.controller.draw_additional_elements(self.canvas, scale_factor=self.scale_factor)

        if self.selecting_class and self.controller.label_wheel_xc is not None and self.controller.label_wheel_yc is not None:
            self.canvas = create_class_selection_wheel(
                img=self.canvas,
                classes=[label.name if label.type != FigureType.KGROUP.name else f"{label.name}"+":"+f"{label.type}" for label in self.available_labels],
                colors=[label.color_bgr for label in self.available_labels],
                center_x=self.controller.label_wheel_xc, 
                center_y=self.controller.label_wheel_yc, 
                edge_x=self.controller.cursor_x, 
                edge_y=self.controller.cursor_y
            )
        
        self.force_redrawing = False

    def load_item(self, next: bool = True):
        self.hide_figures = False
        self.hide_review_labels = False
        assert 0 <= self.item_id < len(self.img_names), f"The Image ID {self.item_id} is out of range of the images list: {len(self.img_names)}"
        img_name = self.img_names[self.item_id]
        self.orig_image = cv2.imread(os.path.join(self.img_dir, img_name))
        self.blurred_image = None
        self.init_canvas = None
        self.prev_blur_figures = list()
        self.labeled_image = LabeledImage.get(name=img_name)
        self.review_labels = list(self.labeled_image.review_labels)
        self.figures = list(self.labeled_image.bboxes + self.labeled_image.kgroups + self.labeled_image.masks)
        if self.project_data.stage is AnnotationStage.REVIEW:
            self.controller.figures = self.review_labels # Can edit only review labels
        else:
            self.controller.figures = self.figures # Can edit only figures

        h, w, c = self.orig_image.shape
        self.controller.img_height, self.controller.img_width = h, w
        self.labeled_image.height = h
        self.labeled_image.width = w
    
        self.is_trash = self.labeled_image.trash
        self.controller.take_snapshot()

    def save_item(self):
        if self.item_changed:

            if self.project_data.stage is AnnotationStage.REVIEW: 
                # Update only review labels when review
                review_labels = self.controller.figures
                self.labeled_image.review_labels = review_labels
            else:
                # Update only figures without review labels when annotation
                bboxes = list()
                kgroups = list()
                masks = list()
                for figure in self.controller.figures:
                    figure_type = figure.figure_type
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


    def switch_item(self, item_id: int):
        self.processed_item_ids.add(self.item_id)
        if item_id > len(self.img_names) - 1 or item_id < 0:
            return
        self.save_item()
        self.controller.clear_history()
        self.item_id = item_id
        self.load_item()
        self.save_state()


    def toggle_image_trash_tag(self):
        if self.project_data.stage is AnnotationStage.REVIEW:
            return
        self.labeled_image.trash = not self.labeled_image.trash
        self.labeled_image.save()
        self.is_trash = self.labeled_image.trash
        self.item_changed = True

    def switch_object_names_visibility(self):
        self.show_label_names = not self.show_label_names

    def switch_object_size_visibility(self):
        self.show_object_size = not self.show_object_size

    def switch_hiding_figures(self):
        self.hide_figures = not self.hide_figures
        if not self.hide_figures:
            self.force_redrawing = True

    def switch_hiding_review_labels(self):
        self.hide_review_labels = not self.hide_review_labels

    def change_label(self, label_hotkey: int):
        if self.editing_blocked: return              
        label = self.labels_by_hotkey.get(label_hotkey)
        if label is not None:
            self.controller.change_label(label)
            self.item_changed = True

    def start_selecting_class(self):
        if not self.selecting_class:
            self.controller.update_label_wheel_coordinates()
            self.selecting_class = True

    def end_selecting_class(self):
        if self.selecting_class:
            label_id = get_selected_sector_id(
                n_classes=len(self.available_labels), 
                center_x=self.controller.label_wheel_xc, 
                center_y=self.controller.label_wheel_yc, 
                edge_x=self.controller.cursor_x, 
                edge_y=self.controller.cursor_y
            )
            self.controller.change_label(self.available_labels[label_id])
            self.item_changed = True
            self.selecting_class = False
        
    def delete_command(self):
        if self.editing_blocked: return 
        self.controller.delete_command()
        self.item_changed = True

    def handle_left_mouse_press(self, x: int, y: int):
        if self.editing_blocked: return
        self.controller.handle_left_mouse_press(x, y)
        self.item_changed = True

    def handle_mouse_move(self, x: int, y: int):
        self.controller.handle_mouse_move(x, y)
        self.item_changed = True

    def handle_mouse_hover(self, x: int, y: int):
        if self.selecting_class:
            self.controller.cursor_x, self.controller.cursor_y = x, y
        else:
            self.controller.handle_mouse_hover(x, y)

    def handle_left_mouse_release(self, x: int, y: int):
        if self.editing_blocked: return
        self.controller.handle_left_mouse_release(x, y)

    def handle_space(self):
        self.controller.handle_space()

    def handle_esc(self):
        self.controller.handle_esc()

    def on_shift_press(self):
        self.controller.shift_mode = not self.controller.shift_mode
    
    def redo(self):
        if self.editing_blocked: return
        self.controller.redo()

    def undo(self):
        if self.editing_blocked: return
        self.controller.undo()
    
    def copy(self):
        if self.editing_blocked: return
        self.controller.copy()

    def paste(self):
        if self.editing_blocked: return
        self.controller.paste()
        self.item_changed = True

    def handle_key(self, key: str):
        if key.isdigit(): 
            self.change_label(key)
        elif key.lower() == "d":
            self.delete_command()
        elif key.lower() == "t":
            self.toggle_image_trash_tag()
        elif key.lower() == "e":
            self.switch_hiding_figures()
        elif key.lower() == "r":
            self.switch_hiding_review_labels() 
        elif key.lower() == "n":
            self.switch_object_names_visibility() 
        elif key.lower() == "h":
            self.switch_object_size_visibility() 
        elif key.lower() == "s":
            self.make_image_worse = not self.make_image_worse
