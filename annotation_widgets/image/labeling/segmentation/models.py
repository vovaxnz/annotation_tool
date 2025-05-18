from annotation_widgets.image.labeling.models import Figure, Point
from annotation_widgets.image.labeling.segmentation.masks_encoding import decode_rle, encode_rle
from annotation_widgets.image.models import Label
from db import Base, get_session

import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings


class Mask(Base):
    __tablename__ = 'mask'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('image.id'))
    rle = Column(Integer)
    label = Column(String)
    height = Column(Integer)
    width = Column(Integer)


    image = relationship("LabeledImage", back_populates="masks")

    def __init__(self, label: str, rle: str, height: int, width: int):
        self.rle = rle
        self.label = label
        self.height = height
        self.width = width
        self.selected: bool = False
        self.decode_rle()

    @reconstructor
    def init_on_load(self):
        self.decode_rle()
        self.selected = False

    @property
    def figure_type(self) -> str:
        return "MASK"

    @property
    def surface(self) -> int:
        return 1

    def decode_rle(self):
        self.mask = decode_rle(self.rle, height=self.height, width=self.width)

    def encode_mask(self):
        self.rle = encode_rle(self.mask)

    @property
    def state(self):
        return inspect(self)

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        pass

    def delete(self):
        if not self.state.persistent:
            return
        session = get_session()
        session.delete(self)
        session.commit()

    def copy(self) -> "Mask":
        return Mask(
            label=self.label,
            rle=self.rle,
            height=self.height,
            width=self.width
        )

    def find_nearest_point_index(self, x: int, y: int) -> Optional[int]:
        raise NotImplementedError

    def move_active_point(self, x, y):
        raise NotImplementedError

    def embed_to_bbox(self, start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "Figure" = None):
        raise NotImplementedError

    def contains_point(self, point: Point) -> bool:
        raise NotImplementedError

    def draw_figure(
            self,
            canvas: np.ndarray,
            elements_scale_factor: float,
            label: Label,
            show_label_names: bool = False,
            show_object_size: bool = False,
            with_border: bool = True,
            color_fill_opacity: float = 0.5,
            color: Tuple[int, int, int] = None,
            show_active_point: bool = True
        ) -> np.ndarray:

        opacity = 0.5

        b2, g2, r2 = label.color_bgr

        if opacity > 0:
            canvas_with_mask = np.copy(canvas)
        else:
            canvas_with_mask = canvas

        canvas_with_mask[:, :, :3][self.mask > 0] = [b2, g2, r2]

        if opacity > 0:
            canvas = cv2.addWeighted(canvas_with_mask, opacity, canvas, max(1 - opacity, 0), 0)
            
        return canvas

    def serialize(self) -> Dict:
        return {"label": self.label, "rle": self.rle, "height": self.height, "width": self.width}