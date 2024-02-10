
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from enum import Enum, auto

from tqdm import tqdm
from models import Image, Rectangle
from utils import open_json, save_json


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    ROTATING = auto()
    IDLE = auto()



class ImageCanvas:

    def __init__(self, image: np.ndarray, rectangles: List[Rectangle] = None, show_trash_label: bool = False):
        self.image = image
        self.canvas = np.copy(self.image)
        self.rectangles: list[Rectangle] = rectangles if rectangles is not None else list()
        self.selected_rectangle_id = None

        self.draw_figures = True
        self.mode = Mode.IDLE
        self.start_point: Optional[Tuple[int, int]] = None

        self.show_trash_label = show_trash_label

    @property
    def selected_rectangle(self) -> Rectangle:
        if self.selected_rectangle_id is None:
            return None
        return self.rectangles[self.selected_rectangle_id]


    def add_rectangle(self, start_point: Tuple[int, int], end_point: Tuple[int, int]):
        """ Add a new rectangle to the canvas. """
        h = abs(start_point[1] - end_point[1])
        w = abs(start_point[0] - end_point[0])
        yc = (start_point[1] + end_point[1]) / 2
        xc = (start_point[0] + end_point[0]) / 2
        rectangle = Rectangle(h, w, xc, yc)

        self.rectangles.append(rectangle)
        self.update_canvas()

    def draw_rectangle(self, canvas: np.ndarray, rectangle: Rectangle):
        """Drawing the rectangle on the canvas"""
        if not self.draw_figures:
            return canvas

        points = rectangle.points
        for i in range(4):
            p1 = points[i]
            p2 = points[(i + 1) % 4]
            canvas = cv2.line(canvas, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (255, 255, 255), 2)

        for i, point in enumerate(points):
            radius = 5
            if i == rectangle.active_point_id:
                radius = 8
            cv2.circle(canvas, (int(point[0]), int(point[1])), radius, (0, 255, 0), -1)

        return canvas

    def update_canvas(self):
        """Update the canvas with the current rectangles. """
        self.canvas = np.copy(self.image)
        for rect in self.rectangles:
            self.canvas = self.draw_rectangle(self.canvas, rect)

        if self.show_trash_label:
            self.canvas = cv2.putText(self.canvas, "TRASH", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 255), 8, cv2.LINE_AA)

    def save_canvas_state(self, file_path):
        """Save the current state of the canvas to a file. """
        cv2.imwrite(file_path, self.canvas)

    def search_near_point(self, x: int, y: int, rectangle: Rectangle, threshold: int = 10) -> Optional[int]:
        """Returns id of point of near rectangle"""
        for i, point in enumerate(rectangle.points):
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



    def move_selected_rectangle(self, x, y):
        if self.selected_rectangle is not None:
            self.selected_rectangle.move_active_point(x, y)

    def remove_rectangle(self, x, y):
        rect_id = self.get_selected_rectangle(x, y)
        if rect_id is not None:

            self.rectangles.pop(rect_id)
            
            self.selected_rectangle_id = None
            self.update_canvas()


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
        self.export_path = export_path if export_path is not None else "result.json"

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
        
        print(f'Img {self.img_id}')
        img_name = self.img_names[self.img_id]
        img_mat = cv2.imread(os.path.join(self.img_dir, img_name))
        image = Image.get(name=img_name)


        # Draw img id on image
        cv2.putText(img_mat, str(self.img_id), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 1, cv2.LINE_AA)


        if self.canvas is None:
            self.canvas = ImageCanvas(
                rectangles = list(image.rectangles),
                image = img_mat,
                show_trash_label = image.trash
            )
        else:
            self.canvas.rectangles = list(image.rectangles)
            self.canvas.image = img_mat
            self.canvas.show_trash_label = image.trash
        
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

        self.save_image()

        result_images = dict()
        for image_name in tqdm(self.img_names, desc=f"Exporting data to {self.export_path}"):
            image = Image.get(name=image_name)
            result_images[image.name] = {"trash": image.trash, "rectangles": [rectangle.points for rectangle in image.rectangles]}

        save_json(result_images, self.export_path) 

    def toggle_image_trash_tag(self):
        image = Image.get(name=self.img_names[self.img_id])
        if image.trash:
            image.trash = False
        else:
            image.trash = True
        image.save()
        self.canvas.show_trash_label = image.trash
        self.canvas.update_canvas()

    def switch_drawing_figures(self):
        if self.canvas.draw_figures:
            self.canvas.draw_figures = False
        else:
            self.canvas.draw_figures = True
        self.canvas.update_canvas()

    def copy_figures_from_previous_image(self):
        if self.img_id > 0:
            prev_image = Image.get(name=self.img_names[self.img_id - 1])
            self.canvas.rectangles = [rect.copy() for rect in prev_image.rectangles]
        self.canvas.update_canvas()

