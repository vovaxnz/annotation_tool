
from abc import ABC, abstractmethod
from ast import Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, IntEnum
import json
import math
import os
import time
from typing import Dict, List, Optional
import numpy as np
import cv2

from controller import ControllerByMode, ObjectFigureController
from drawing import create_class_selection_wheel, get_selected_sector_id
from enums import AnnotationMode, AnnotationStage, FigureType
from exceptions import MessageBoxException
from models import ClassificationImage, Value

# TODO:
# Mode: Filtering
# Delay: 200ms
# Selected: TRUE/FALSE

# Img id: ...
# Speed
# Position
# progress
# duration

FILTERING_BARCODE_PIXEL_SIZE = 
MAX_IMAGE_NAME_LENGTH = 


def decode_binary_to_string(binary_array):
    # Convert binary array to strings
    binary_strings = [''.join(map(str, binary)) for binary in binary_array]
    
    # Convert binary strings to decimal values
    decimal_vals = np.array([int(binary, 2) for binary in binary_strings])

    # Convert decimal values to characters
    decoded_string = ''.join(chr(val) for val in decimal_vals)
    
    return decoded_string

def decode_img_name_from_image(img: np.ndarray, mult=1):

    code_height = int(8 * FILTERING_BARCODE_PIXEL_SIZE * mult)
    code_width = int(MAX_IMAGE_NAME_LENGTH * FILTERING_BARCODE_PIXEL_SIZE * mult)


    img_h, img_w = img.shape[0], img.shape[1]
    code = img[img_h - code_height:img_h, 0:code_width]
    code =  cv2.cvtColor(code, cv2.COLOR_BGR2GRAY) 

    code = cv2.resize(code, (MAX_IMAGE_NAME_LENGTH, 8))
    binary_array = np.zeros_like(code, dtype=int)
    binary_array[code > 150] = 1
    binary_array = binary_array.T
    decoded_string = decode_binary_to_string(binary_array)

    result = decoded_string.lstrip()
    return result

@dataclass
class FilteringStatusData:
    delay: str
    selected: bool
    speed_per_hour: float
    img_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_images: int

class FilteringDelay(Enum):
    SLOW = 0.25
    MIDDLE = 0.1
    FAST = 0.01



class FilteringApp(ABC):

    def __init__(self, data_path: str, annotation_stage: AnnotationStage, annotation_mode: AnnotationMode, project_id: int, project_uid: str):
    
        assert data_path.endswith("mp4")

        self.project_id = project_id
        self.project_uid = project_uid
        self.tick_time = time.time()
        self.max_action_time_sec = 10
        self.img_id = 0 
        self.duration_hours = 0
        self.processed_img_ids: set = set()
        self.annotation_mode: AnnotationMode = annotation_mode
        self.annotation_stage: AnnotationStage = annotation_stage
        self.canvas: np.ndarray = None
        self.image_changed = False
        self.delay: FilteringDelay = FilteringDelay.MIDDLE
        self.cap = cv2.VideoCapture(data_path)
        self.labeled_image: ClassificationImage = None

        # Check if the video file was successfully opened
        if not self.cap.isOpened():
            raise MessageBoxException(f"Error opening video file {data_path}")

        self.img_number = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.load_state()
        self.load_image()

    @property
    def status_data(self) -> FilteringStatusData:
        number_of_processed = len(self.processed_img_ids)
        return FilteringStatusData(
            delay=self.delay.name,
            selected = self.labeled_image.selected,
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            img_id=self.img_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_images=self.img_number,
        )

    def update_time_counter(self):
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600
    
    def load_image(self, img_id: int = None):
        if img_id is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, img_id)
        
        ret, orig_img = self.cap.read()
        if ret:
            self.canvas = orig_img

        self.current_img_name = decode_img_name_from_image(self.canvas)

        self.labeled_image = ClassificationImage.get(name=self.current_img_name)
        if self.labeled_image is None:
            self.labeled_image = ClassificationImage(name=self.current_img_name)

    def save_image(self):
        if self.image_changed:
            self.labeled_image.save()

    def save_state(self):  # TODO: Save values as a batch
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

        self.image_changed = False

    def change_image(self, img_id: int):
        if img_id > self.img_number - 1 or img_id < 0:
            return
        time.sleep(self.delay.value)
        self.save_image()
        self.processed_img_ids.add(self.img_id)
        self.img_id = img_id
        self.load_image()
        self.save_state()

    def forward(self):
        self.change_image(img_id=self.img_id+1)
        
    def backward(self):
        self.change_image(img_id=self.img_id-1)

    def go_to_image_by_id(self, img_id: int):
        self.change_image(img_id=img_id)

    def select_image(self):
        self.labeled_image.selected = True

    def delete_command(self):
        self.handle_key(key="d")

    def handle_key(self, key: str):
        if key.lower() == "d":
            self.select_image()
        elif key.lower() == "1":
            self.delay = FilteringDelay.FAST
        elif key.lower() == "2":
            self.delay = FilteringDelay.MIDDLE
        elif key.lower() == "3":
            self.delay = FilteringDelay.SLOW


    # TODO: Move methods below to the abstract class
    def update_canvas(self): 
        pass
        
    def toggle_image_trash_tag(self):
        pass

    def switch_object_names_visibility(self):
        pass

    def switch_hiding_figures(self):
        pass

    def switch_hiding_review_labels(self):
        pass

    def change_label(self, label_hotkey: int):
        pass

    def start_selecting_class(self):
        pass

    def end_selecting_class(self):
        pass
        
    def handle_left_mouse_press(self, x: int, y: int):
        pass

    def handle_mouse_move(self, x: int, y: int):
        pass

    def handle_mouse_hover(self, x: int, y: int):
        pass

    def handle_left_mouse_release(self, x: int, y: int):
        pass

    def handle_space(self):
        pass

    def handle_esc(self):
        pass

    def on_shift_press(self):
        pass
    
    def redo(self):
        pass

    def undo(self):
        pass
    
    def copy(self):
        pass

    def paste(self):
        pass
