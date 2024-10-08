from dataclasses import dataclass
from db import Base, get_session

import json
import cv2
import numpy as np
from enums import AnnotationMode, AnnotationStage
from sqlalchemy import Boolean, asc, create_engine, Column, Float, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import Any, List, Optional, Tuple, Dict
from config import settings


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


@dataclass
class ProjectData:
    id: int
    uid: str
    stage: AnnotationStage
    mode: AnnotationMode

    def to_json(self):
        data_dict = {
            'id': self.id,
            'uid': self.uid,
            'stage': self.stage.name,
            'mode': self.mode.name
        }
        return data_dict