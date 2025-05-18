from abc import ABC, abstractmethod

from annotation_widgets.image.models import Label
from db import Base, get_session

import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, String, Integer, ForeignKey, inspect, func
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings


class LabeledImage(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    height = Column(Integer)
    width = Column(Integer)
    trash = Column(Boolean, default=False)
    requires_annotation = Column(Boolean, default=True)

    bboxes = relationship("BBox", back_populates="image")
    kgroups = relationship("KeypointGroup", back_populates="image")
    review_labels = relationship("ReviewLabel", back_populates="image")
    masks = relationship("Mask", back_populates="image")

    @classmethod
    def get(cls, name):
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()

    @classmethod
    def all(cls) -> List["LabeledImage"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))

    def __init__(self, name, height, width):
        self.name = name
        self.height = height
        self.width = width

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    @classmethod
    def save_batch(cls, limages: List["LabeledImage"]):
        session = get_session()
        for limage in limages:
            session.add(limage)
        session.commit()

    def delete(self):
        session = get_session()
        for bbox in self.bboxes:
            session.delete(bbox)
        for review_label in self.review_labels:
            session.delete(review_label)
        for kgroup in self.kgroups:
            session.delete(kgroup)
        for mask in self.masks:
            session.delete(mask)
        session.delete(self)
        session.commit()

    def clear_review_labels(self):
        for review_label in self.review_labels:
            review_label.delete()



class Point:

    def __init__(self, x, y, label: str = None):
        self.x = x
        self.y = y
        self.label = label

    def close_to(self, x, y, distance=8) -> bool:
        return abs(self.x - x) <= distance and abs(self.y - y) <= distance

    def serialize(self) -> Dict:
        return {"x": self.x, "y": self.y, "label": self.label}


class Figure(Base, ABC):
    __abstract__ = True  # Make sure Figure is not created as a table

    def __init__(self):
        self.active_point_id: int
        self.selected: bool = False
        self.point_number = 1
        self.label: Label

    @abstractmethod
    def draw_figure(
            self,
            canvas: np.ndarray,
            elements_scale_factor: float,
            label: Label,  # TODO: Use Label reference from the database
            show_label_names: bool = False,
            show_object_size: bool = False,
            with_border: bool = True,
            color_fill_opacity: float = 0,
            color: Tuple[int, int, int] = None,
            show_active_point: bool = True
        ) -> np.ndarray:
        raise NotImplementedError

    @property
    @abstractmethod
    def figure_type(self) -> str:
        raise NotImplementedError

    @property
    def surface(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def find_nearest_point_index(self, x, y):
        raise NotImplementedError

    @abstractmethod
    def move_active_point(self, x, y):
        raise NotImplementedError

    @abstractmethod
    def delete_point(self, point_id):
        raise NotImplementedError

    @abstractmethod
    def delete(self):
        raise NotImplementedError

    @abstractmethod
    def embed_to_bbox(self, start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "Figure" = None):
        raise NotImplementedError

    @abstractmethod
    def contains_point(self, point: Point) -> bool:
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> Dict:
        raise NotImplementedError


class ReviewLabel(Figure):
    __tablename__ = 'review_label'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('image.id', ondelete='CASCADE'))
    x = Column(Integer)
    y = Column(Integer)
    label = Column(String) # TODO: Use Label reference instead of str

    image = relationship("LabeledImage", back_populates="review_labels")

    def __init__(self, x, y, label):
        self.x = x
        self.y = y
        self.label = label
        self.point_number = 1
        self.active_point_id = None
        self.selected = False

    @reconstructor
    def init_on_load(self):
        self.active_point_id = None
        self.selected = False
        self.point_number = 1

    @property
    def figure_type(self) -> str:
        return "REVIEW_LABEL"

    @property
    def surface(self) -> int:
        return 1

    @classmethod
    def all(cls) -> List["ReviewLabel"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))

    @classmethod
    def count_with_image(cls) -> int:
        session = get_session()
        return session.query(func.count(cls.id)).filter(cls.item_id.isnot(None)).scalar()

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

    def copy(self) -> "ReviewLabel":
        return ReviewLabel(
            x=self.x,
            y=self.y,
            label=self.label,
        )

    def move_active_point(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def find_nearest_point_index(self, x: int, y: int) -> Optional[int]:
        if Point(self.x, self.y).close_to(x, y, distance=15):
            return 0

    def contains_point(self, point: Point) -> bool:
        return False

    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "ReviewLabel" = None) -> Optional[Figure]:
        x, y = start_point
        figure = ReviewLabel(x=x, y=y, label=label.name)
        return figure

    def draw_figure(
            self,
            canvas: np.ndarray,
            elements_scale_factor: float,
            label: Label,
            show_label_names: bool = True,
            show_object_size: bool = False,
            with_border: bool = True,
            color_fill_opacity: float = 0,
            color: Tuple[int, int, int] = None,
            show_active_point: bool = True
        ) -> np.ndarray:

        circle_radius = max(1, int(3 / ((elements_scale_factor + 1e-7) ** (1/3))))

        if self.selected:
            circle_radius += 3

        if label is None:
            return canvas

        textSize = cv2.getTextSize(label.name, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]

        img_h, img_w, c = canvas.shape
        padding = 10

        rect_x_shift = 40
        rect_y_shift = 40

        rect_x1 = self.x + rect_x_shift
        rect_y2 = self.y - rect_y_shift

        rect_h = textSize[1] + padding * 2
        rect_w = textSize[0] + padding * 2

        rect_x2 = rect_x1 + rect_w
        rect_y1 = rect_y2 - rect_h

        if rect_x1 < 0:
            rect_x1 = max(rect_x1, 0)

        if rect_y1 < 0:
            rect_y1 += rect_y_shift * 2 + rect_h
            rect_y1 = max(rect_y1, 0)

        if rect_x2 > img_w:
            rect_x1 -= rect_x_shift * 2 + rect_w
            rect_x1 = min(rect_x1, img_w - rect_w)

        if rect_y2 > img_h:
            rect_y1 = min(rect_y1, img_h - rect_h)

        rect_x2 = rect_x1 + rect_w
        rect_y2 = rect_y1 + rect_h

        text_x = rect_x1 + padding
        text_y = rect_y2 - padding

        if abs(rect_x1 - self.x) > abs(rect_x2 - self.x):
            line_p2_x = rect_x2
        else:
            line_p2_x = rect_x1
        if abs(rect_y1 - self.y) > abs(rect_y2 - self.y):
            line_p2_y = rect_y2
        else:
            line_p2_y = rect_y1

        cv2.line(canvas, (int(self.x), int(self.y)), (line_p2_x, line_p2_y), (255, 255, 255), 8)
        cv2.circle(canvas, (int(self.x), int(self.y)), circle_radius + 4, (255, 255, 255), 2)
        cv2.rectangle(canvas, (rect_x1-4, rect_y1-4), (rect_x2+4, rect_y2+4), (255, 255, 255), 2)
        cv2.line(canvas, (int(self.x), int(self.y)), (line_p2_x, line_p2_y), (0, 0, 0), 4)
        cv2.circle(canvas, (int(self.x), int(self.y)), circle_radius, label.color_bgr, -1)
        cv2.rectangle(canvas, (rect_x1, rect_y1), (rect_x2, rect_y2), label.color_bgr, -1)
        cv2.circle(canvas, (int(self.x), int(self.y)), circle_radius + 1, (0, 0, 0), 2)
        cv2.rectangle(canvas, (rect_x1-2, rect_y1-2), (rect_x2+2, rect_y2+2), (0, 0, 0), 2)

        if sum(label.color_bgr) / 3 > 120:
            text_color = (0, 0, 0)
        else:
            text_color = (255, 255, 255)

        cv2.putText(canvas, label.name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)

        return canvas

    def serialize(self) -> Dict:
        return {"x": self.x, "y": self.y, "label": self.label}
