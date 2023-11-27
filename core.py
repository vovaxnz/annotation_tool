import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
import json


def find_line_equation(x, y, angle_degrees):
    # Calculate the slope (m) using the tangent of the angle
    angle_radians = math.radians(angle_degrees)
    m = math.tan(angle_radians)
    # Calculate the y-intercept (b) using the point (xa, ya)
    b = y - m * x
    return m, b

def find_intersection(m1, b1, m2, b2):
    # Check if the lines are parallel (slopes are equal)
    if m1 == m2:
        return None  # No intersection (or infinite intersections if b1 == b2)
    # Calculate the x-coordinate of the intersection
    x = (b2 - b1) / (m1 - m2)
    # Calculate the y-coordinate of the intersection using either line equation
    y = m1 * x + b1
    return x, y

def line_length(x1, y1, x2, y2) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def open_json(detections_file) -> Dict:
    with open(detections_file) as file:
        value = json.load(file)
    return value


class CoordinateTransformer:
    def __init__(self, 
            homography_matrix_path: str,
            homography_matrix_reversed_path: str, 
        ): 
        self.view_to_scheme_matrix = np.array(open_json(homography_matrix_path))
        self.scheme_to_view_matrix = np.array(open_json(homography_matrix_reversed_path))

    def view_to_scheme(self, x: float, y: float) -> Tuple[float, float]:
        return self._transform(x, y, self.view_to_scheme_matrix)
    
    def scheme_to_view(self, x: float, y: float) -> Tuple[float, float]:
        return self._transform(x, y, self.scheme_to_view_matrix)
    
    def _transform(self, x: float, y: float, matrix) -> Tuple[float, float]:
        source_position = np.array([x, y], dtype=np.float32)
        result_position = cv2.perspectiveTransform(np.array([source_position[None, :]], dtype=np.float32), matrix)
        return tuple(result_position[0][0])


class Rectangle:
    def __init__(self, h, w, xc, yc, angle=0):
        self.h = h
        self.w = w
        self.xc = xc
        self.yc = yc
        self.angle = angle
        self.active_point_id = None # id of active point (0, 1, 2 or 3)

    @property
    def points(self) -> List[Tuple[float, float]]:
        """Returns points in order [[0, 0], [w, 0], [w, h], [0, h]] and rotated around [xc, yc] by angle. 
        Calculate new h, w, xc, yc values based on moved active point. 
        The position of opposite point to the active point remains the same"""

        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        points = [(0, 0), (self.w, 0), (self.w, self.h), (0, self.h)]
        return [
            (
                cos_a * (x - self.w / 2) - sin_a * (y - self.h / 2) + self.xc,
                sin_a * (x - self.w / 2) + cos_a * (y - self.h / 2) + self.yc
            ) for x, y in points
        ]

    def move_active_point(self, x, y):
        """Move the active point of the rectangle."""
        if self.active_point_id is None:
            return
        
        opposite_point_id = (self.active_point_id + 2) % 4
        opp_x, opp_y = self.points[opposite_point_id]

        if self.active_point_id in [0, 2]:
            act_angle, opp_angle = self.angle, self.angle + 90
        else:
            act_angle, opp_angle = self.angle + 90, self.angle
            
        act_m, act_b = find_line_equation(x, y, angle_degrees=act_angle)
        opp_m, opp_b = find_line_equation(opp_x, opp_y, angle_degrees=opp_angle)
        intersection = find_intersection(act_m, act_b, opp_m, opp_b)
        if intersection is None:
            return
        int_x, int_y = intersection
        self.xc = (x + opp_x) / 2
        self.yc = (y + opp_y) / 2

        if self.active_point_id in [0, 2]:
            self.w = line_length(x, y, int_x, int_y) 
            self.h = line_length(opp_x, opp_y, int_x, int_y) 
        else:
            self.h = line_length(x, y, int_x, int_y) 
            self.w = line_length(opp_x, opp_y, int_x, int_y) 


    def rotate_by_active_point(self, x, y):
        """Rotate the rectangle by active point around the center. 
        Calculate new `angle` value based on x, y position. 
        This transformation is not change h, w, xc and yc, it change only `angle`. 
        We imagine the line from the (xc, yc) to (x, y) and the active point 
        should be on this line. The angle on which we need to rotate a rectangle 
        to achieve that is a delta which we need to add to the `angle` value."""
        
        if self.active_point_id is None:
            return

        # Current active point
        active_x, active_y = self.points[self.active_point_id]

        # Angle from center to new position
        angle_to_new = math.degrees(math.atan2(y - self.yc, x - self.xc))
        # Angle from center to current active point
        angle_to_current = math.degrees(math.atan2(active_y - self.yc, active_x - self.xc))

        # Calculate the difference
        angle_delta = angle_to_new - angle_to_current
        self.angle += angle_delta


class ImageCanvas:
    def __init__(self, width, height, ct: CoordinateTransformer):
        """
        Initialize a new ImageCanvas object.

        :param width: Width of the canvas.
        :param height: Height of the canvas.
        """
        self.width = width
        self.height = height
        self.rectangles: list[Rectangle] = []  # List of Rectangle objects
        self.canvas = self.create_blank_canvas()
        self.ct: CoordinateTransformer = ct
        self.selected_rectangle = None

    def create_blank_canvas(self):
        # Create a blank canvas
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

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
        for i in range(4):
            p1 = rectangle.points[i]
            p2 = rectangle.points[(i + 1) % 4]
            
            # Convert scheme to view
            p1_v = self.ct.scheme_to_view(*p1)
            p2_v = self.ct.scheme_to_view(*p2)

            canvas = cv2.line(canvas, (int(p1_v[0]), int(p1_v[1])), (int(p2_v[0]), int(p2_v[1])), (255, 255, 255), 1)
        return canvas

    def update_canvas(self):
        """Update the canvas with the current rectangles. """
        self.canvas = self.create_blank_canvas()
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
    
    def get_selected_rectangle(self, x: int, y: int) -> bool:
        for rect in self.rectangles:
            near_point_id = self.search_near_point(x, y, rect)
            if near_point_id is not None:
                rect.active_point_id = near_point_id 
                self.selected_rectangle = rect
                return True
        return False

    def complete_rectangle(self):
        if self.selected_rectangle is not None:
            # self.db_manager.saveRectangleData(self.selected_rectangle) # TODO
            self.selected_rectangle.active_point_id = None
            self.selected_rectangle = None

    def rotate_selected_rectangle(self, x, y):
        if self.selected_rectangle is not None:
            x, y = self.ct.view_to_scheme(x, y)
            self.selected_rectangle.rotate_by_active_point(x, y)

    def move_selected_rectangle(self, x, y):
        if self.selected_rectangle is not None:
            x, y = self.ct.view_to_scheme(x, y)
            self.selected_rectangle.move_active_point(x, y)