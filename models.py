from sqlalchemy import Boolean, create_engine, Column, Float, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import List, Tuple
from typing import Dict, List, Tuple

Base = declarative_base()


class Rectangle(Base): # TODO: Rename to bbox
    __tablename__ = 'rectangle'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
    h = Column(Float) # TODO: Change fields to xyxy
    w = Column(Float)
    xc = Column(Float)
    yc = Column(Float)

    # TODO: Add a label, selected, color

    image = relationship("Image", back_populates="rectangles")

    def __init__(self, h, w, xc, yc):
        self.h = h
        self.w = w
        self.xc = xc
        self.yc = yc
        self.active_point_id = None
    
    @reconstructor
    def init_on_load(self):
        """Rectangle has no attribute .active_point_id after being retreived from DB, so we add it here"""
        self.active_point_id = None

    def save(self):
        session = Session()
        session.add(self)
        session.commit()

    def delete(self):
        session = Session()
        session.delete(self)
        session.commit()

    def copy(self) -> "Rectangle":
        return Rectangle(
            h=self.h,
            w=self.w,
            xc=self.xc,
            yc=self.yc,
        )

    @property
    def points(self) -> List[Tuple[float, float]]:

        return [
            (self.xc - self.w / 2, self.yc - self.h / 2), 
            (self.xc + self.w / 2, self.yc - self.h / 2), 
            (self.xc + self.w / 2, self.yc + self.h / 2), 
            (self.xc - self.w / 2, self.yc + self.h / 2)
        ]

    def move_active_point(self, x, y):
        """Move the active point of the rectangle."""
        if self.active_point_id is None:
            return
        
        # TODO: Re-calculate rectangle arguments depending on a new point position
        ...



class Image(Base): # TODO: Add relationship with a mask
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    trash = Column(Boolean, default=False)

    rectangles = relationship("Rectangle", back_populates="image")

    @classmethod
    def get(cls, name):
        session = Session()
        return session.query(cls).filter(cls.name == name).first()

    def __init__(self, name):
        self.name = name

    def save(self):
        session = Session()
        session.add(self)
        session.commit()

    def delete(self):
        session = Session()
        for rectangle in self.rectangles:
            session.delete(rectangle)
        session.delete(self)
        session.commit()
        
# Initialize the database engine
database_path = 'sqlite:///db.sqlite' # TODO: Use own database for each annotation project
engine = create_engine(database_path)

# Create all tables in the engine
Base.metadata.create_all(engine)

# Create a session factory
Session = scoped_session(sessionmaker(bind=engine))