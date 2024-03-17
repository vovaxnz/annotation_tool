import json
from config import AnnotationMode, AnnotationStage, ColorBGR
from drawing import draw_text_label
from labeling_app.labeling import LabelingApp, Mode, Visualizable
from models import KeypointGroup, LabeledImage, Point, Value

import cv2
import numpy as np

from typing import Dict, List, Optional, Tuple


class KeypointLabelingApp(LabelingApp):

    def __init__(
            self, 
            img_dir: str,  
            annotation_stage: AnnotationStage, 
            annotation_mode: AnnotationMode, 
            project_id: int, 
            secondary_visualizer: Visualizable = None
        ):
        self.start_point: Optional[Tuple[int, int]] = None
        self.keypoint_connections: List = json.loads(Value.get_value("keypoint_connections"))
        self.keypoint_info: Dict = json.loads(Value.get_value("keypoint_info")) 
        super().__init__(
            img_dir=img_dir, 
            annotation_stage=annotation_stage, 
            annotation_mode=annotation_mode, 
            project_id=project_id, 
            secondary_visualizer=secondary_visualizer
        )
        self.load_image()
        self.preview_figure: KeypointGroup = None # TODO: Add the same to bboxLabelingApp

    def draw_figure(self, canvas: np.ndarray, figure: KeypointGroup, highlight: bool = False) -> np.ndarray:
        """Drawing the bbox on the canvas"""

        line_width = max(1, int(3 / ((self.scale_factor + 1e-7) ** (1/3))))

        if highlight:
            if self.scale_factor < 3:
                line_width += 2
            else:
                line_width += 1

        kp_dict: Dict[str, Point] = figure.keypoints_as_dict
        
        # Draw connections
        for connection in self.keypoint_connections:
            kp1 = kp_dict.get(connection["from"])
            kp2 = kp_dict.get(connection["to"])
            if kp1 is None or kp2 is None:
                continue
            color = getattr(ColorBGR, connection["color"], ColorBGR.white)
            cv2.line(canvas, (kp1.x, kp1.y), (kp2.x, kp2.y), color, line_width)

        # Draw kpoints
        for i, kp in enumerate(figure.keypoints):
            highlight_keypoint = True if i == figure.active_point_id else False

            kp_color_name = self.keypoint_info[kp.label]["color"]
            color_bgr=getattr(ColorBGR, kp_color_name, ColorBGR.white)

            if self.show_label_names:
                draw_text_label(
                    canvas, 
                    text=kp.label, 
                    x=kp.x, 
                    y=kp.y, 
                    color_bgr=color_bgr, 
                    padding = 5, 
                    under_point = True
                )
            
            circle_radius = max(1, int(5 / ((self.scale_factor + 1e-7) ** (1/3))))
            
            if highlight_keypoint:
                circle_radius += 1
            
            cv2.circle(canvas, (int(kp.x), int(kp.y)), circle_radius, color_bgr, -1)

        return canvas

    def update_canvas(self): 
        super().update_canvas()

        h, w, c = self.canvas.shape

        # Draw vertical and horizontal lines (black and white) # TODO: Show only for bboxes
        self.canvas = cv2.line(self.canvas, (int(self.cursor_x), 0), (int(self.cursor_x), h), (255, 255, 255), 1)
        self.canvas = cv2.line(self.canvas, (int(self.cursor_x + 1), 0), (int(self.cursor_x + 1), h), (0, 0, 0), 1)
        self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y)), (w, int(self.cursor_y)), (255, 255, 255), 1)
        self.canvas = cv2.line(self.canvas, (0, int(self.cursor_y + 1)), (w, int(self.cursor_y + 1)), (0, 0, 0), 1)

        if self.preview_figure is not None:
            self.draw_figure(self.canvas, self.preview_figure)

    def get_figure_point_id(self, x: int, y: int) -> Tuple[Optional[int], Optional[int]]:
        for figure_id, figure in enumerate(self.figures):
            near_point_id = figure.find_nearest_point_index(x, y)
            if near_point_id is not None:
                return figure_id, near_point_id
        return None, None

    def get_selected_figure_id(self, x: int, y: int) -> Optional[int]:
        selected_figure_id, near_point_id = self.get_figure_point_id(x, y)
        return selected_figure_id

    def update_selection(self, x: int, y: int):
        self.selected_figure_id, near_point_id = self.get_figure_point_id(x, y)
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = near_point_id

    def update_preview_figure(self, x: int, y: int):
        if self.start_point is not None:
            if abs(self.start_point[0] - x) > self.min_movement_to_create and abs(self.start_point[1] - y) > self.min_movement_to_create:
                x1 = min(self.start_point[0], x)
                y1 = min(self.start_point[1], y)
                x2 = max(self.start_point[0], x)
                y2 = max(self.start_point[1], y)

                w = x2 - x1
                h = y2 - y1

                result_keypoints = list()
                for kp_label in self.keypoint_info:
                    kp_x = self.keypoint_info[kp_label]["x"] * w + x1
                    kp_y = self.keypoint_info[kp_label]["y"] * h + y1
                    result_keypoints.append(Point(x=int(kp_x), y=int(kp_y), label=kp_label))

                self.preview_figure = KeypointGroup(
                    label=self.active_label.name,
                    keypoint_data=KeypointGroup.serialize_keypoints(result_keypoints)
                )
            self.image_changed = True
        else:
            self.preview_figure = None

    def release_figure(self):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].active_point_id = None
            self.selected_figure_id = None
        self.image_changed = True

    def move_selected_figure(self, x, y):
        if self.selected_figure_id is not None:
            self.figures[self.selected_figure_id].move_active_point(x, y)
        self.image_changed = True

    def save_image(self):
        if self.image_changed:
            image = LabeledImage.get(name=self.img_names[self.img_id])
            for figure in self.figures:
                figure.keypoints_data = KeypointGroup.serialize_keypoints(figure.keypoints)
            image.kgroups = self.figures
            image.trash = self.is_trash
            image.save()

    def handle_mouse_move(self, x: int, y: int):
        self.cursor_x, self.cursor_y = x, y
        if self.mode == Mode.MOVING:
            self.move_selected_figure(x, y)
        self.update_canvas()

    def handle_left_mouse_release(self, x: int, y: int):
        if self.mode == Mode.MOVING:
            self.release_figure()
            self.mode = Mode.IDLE
        self.update_selection(x, y)
        self.update_canvas()

    def handle_left_mouse_press(self, x: int, y: int):

        if self.mode == Mode.IDLE:
            rect_id, point_id = self.get_figure_point_id(x, y)
            if point_id is not None:
                self.selected_figure_id = rect_id
                self.figures[rect_id].active_point_id = point_id
                self.mode = Mode.MOVING
            else:
                self.start_point = (x, y)
                self.mode = Mode.CREATE

        elif self.mode == Mode.CREATE:

            if self.preview_figure is not None:
                self.figures.append(self.preview_figure)
                self.preview_figure = None
                self.image_changed = True
                self.start_point = None
                self.mode = Mode.IDLE
                self.update_selection(x, y)
        self.update_canvas()

    def handle_mouse_hover(self, x: int, y: int):
        if self.mode == Mode.CREATE:
            self.update_preview_figure(x, y)
        self.update_selection(x, y)
        self.cursor_x, self.cursor_y = x, y
        self.update_canvas()

    def remove_selected_figure(self):
        self.selected_figure_id, near_point_id = self.get_figure_point_id(self.cursor_x, self.cursor_y)
        if self.selected_figure_id is not None:
            figure = self.figures[self.selected_figure_id]
            figure.keypoints.pop(near_point_id)
            if len(figure.keypoints) == 0:
                figure.delete()
                self.figures.pop(self.selected_figure_id)
                self.selected_figure_id = self.get_selected_figure_id(self.cursor_x, self.cursor_y)
            self.update_canvas()
            self.image_changed = True

    @staticmethod
    def get_image_figures(image: LabeledImage) -> List[KeypointGroup]: 
        return image.kgroups
