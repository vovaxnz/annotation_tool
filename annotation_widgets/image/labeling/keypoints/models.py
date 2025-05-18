from annotation_widgets.image.labeling.drawing import draw_text_label
from annotation_widgets.image.labeling.models import Figure, Point
from annotation_widgets.image.models import Label
from config import ColorBGR
from db import get_session

import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings



import numpy as np


import json
from typing import Dict, List, Tuple


class KeypointGroup(Figure):
    __tablename__ = 'keypoint_group'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('image.id'))
    label = Column(String)
    keypoints_data = Column(String) # "[{"x": ..., "y": ..., "label": ...}, ...]"

    image = relationship("LabeledImage", back_populates="kgroups")

    def __init__(self, label: str, keypoints_data: str):
        self.label = label
        self.keypoints_data = keypoints_data
        self.active_point_id = None
        self.selected = False
        self.keypoints: List[Point] = self.deserialize_keypoints(self.keypoints_data)
        self.point_number = len(self.keypoints)

    @reconstructor
    def init_on_load(self):
        self.active_point_id = None
        self.selected = False
        self.keypoints: List[Point] = self.deserialize_keypoints(self.keypoints_data)
        self.point_number = len(self.keypoints)

    @property
    def figure_type(self) -> str:
        return "KGROUP"

    @property
    def surface(self) -> int:
        return 1

    @property
    def keypoints_as_dict(self) -> Dict[str, Point]:
        return {kp.label: kp for kp in self.keypoints}

    @property
    def state(self):
        return inspect(self)

    def save(self):
        session = get_session()
        self.keypoints_data = self.serialize_keypoints(self.keypoints)
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        self.keypoints.pop(point_id)
        if len(self.keypoints) == 1: # Remove both keypoints if there are 2 kepoints left
            self.keypoints = list()
        self.keypoints_data = self.serialize_keypoints(self.keypoints)
        self.point_number = len(self.keypoints)

    def delete(self):
        if not self.state.persistent:
            return
        session = get_session()
        session.delete(self)
        session.commit()

    def copy(self) -> "KeypointGroup":
        return KeypointGroup(
            label=self.label,
            keypoints_data=self.serialize_keypoints(self.keypoints),
        )

    def move_active_point(self, x, y):
        if self.active_point_id is None:
            return
        self.keypoints[self.active_point_id].x = x
        self.keypoints[self.active_point_id].y = y
        self.keypoints_data = self.serialize_keypoints(self.keypoints)

    def find_nearest_point_index(self, x: int, y: int) -> Optional[int]:
        for i, point in enumerate(self.keypoints):
            if point.close_to(x, y, distance=settings.cursor_proximity_threshold):
                return i

    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "KeypointGroup" = None) -> Optional[Figure]:
        x1, y1 = start_point
        x2, y2 = end_point

        if abs(x1 - x2) > min_movement_to_create or abs(y1 - y2) > min_movement_to_create:

            reflect_x = False
            reflect_y = False
            if x2 < x1:
                reflect_x = True
            if y2 < y1:
                reflect_y = True

            w = abs(x2 - x1)
            h = abs(y2 - y1)

            assert label.attributes is not None
            keypoint_info = json.loads(label.attributes)["keypoint_info"]

            result_keypoints = list()
            for kp_label in keypoint_info:
                if reflect_x:
                    kp_x = x1 - keypoint_info[kp_label]["x"] * w
                else:
                    kp_x = keypoint_info[kp_label]["x"] * w + x1
                if reflect_y:
                    kp_y = y1 - keypoint_info[kp_label]["y"] * h
                else:
                    kp_y = keypoint_info[kp_label]["y"] * h + y1

                result_keypoints.append(Point(x=int(kp_x), y=int(kp_y), label=kp_label))


            keypoints_data = KeypointGroup.serialize_keypoints(result_keypoints)

            if figure is None:
                figure = KeypointGroup(
                    label=label.name,
                    keypoints_data=keypoints_data
                )
            else:
                figure.label = label.name
                figure.keypoints_data = keypoints_data
                figure.keypoints = figure.deserialize_keypoints(figure.keypoints_data)
            return figure

    def draw_figure(
            self,
            canvas: np.ndarray,
            elements_scale_factor: float,
            label: Label,
            show_label_names: bool = False,
            show_object_size: bool = False,
            with_border: bool = True,
            color_fill_opacity: float = 0,
            color: Tuple[int, int, int] = None,
            show_active_point: bool = True
        ) -> np.ndarray:

        line_width = max(1, int(3 / ((elements_scale_factor + 1e-7) ** (1/3))))

        if self.selected:
            if elements_scale_factor < 3:
                line_width += 2
            else:
                line_width += 1

        kp_dict: Dict[str, Point] = self.keypoints_as_dict


        assert label.attributes is not None
        keypoint_info = json.loads(label.attributes)["keypoint_info"]
        keypoint_connections = json.loads(label.attributes)["keypoint_connections"]

        # Draw connections
        for connection in keypoint_connections:
            kp1 = kp_dict.get(connection["from"])
            kp2 = kp_dict.get(connection["to"])
            if kp1 is None or kp2 is None:
                continue
            color = getattr(ColorBGR, connection["color"], ColorBGR.white)
            cv2.line(canvas, (kp1.x, kp1.y), (kp2.x, kp2.y), color, line_width)

        # Draw kpoints
        for i, kp in enumerate(self.keypoints):
            highlight_keypoint = True if i == self.active_point_id else False

            kp_color_name = keypoint_info[kp.label]["color"]
            color_bgr=getattr(ColorBGR, kp_color_name, ColorBGR.white)

            if show_label_names:
                draw_text_label(
                    canvas,
                    text=kp.label,
                    x=kp.x,
                    y=kp.y,
                    color_bgr=color_bgr,
                    padding = 5,
                    under_point = True
                )

            circle_radius = max(1, int(settings.keypoint_handler_size / ((elements_scale_factor + 1e-7) ** (1/3))))

            if highlight_keypoint:
                circle_radius += 1

            cv2.circle(canvas, (int(kp.x), int(kp.y)), circle_radius, color_bgr, -1)

        return canvas

    @staticmethod
    def serialize_keypoints(keypoints: List[Point]) -> str:
        result = list()
        for kp in keypoints:
            result.append(kp.serialize())
        return json.dumps(result)

    @staticmethod
    def deserialize_keypoints(data: str) -> List[Point]:
        kp_serialized = json.loads(data)
        result = list()
        for kp in kp_serialized:
            result.append(Point(x=kp["x"], y=kp["y"], label=kp["label"]))
        return result

    def contains_point(self, point: Point) -> bool:
        return False

    def serialize(self) -> Dict:
        self.keypoints_data = self.serialize_keypoints(self.keypoints)
        return {"keypoints_data": self.keypoints_data, "label": self.label}