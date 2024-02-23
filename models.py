from abc import ABC
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple
from typing import Dict, List, Tuple

from config import ColorBGR

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

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def close_to(self, x, y, distance=8) -> bool:
        return abs(self.x - x) <= distance and abs(self.y - y) <= distance
    

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
        row = cls.get(name=name)
        if row is not None:
            return row.value
    
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()


class Label(Base):
    __tablename__ = 'label'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    color = Column(String)
    hotkey = Column(String, unique=True)

    def __init__(self, name: str, color: str, hotkey: str):
        self.name = name
        self.color = color
        self.hotkey = hotkey

    @property
    def color_bgr(self) -> Tuple[int, int, int]:
        try:
            color = getattr(ColorBGR, self.color)
        except AttributeError:
            color = ColorBGR.white
        return color
    
    @classmethod
    def get_by_name(cls, name):
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()
    
    @classmethod
    def get_by_hotkey(cls, hotkey):
        session = get_session()
        return session.query(cls).filter(cls.hotkey == hotkey).first()
    
    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    @classmethod
    def all(cls) -> List["Label"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.hotkey)))

    @classmethod
    def first(cls) -> "Label":        
        return cls.all()[0]


class IssueName(Base):
    __tablename__ = 'issue_name'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    color = Column(String)
    hotkey = Column(String, unique=True)

    def __init__(self, name: str, color: str, hotkey: str):
        self.name = name
        self.color = color
        self.hotkey = hotkey

    @property
    def color_bgr(self) -> Tuple[int, int, int]:
        try:
            color = getattr(ColorBGR, self.color)
        except AttributeError:
            color = ColorBGR.white
        return color
    
    @classmethod
    def get_by_name(cls, name):
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()
    
    @classmethod
    def get_by_hotkey(cls, hotkey):
        session = get_session()
        return session.query(cls).filter(cls.hotkey == hotkey).first()
    
    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    @classmethod
    def all(cls) -> List["Label"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.hotkey)))

    @classmethod
    def first(cls) -> "Label":        
        return cls.all()[0]


class ReviewLabel(Base):
    __tablename__ = 'review_label'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
    x = Column(Integer)
    y = Column(Integer)
    text = Column(String)

    image = relationship("LabeledImage", back_populates="review_labels")

    def __init__(self, x, y, text):
        self.x = x
        self.y = y
        self.text = text

    @classmethod
    def all(cls) -> List["ReviewLabel"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))
    
    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    def delete(self):
        session = get_session()
        session.delete(self)
        session.commit()


    def copy(self) -> "ReviewLabel":
        return ReviewLabel(
            x=self.x,
            y=self.y,
            text=self.text,
        )

class BBox(Base):
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
    
    @reconstructor
    def init_on_load(self):
        """BBox has no attribute .active_point_id after being retreived from DB, so we add it here"""
        self.active_point_id = None

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    def delete(self):
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
            if point.close_to(x, y):
                return i

    def contains_point(self, point: Point) -> bool:
        return self.x1 <= point.x <= self.x2 and self.y1 <= point.y <= self.y2

class LabeledImage(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    trash = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)

    bboxes = relationship("BBox", back_populates="image")
    review_labels = relationship("ReviewLabel", back_populates="image")
    # masks = relationship("Mask", back_populates="image") 

    @classmethod
    def get(cls, name):
        session = get_session()
        return session.query(cls).filter(cls.name == name).first()

    @classmethod
    def all(cls) -> List["LabeledImage"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))
    
    def __init__(self, name):
        self.name = name

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
        # for mask in self.masks:
        #     session.delete(mask)
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