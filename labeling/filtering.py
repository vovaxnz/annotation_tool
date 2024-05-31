
from dataclasses import dataclass
from enum import Enum, IntEnum
import json
import math
import os
import time
from typing import Dict, List, Optional
import numpy as np
import cv2

from labeling.abstract_labeling_app import AbstractLabelingApp, ProjectData

from exceptions import MessageBoxException
from models import ClassificationImage



FILTERING_BARCODE_PIXEL_SIZE = 2
MAX_IMAGE_NAME_LENGTH = 100


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
    LONG = 0.25
    MIDDLE = 0.1
    SHORT = 0.01


class FilteringApp(AbstractLabelingApp):

    def __init__(self, data_path: str, project_data: ProjectData):
    
        assert data_path.endswith("mp4")

        self.delay: FilteringDelay = FilteringDelay.SHORT
        self.cap = cv2.VideoCapture(data_path)
        self.labeled_image: ClassificationImage = None

        # Check if the video file was successfully opened
        if not self.cap.isOpened():
            raise MessageBoxException(f"Error opening video file {data_path}")

        self.number_of_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        super().__init__(data_path=data_path, project_data=project_data)

    @property
    def img_number(self) -> int:
        return self.number_of_frames

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
    
    def load_image(self, next: bool = True):
        if not next:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.img_id)
        
        ret, orig_image = self.cap.read()
    
        if ret:
            self.orig_image = orig_image
            self.canvas = orig_image

        try:
            current_img_name = decode_img_name_from_image(self.orig_image)
            self.labeled_image = ClassificationImage.get(name=current_img_name)
        except:
            self.labeled_image = ClassificationImage.get(img_id=self.img_id)

        if self.labeled_image is None:
            self.labeled_image = ClassificationImage(name=current_img_name, img_id=self.img_id)
        
        self.update_canvas()

    def save_image(self):
        if self.image_changed:
            self.labeled_image.save()

    def change_image(self, img_id: int):
        if img_id > self.img_number - 1 or img_id < 0:
            return
        time.sleep(self.delay.value)
        self.save_image()
        self.processed_img_ids.add(self.img_id)

        forward = img_id == self.img_id + 1
        self.img_id = img_id
        self.load_image(next=forward)
        self.save_state()

    def select_image(self):
        self.labeled_image.selected = not self.labeled_image.selected
        self.image_changed = True

    def handle_key(self, key: str):
        if key.lower() == "d" or key.lower() == "k":
            self.select_image()
        elif key.lower() == "z":
            self.go_to_previous_selected()
        elif key.lower() == "x":
            self.go_to_next_selected()
        elif key.lower() == "s":
            self.make_image_worse = not self.make_image_worse
        elif key.lower() == "1":
            self.delay = FilteringDelay.SHORT
        elif key.lower() == "2":
            self.delay = FilteringDelay.MIDDLE
        elif key.lower() == "3":
            self.delay = FilteringDelay.LONG

    def go_to_next_selected(self):
        cimages = ClassificationImage.all_selected()
        for cimage in cimages:
            if cimage.img_id > self.img_id:
                self.change_image(img_id=cimage.img_id)
                break

    def go_to_previous_selected(self):
        cimages = ClassificationImage.all_selected()
        for cimage in reversed(list(cimages)):
            if cimage.img_id < self.img_id:
                self.change_image(img_id=cimage.img_id)
                break

    def update_canvas(self):


        if self.labeled_image.selected:
            self.canvas = np.copy(self.orig_image)
            h, w, c = self.canvas.shape
            self.canvas = cv2.rectangle(self.canvas, (0, 0), (w, h), (0, 255, 0), 10)
        else:
            self.canvas = self.orig_image
            
        if self.make_image_worse:
            self.canvas = self.deteriorate_image(self.canvas)