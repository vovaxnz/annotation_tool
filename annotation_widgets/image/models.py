from typing import List, Tuple

from sqlalchemy import asc, Column, String, Integer

from config import ColorBGR
from db import Base, get_session
from enums import FigureType


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
        return getattr(ColorBGR, self.color, ColorBGR.gray)

    @property
    def is_blur(self):
        return self.name == "blur"

    @classmethod
    def get(cls, name: str, figure_type: str):
        session = get_session()
        return session.query(cls).filter(cls.name == name, cls.type == figure_type).first()

    def save(self):
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
