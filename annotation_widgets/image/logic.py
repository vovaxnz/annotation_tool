
from abc import ABC, abstractmethod
import cv2
import numpy as np
from annotation_widgets.logic import AbstractAnnotationLogic
from models import ProjectData


class AbstractImageAnnotationLogic(AbstractAnnotationLogic):

    def __init__(self, data_path: str, project_data: ProjectData):
        self.canvas: np.ndarray = None
        self.orig_image: np.ndarray = None
        self.image_changed = False
        self.make_image_worse: bool = False
        super().__init__(data_path, project_data)
    
    @abstractmethod
    def update_canvas(self): 
        raise NotImplementedError

    def deteriorate_image(self, img) -> np.ndarray:
        img = cv2.GaussianBlur(src=img, ksize=(31, 31), sigmaX=0)
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv_img[:, :, 1] = hsv_img[:, :, 1] * 0.5  # reduce saturation to 50%
        img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
        return img

    def start_selecting_class(self):
        pass

    def end_selecting_class(self):
        pass