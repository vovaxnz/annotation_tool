from db import Base, get_session

import json
import cv2
import numpy as np
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings

from typing import List


class ClassificationImage(Base):
    __tablename__ = 'classification_image'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=True)
    item_id = Column(Integer, nullable=True)
    selected = Column(Boolean, default=False)

    @classmethod
    def get(cls, name: str = None, item_id: int = None):
        session = get_session()
        if name is not None:
            return session.query(cls).filter(cls.name == name).first()
        elif item_id is not None:
            return session.query(cls).filter(cls.item_id == item_id).first()

    @classmethod
    def all(cls) -> List["ClassificationImage"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.name)))

    @classmethod
    def all_selected(cls) -> List["ClassificationImage"]:
        session = get_session()
        return list(session.query(cls).filter(cls.selected == True).order_by(asc(cls.item_id)))

    def __init__(self, name, item_id, selected: bool = False):
        self.name = name
        self.item_id = item_id
        self.selected = selected

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()