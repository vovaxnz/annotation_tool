from abc import ABC, abstractmethod
import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple
from typing import Dict, List, Tuple

from config import ColorBGR
from drawing import draw_text_label
from enums import FigureType
from masks_encoding import decode_rle, encode_rle

Base = declarative_base()

session_configured = False

class SessionNotConfiguredException(Exception):
    """Custom exception to indicate the session is not configured."""
    pass


def get_session():
    """Session factory to ensure the session is configured before use."""
    if not session_configured:
        raise SessionNotConfiguredException("Session is not configured. Please run configure_database() before performing database operations.")
    return session

class Point:

    def __init__(self, x, y, label: str = None):
        self.x = x
        self.y = y
        self.label = label

    def close_to(self, x, y, distance=8) -> bool:
        return abs(self.x - x) <= distance and abs(self.y - y) <= distance
    
    def serialize(self) -> Dict:
        return {"x": self.x, "y": self.y, "label": self.label}
    

class Value(Base):
    __tablename__ = 'value'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)

    @classmethod
    def get(cls, name) -> Optional["Value"]:
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()
        
    @classmethod
    def update_value(cls, name, value, overwrite=True):
        row = cls.get(name=name)
        if row is None:
            row = Value(name=name, value=str(value))
            row.save()
        else:
            if overwrite:
                row.value = str(value)
                row.save()
    
    @classmethod
    def get_value(cls, name) -> Optional[str]:
        print("get value", name)
        row = cls.get(name=name)
        if row is not None:
            return row.value
    
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def save(self):
        print("save value", self.name)
        session = get_session()
        session.add(self)
        session.commit()


class Label(Base):
    __tablename__ = 'label'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    color = Column(String)
    hotkey = Column(String)
    type = Column(String) # FigureType
    attributes = Column(String, nullable=True) 


    def __init__(self, name: str, color: str, hotkey: str, type: str, attributes: str = None):
        """
        Args:
            attributes (str): Any attributes in json format
        """
        self.name = name
        self.color = color
        self.hotkey = hotkey
        self.type = type
        self.attributes = attributes

    @property
    def color_bgr(self) -> Tuple[int, int, int]:
        return getattr(ColorBGR, self.color, ColorBGR.white)
    
    @classmethod
    def get(cls, name: str, figure_type: str):
        print("get label")
        session = get_session()
        return session.query(cls).filter(cls.name == name, cls.type == figure_type).first()
    
    def save(self):
        print("save label")
        session = get_session()
        session.add(self)
        session.commit()

    @classmethod
    def get_review_labels(cls) -> List["Label"]:
        session = get_session()
        return session.query(cls).filter(cls.type == FigureType.REVIEW_LABEL.name).order_by(asc(cls.hotkey))
    
    @classmethod
    def get_figure_labels(cls) -> List["Label"]:
        session = get_session()
        return session.query(cls).filter(cls.type != FigureType.REVIEW_LABEL.name).order_by(asc(cls.hotkey))

    @classmethod
    def all(cls) -> List["Label"]:
        session = get_session()
        return session.query(cls).order_by(asc(cls.hotkey))
    

class Figure(ABC):

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
            label: Label, 
            show_label_names: bool = False,
        ) -> np.ndarray:
        raise NotImplementedError

    @property
    @abstractmethod
    def figure_type(self) -> str:
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
    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "Figure" = None):
        raise NotImplementedError

    @abstractmethod
    def contains_point(point: Point) -> bool:
        raise NotImplementedError


class ReviewLabel(Base): # TODO: Find how to inherit this class from the Figure
    __tablename__ = 'review_label'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
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
    
    @classmethod
    def all(cls) -> List["ReviewLabel"]:
        print("get review label")   
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))
    
    @property
    def state(self):
        return inspect(self)
    
    def save(self):
        print("save review label")   
        session = get_session()
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        self.point_number = 0
        
    def delete(self):
        print("delete review label")   
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
        if Point(self.x, self.y).close_to(x, y, distance=30):
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


class KeypointGroup(Base): # TODO: Find how to inherit this class from the Figure
    __tablename__ = 'keypoint_group'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
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
            if point.close_to(x, y, distance=10):
                return i

    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "KeypointGroup" = None) -> Optional[Figure]:
        x, y = end_point
        if abs(start_point[0] - x) > min_movement_to_create and abs(start_point[1] - y) > min_movement_to_create:
            x1 = min(start_point[0], x)
            y1 = min(start_point[1], y)
            x2 = max(start_point[0], x)
            y2 = max(start_point[1], y)

            w = x2 - x1
            h = y2 - y1

            assert label.attributes is not None
            keypoint_info = json.loads(label.attributes)["keypoint_info"]
            
            result_keypoints = list()
            for kp_label in keypoint_info:
                kp_x = keypoint_info[kp_label]["x"] * w + x1
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
            
            circle_radius = max(1, int(5 / ((elements_scale_factor + 1e-7) ** (1/3))))
            
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


class BBox(Base): # TODO: Find how to inherit this class from the Figure
    __tablename__ = 'bbox'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
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
    def state(self):
        return inspect(self)

    def save(self):
        print("save bbox") 
        session = get_session()
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        self.point_number = 0

    def delete(self):
        print("delete bbox") 
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
            if point.close_to(x, y, distance=10):
                return i

    def contains_point(self, point: Point) -> bool:
        return self.x1 <= point.x <= self.x2 and self.y1 <= point.y <= self.y2

    def draw_figure(
            self,
            canvas: np.ndarray, 
            elements_scale_factor: float, 
            label: Label, 
            show_label_names: bool = False,
        ) -> np.ndarray:

        line_width = max(1, int(5 / ((elements_scale_factor + 1e-7) ** (1/3))))

        if self.selected:
            if elements_scale_factor < 3:
                line_width += 2
            else:
                line_width += 1

        for layer_id in range(line_width):
            canvas = cv2.rectangle(canvas, (int(self.x1 - layer_id), int(self.y1 - layer_id)), (int(self.x2 + layer_id), int(self.y2 + layer_id)), label.color_bgr, 1)

        if show_label_names:
            x, y = self.x1, self.y1
            under_point = True
            if y - 20 < 0:
                y = self.y2
                under_point = False
            draw_text_label(
                canvas, 
                text=label.name, 
                x=x, 
                y=y, 
                color_bgr=label.color_bgr, 
                padding=5, 
                under_point=under_point
            )

        if self.active_point_id is not None:
            point = self.points[self.active_point_id]
            circle_radius = max(1, int(7 / ((elements_scale_factor + 1e-7) ** (1/3))))
            cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (255, 255, 255), -1)
            cv2.circle(canvas, (int(point.x), int(point.y)), circle_radius, (0, 0, 0), 2)

        return canvas

    def embed_to_bbox(start_point: Tuple[int, int], end_point: Tuple[int, int], label: Label, min_movement_to_create: int = 5, figure: "BBox" = None) -> Optional[Figure]:
        x, y = end_point
        if abs(start_point[0] - x) > min_movement_to_create and abs(start_point[1] - y) > min_movement_to_create:
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


class Mask(Base):
    __tablename__ = 'mask'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
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
        self.decode_rle()
    
    @reconstructor
    def init_on_load(self):
        self.decode_rle()
        self.selected = False

    @property
    def figure_type(self) -> str:
        return "MASK"
    
    def decode_rle(self):
        self.mask = decode_rle(self.rle, height=self.height, width=self.width)

    def encode_mask(self):
        self.rle = encode_rle(self.mask)

    @property
    def state(self):
        return inspect(self)

    def save(self):
        print("save mask") 
        session = get_session()
        session.add(self)
        session.commit()

    def delete_point(self, point_id):
        pass

    def delete(self):
        print("delete mask") 
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

    def draw_figure(
            self,
            canvas: np.ndarray, 
            elements_scale_factor: float, 
            label: Label, 
            show_label_names: bool = False,
        ) -> np.ndarray:   
        b2, g2, r2 = label.color_bgr
        canvas_copy = np.copy(canvas)
        canvas_copy[:, :, :3][self.mask > 0] = [b2, g2, r2]
        canvas = cv2.addWeighted(canvas_copy, 0.4, canvas, 0.6, 0)
        return canvas


class LabeledImage(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    height = Column(Integer)
    width = Column(Integer)
    trash = Column(Boolean, default=False)

    bboxes = relationship("BBox", back_populates="image")
    kgroups = relationship("KeypointGroup", back_populates="image")
    review_labels = relationship("ReviewLabel", back_populates="image")
    masks = relationship("Mask", back_populates="image") 

    @classmethod
    def get(cls, name):
        print("get image") 
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()

    @classmethod
    def all(cls) -> List["LabeledImage"]:
        print("get all images") 
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))
    
    def __init__(self, name, height, width):
        self.name = name
        self.height = height
        self.width = width

    def save(self):
        print("save image") 
        session = get_session()
        session.add(self)
        session.commit()
    
    @classmethod
    def save_batch(cls, limages: List["LabeledImage"]):
        print("get image batch") 
        session = get_session()
        for limage in limages:
            session.add(limage)
        session.commit()

    def delete(self):
        print("delete image") 
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


def configure_database(database_path):
    global session
    global session_configured
    engine = create_engine(database_path)
    Base.metadata.create_all(engine)  # Make sure all tables are created
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    session_configured = True


FigureTypes: Dict[FigureType, Figure] = {
    FigureType.KGROUP: KeypointGroup,
    FigureType.BBOX: BBox,
    FigureType.REVIEW_LABEL: ReviewLabel,
    FigureType.MASK: Mask
}
