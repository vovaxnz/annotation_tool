import json
from typing import List, Optional

from sqlalchemy import asc, Column, String, Integer

from db import Base, get_session


class Event(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    uid = Column(String, nullable=False, unique=True)
    comment = Column(String, nullable=True)
    custom_fields = Column(String, nullable=True)

    def __init__(self, uid):
        self.uid = uid

    @classmethod
    def get(cls, uid: str) -> Optional["Event"]:
        session = get_session()
        if uid is not None:
            return session.query(cls).filter(cls.uid == uid).first()

    @classmethod
    def all(cls) -> List["Event"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.uid)))

    @classmethod
    def all_selected(cls) -> List["Event"]:
        session = get_session()
        return list(session.query(cls).order_by(asc(cls.uid)))

    @classmethod
    def save_new_in_bulk(cls, events: List["Event"]):
        session = get_session()
        existed_uids = [uid[0] for uid in session.query(cls.uid).all()]
        new_events = [item for item in events if item.uid not in existed_uids]
        session.bulk_save_objects(new_events)
        session.commit()

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()

    @property
    def validation_values(self) -> dict:
        sidebar_values = {}
        if self.custom_fields:
            sidebar_values["answers"] = json.loads(self.custom_fields)
        sidebar_values["comment"] = self.comment if self.comment else ""
        return sidebar_values
