
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
import json
from enum import Enum, auto
import config

from tqdm import tqdm
from geometry import distort_point
from models import Image, Rectangle
from utils import open_json, save_json


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    ROTATING = auto()
    IDLE = auto()


class CoordinateTransformer:
    def __init__(self, 
            homography_matrix: str,
            homography_matrix_reversed: str, 
        ): 
        self.view_to_scheme_matrix = np.array(homography_matrix)
        self.scheme_to_view_matrix = np.array(homography_matrix_reversed)

    def view_to_scheme(self, x: float, y: float) -> Tuple[float, float]:
        return self._transform(x, y, self.view_to_scheme_matrix)
    
    def scheme_to_view(self, x: float, y: float) -> Tuple[float, float]:
        return self._transform(x, y, self.scheme_to_view_matrix)
    
    def _transform(self, x: float, y: float, matrix) -> Tuple[float, float]:
        source_position = np.array([x, y], dtype=np.float32)
        result_position = cv2.perspectiveTransform(np.array([source_position[None, :]], dtype=np.float32), matrix)
        return tuple(result_position[0][0])


class ImageCanvas:

    def __init__(self, image: np.ndarray, ct: CoordinateTransformer, rectangles: List[Rectangle] = None):
        """
        Initialize a new ImageCanvas object.

        :param width: Width of the canvas.
        :param height: Height of the canvas.
        """
        self.image = image
        self.rectangles: list[Rectangle] = rectangles if rectangles is not None else list()
        self.ct: CoordinateTransformer = ct
        self.selected_rectangle_id = None

        self.mode = Mode.IDLE
        self.start_point: Optional[Tuple[int, int]] = None

    @property
    def selected_rectangle(self) -> Rectangle:
        if self.selected_rectangle_id is None:
            return None
        return self.rectangles[self.selected_rectangle_id]


    def add_rectangle(self, start_point: Tuple[int, int], end_point: Tuple[int, int]):
        """ Add a new rectangle to the canvas. """

        # Convert points to scheme
        start_point_scheme = self.ct.view_to_scheme(*start_point)
        end_point_scheme = self.ct.view_to_scheme(*end_point)

        h = abs(start_point_scheme[1] - end_point_scheme[1])
        w = abs(start_point_scheme[0] - end_point_scheme[0])
        yc = abs((start_point_scheme[1] + end_point_scheme[1]) / 2)
        xc = abs((start_point_scheme[0] + end_point_scheme[0]) / 2)
        rectangle = Rectangle(h, w, xc, yc)

        self.rectangles.append(rectangle)
        self.update_canvas()

    def draw_rectangle(self, canvas: np.ndarray, rectangle: Rectangle):
        """Drawing the rectangle on the canvas"""
        points = rectangle.points
        for i in range(4):
            p1 = points[i]
            p2 = points[(i + 1) % 4]
            
            # Convert scheme to view
            p1_v = self.ct.scheme_to_view(*p1)
            p2_v = self.ct.scheme_to_view(*p2)

            canvas = cv2.line(canvas, (int(p1_v[0]), int(p1_v[1])), (int(p2_v[0]), int(p2_v[1])), (255, 255, 255), 2)

        for i, point in enumerate(points):
            color = config.POINT_COLORS[i]
            point = self.ct.scheme_to_view(*point)
            radius = 5
            if i == rectangle.active_point_id:
                radius = 8
            cv2.circle(canvas, (int(point[0]), int(point[1])), radius, color, -1)

        return canvas

    def update_canvas(self):
        """Update the canvas with the current rectangles. """
        self.canvas = np.copy(self.image)
        for rect in self.rectangles:
            self.canvas = self.draw_rectangle(self.canvas, rect)

    def save_canvas_state(self, file_path):
        """Save the current state of the canvas to a file. """
        cv2.imwrite(file_path, self.canvas)

    def search_near_point(self, x: int, y: int, rectangle: Rectangle, threshold: int = 10) -> Optional[int]:
        """Returns id of point of near rectangle"""
        for i, point in enumerate(rectangle.points):
            point = self.ct.scheme_to_view(*point)
            if abs(point[0] - x) <= threshold and abs(point[1] - y) <= threshold:
                return i
    
    def get_selected_rectangle(self, x: int, y: int) -> int:
        for rect_i, rect in enumerate(self.rectangles):
            near_point_id = self.search_near_point(x, y, rect)
            if near_point_id is not None:
                rect.active_point_id = near_point_id 
                self.selected_rectangle_id = rect_i
                return self.selected_rectangle_id

    def complete_drawing(self, x: int, y: int):
        if self.start_point:
            self.add_rectangle(start_point=self.start_point, end_point=(x, y))
            self.start_point = None
            self.mode = Mode.IDLE

    def complete_rectangle(self):
        if self.selected_rectangle is not None:
            self.selected_rectangle.active_point_id = None 
            self.selected_rectangle_id = None
        self.update_canvas()

    def rotate_selected_rectangle(self, x, y):
        if self.selected_rectangle is not None:
            x, y = self.ct.view_to_scheme(x, y)
            self.selected_rectangle.rotate_by_active_point(x, y)

    def move_selected_rectangle(self, x, y):
        if self.selected_rectangle is not None:
            x, y = self.ct.view_to_scheme(x, y)
            self.selected_rectangle.move_active_point(x, y)

    def remove_rectangle(self, x, y):
        rect_id = self.get_selected_rectangle(x, y)
        if rect_id is not None:

            self.rectangles.pop(rect_id)
            
            self.selected_rectangle_id = None
            self.update_canvas()

def undistort_image(img: np.ndarray, mtx, dist, new_camera_mtx):
    return cv2.undistort(img, mtx, dist, None, new_camera_mtx)

def get_cam_config_for_img_name(img_name):
    for cam_name, cfg in config.cam_configs.items():
        if cam_name in img_name:
            return cfg
    raise RuntimeError(f"Config for image {img_name} is not found")


class LabelingApp:

    def __init__(self, img_dir: str, export_path: str):    
        self.canvas: ImageCanvas = None

        # Add images from the directory to the database
        self.img_names = sorted(os.listdir(img_dir))
        for img_name in self.img_names:
            img_object = Image.get(name=img_name)
            if img_object is None:
                img_object = Image(name=img_name)
                img_object.save()

        self.img_dir = img_dir
        self.export_path = export_path

        self.img_id = 0
        self.load_image()
    
    def handle_left_click(self, x: int, y: int):
        if self.canvas.mode == Mode.IDLE:
            rect_id = self.canvas.get_selected_rectangle(x, y)
            if rect_id is not None:
                self.canvas.mode = Mode.MOVING
            else:
                self.canvas.start_point = (x, y)
                self.canvas.mode = Mode.DRAWING
        elif self.canvas.mode == Mode.DRAWING:
            self.canvas.complete_drawing(x, y)
            self.canvas.mode = Mode.IDLE

    def handle_right_click(self, x: int, y: int):
        if self.canvas.mode == Mode.IDLE:
            rect_id = self.canvas.get_selected_rectangle(x, y)
            if rect_id is not None:
                self.canvas.mode = Mode.ROTATING
    
    def handle_middle_click(self, x: int, y: int):
        self.canvas.remove_rectangle(x, y)
        self.canvas.mode = Mode.IDLE

    def handle_mouse_move(self, x: int, y: int):
        if self.canvas.mode == Mode.MOVING:
            self.canvas.move_selected_rectangle(x, y)
        elif self.canvas.mode == Mode.ROTATING:
            self.canvas.rotate_selected_rectangle(x, y)
        self.canvas.update_canvas() 

    def handle_mouse_release(self, x: int, y: int):
        if self.canvas.mode in [Mode.MOVING, Mode.ROTATING]:
            self.canvas.complete_rectangle()
            self.canvas.mode = Mode.IDLE

    def load_image(self):

        img_name = self.img_names[self.img_id]
        img_mat = cv2.imread(os.path.join(self.img_dir, img_name))
        image = Image.get(name=img_name)

        # Select cam config for this image 
        cam_config: config.CamConfig = get_cam_config_for_img_name(img_name)

        # Set image, rectangles, ct to canvas
        img_mat = undistort_image(
            img_mat, 
            mtx=cam_config.undistort["mtx"], 
            dist=cam_config.undistort["dist"], 
            new_camera_mtx=cam_config.undistort["new_camera_mtx"]
        )

        # Draw img id on image
        cv2.putText(img_mat, str(self.img_id), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 1, cv2.LINE_AA)

        ct = CoordinateTransformer(
            homography_matrix=cam_config.transform_v2s,
            homography_matrix_reversed=cam_config.transform_s2v, 
        )

        if self.canvas is None:
            self.canvas = ImageCanvas(
                ct = ct,
                rectangles = list(image.rectangles),
                image = img_mat,
            )
        else:
            self.canvas.ct = ct
            self.canvas.rectangles = list(image.rectangles)
            self.canvas.image = img_mat
        
        self.canvas.update_canvas()

    def save_image(self): 
        image = Image.get(name=self.img_names[self.img_id])
        image.rectangles = self.canvas.rectangles 
        image.save()

    def forward(self):
        # Save previous image with rectangles to db
        self.save_image()

        # Take new image name if this is not the end of the list
        if self.img_id < len(self.img_names) - 1:
            self.img_id += 1

        # load new image
        self.load_image()

    def backward(self):
        # Save previous image with rectangles to db
        self.save_image()

        if self.img_id > 0:
            self.img_id -= 1

        # load new image
        self.load_image()

    def export_data(self):

        result_images = dict()

        for image_name in tqdm(self.img_names, desc=f"Exporting data to {self.export_path}"):
            image = Image.get(name=image_name)
            cfg = get_cam_config_for_img_name(image_name)

            ct = CoordinateTransformer(             
                homography_matrix=cfg.transform_v2s,
                homography_matrix_reversed=cfg.transform_s2v, 
            )
            rectangles_2d = list()
            for rectangle in image.rectangles:
                points = rectangle.points
                result_points = list()
                for p in points:
                    p = ct.scheme_to_view(*p)
                    p = distort_point(p[0], p[0], mtx=cfg.undistort["mtx"], dist=cfg.undistort["dist"], new_camera_mtx=cfg.undistort["new_camera_mtx"])
                    result_points.append(p)
                rectangles_2d.append(result_points)
                
            result_images[image.name] = rectangles_2d

        save_json(result_images, self.export_path) 
