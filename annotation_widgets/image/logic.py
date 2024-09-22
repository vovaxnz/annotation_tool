
from abc import ABC, abstractmethod
import json
import time
import cv2
import numpy as np
from enums import AnnotationMode, AnnotationStage
from models import ProjectData
from models import Value
from path_manager import PathManager
from utils import get_datetime_str


class AbstractImageAnnotationLogic(ABC):

    def __init__(self, data_path: str, project_data: ProjectData):

        self.project_id = project_data.id
        self.project_uid = project_data.uid
        self.annotation_mode: AnnotationMode = project_data.mode
        self.annotation_stage: AnnotationStage = project_data.stage

        self.tick_time = time.time()
        self.max_action_time_sec = 60
        self.img_id = 0 
        self.duration_hours = 0
        self.processed_img_ids: set = set()

        self.canvas: np.ndarray = None
        self.orig_image: np.ndarray = None
        self.image_changed = False

        self.ready_for_export = False

        self.make_image_worse: bool = False

        self.pm = PathManager(project_id=self.project_id)

        self.load_state()
        self.load_image(next=False)

    @property
    def img_number(self) -> int:
        raise NotImplementedError

    @property
    def status_data(self):
        raise NotImplementedError

    def update_time_counter(self, message: str = None):
        with open(self.pm.statistics_path, 'a+') as file:
            file.write(f"{self.annotation_stage.name},{get_datetime_str()},{message}\n")
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600
    
    @abstractmethod
    def update_canvas(self): 
        raise NotImplementedError

    @abstractmethod
    def load_image(self, next: bool = True):
        raise NotImplementedError

    @abstractmethod
    def save_image(self):
        raise NotImplementedError

    def deteriorate_image(self, img) -> np.ndarray:
        img = cv2.GaussianBlur(src=img, ksize=(31, 31), sigmaX=0)
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv_img[:, :, 1] = hsv_img[:, :, 1] * 0.5  # reduce saturation to 50%
        img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
        return img

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
        
        assert self.img_id < self.img_number, f"Incorrect img_id {self.img_id}. The number of images is {self.img_number}"

    @abstractmethod
    def change_image(self, img_id: int):
        raise NotImplementedError

    def forward(self):
        self.change_image(img_id=self.img_id+1)
        
    def backward(self):
        self.change_image(img_id=self.img_id-1)

    def go_to_image_by_id(self, img_id: int):
        self.change_image(img_id=img_id)

    def start_selecting_class(self): # ?
        pass

    def end_selecting_class(self): # ?
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

    def handle_key(self, key: str):
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