from annotation_widgets.image.labeling.drawing import draw_text_label
from annotation_widgets.image.labeling.models import Figure, Point
from annotation_widgets.image.models import Label
from db import get_session

import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings

import numpy as np


from typing import Dict, List, Tuple


class BBox(Figure):
    __tablename__ = 'bbox'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('image.id'))
    x1 = Column(Integer)
    y1 = Column(Integer)
    x2 = Column(Integer)
    y2 = Column(Integer)
    label = Column(String)

    image = relationship("LabeledImage", back_populates="bboxes")

    def __init__(self, x1, y1, x2, y2, label):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.label = label
        self.active_point_id = None
        self.selected = False
        self.point_number = 4

    @reconstructor
    def init_on_load(self):
        self.active_point_id = None
        self.selected = False
        self.point_number = 4

    @property
    def figure_type(self) -> str:
        return "BBOX"

    @property
    def surface(self) -> int:
        w = abs(self.x2 - self.x1)
        h = abs(self.y2 - self.y1)
        return w * h

    @property
    def state(self):
        return inspect(self)

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        self.point_number = 0

    def delete(self):
        if not self.state.persistent:
            return
        session = get_session()
        session.delete(self)
        session.commit()

    def copy(self) -> "BBox":
        return BBox(
            x1=self.x1,
            y1=self.y1,
            x2=self.x2,
            y2=self.y2,
            label=self.label
        )

    @property
    def points(self) -> List[Point]:

        return [
            Point(self.x1, self.y1),
            Point(self.x2, self.y1),
            Point(self.x2, self.y2),
            Point(self.x1, self.y2),
        ]

    def move_active_point(self, x, y):
        """Move the active point of the bbox."""
        if self.active_point_id is None:
            return

        opposite_point_id = (self.active_point_id + 2) % 4
        opp_point = self.points[opposite_point_id]

        self.x1=min(x, opp_point.x)
        self.y1=min(y, opp_point.y)
        self.x2=max(x, opp_point.x)
        self.y2=max(y, opp_point.y)

    def find_nearest_point_index(self, x: int, y: int) -> Optional[int]:
        """Returns id of point of near bbox"""
        for i, point in enumerate(self.points):
            if point.close_to(x, y, distance=settings.cursor_proximity_threshold):
                return i

    def contains_point(self, point: Point) -> bool:
        return self.x1 <= point.x <= self.x2 and self.y1 <= point.y <= self.y2

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

        
        if color is None:
            color = label.color_bgr

        if color_fill_opacity > 0:
            canvas_orig = np.copy(canvas)
            canvas = cv2.rectangle(
                canvas, 
                (int(self.x1), int(self.y1)), (int(self.x2), int(self.y2)), 
                color, 
                thickness=-1,
            )
            canvas = cv2.addWeighted(canvas, color_fill_opacity, canvas_orig, max(1 - color_fill_opacity, 0), 0)


        if  with_border:
            line_width = max(1, int(settings.bbox_line_width / ((elements_scale_factor + 1e-7) ** (1/3))))

            if self.selected:
                if elements_scale_factor < 3:
                    line_width += 1

            for layer_id in range(line_width):
                canvas = cv2.rectangle(
                    canvas, 
                    (int(self.x1 - layer_id), int(self.y1 - layer_id)), (int(self.x2 + layer_id), int(self.y2 + layer_id)), 
                    color, 
                    thickness=1,
                )

        label_text = None
        if show_label_names:
            label_text = label.name
        if show_object_size:
            w = abs(self.x2 - self.x1)
            h = abs(self.y2 - self.y1)
            if label_text is not None:
                label_text += f", {h}x{w}"
            else:
                label_text = f"{h}x{w}"

        if label_text is not None:
            x, y = self.x1, self.y1
            under_point = True
            if y - 20 < 0:
                y = self.y2
                under_point = False
            draw_text_label(
                canvas,
                text=label_text,
                x=x,
                y=y,
                color_bgr=color,
                padding=5,
                under_point=under_point
            )


        if show_active_point and self.active_point_id is not None:
            point = self.points[self.active_point_id]
            circle_radius = max(1, int(settings.bbox_handler_size / ((elements_scale_factor + 1e-7) ** (1/3))))
            cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (255, 255, 255), -1)
            cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (0, 0, 0), 2)

        return canvas

    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 3, figure: "BBox" = None) -> Optional[Figure]:
        x, y = end_point
        if abs(start_point[0] - x) > min_movement_to_create or abs(start_point[1] - y) > min_movement_to_create:
            x1 = min(start_point[0], x)
            y1 = min(start_point[1], y)
            x2 = max(start_point[0], x)
            y2 = max(start_point[1], y)
            if figure is None:
                figure = BBox(x1, y1, x2, y2, label=label.name)
            else:
                figure.x1=x1
                figure.y1=y1
                figure.x2=x2
                figure.y2=y2
                figure.label=label.name
            return figure

    def serialize(self) -> Dict:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "label": self.label}