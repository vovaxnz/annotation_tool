from geometry import find_intersection, find_line_equation, line_length
from sqlalchemy import Boolean, create_engine, Column, Float, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, declarative_base, reconstructor
from typing import List, Tuple
import math
from typing import Dict, List, Tuple
from config import database_path

Base = declarative_base()


class Rectangle(Base):
    __tablename__ = 'rectangle'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'))
    h = Column(Float)
    w = Column(Float)
    xc = Column(Float)
    yc = Column(Float)
    angle = Column(Float)

    image = relationship("Image", back_populates="rectangles")

    def __init__(self, h, w, xc, yc, angle=0):
        self.h = h
        self.w = w
        self.xc = xc
        self.yc = yc
        self.angle = angle
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

    @property
    def points(self) -> List[Tuple[float, float]]:
        """Returns points in order [[0, 0], [w, 0], [w, h], [0, h]] and rotated around [xc, yc] by angle. 
        Calculate new h, w, xc, yc values based on moved active point. 
        The position of opposite point to the active point remains the same"""

        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        points = [(0, 0), (self.w, 0), (self.w, self.h), (0, self.h)]
        return [
            (
                cos_a * (x - self.w / 2) - sin_a * (y - self.h / 2) + self.xc,
                sin_a * (x - self.w / 2) + cos_a * (y - self.h / 2) + self.yc
            ) for x, y in points
        ]

    def move_active_point(self, x, y):
        """Move the active point of the rectangle."""
        if self.active_point_id is None:
            return
        
        opposite_point_id = (self.active_point_id + 2) % 4
        opp_x, opp_y = self.points[opposite_point_id]

        if self.active_point_id in [0, 2]:
            act_angle, opp_angle = self.angle, self.angle + 90
        else:
            act_angle, opp_angle = self.angle + 90, self.angle
            
        act_m, act_b = find_line_equation(x, y, angle_degrees=act_angle)
        opp_m, opp_b = find_line_equation(opp_x, opp_y, angle_degrees=opp_angle)
        intersection = find_intersection(act_m, act_b, opp_m, opp_b)
        if intersection is None:
            return
        int_x, int_y = intersection
        self.xc = (x + opp_x) / 2
        self.yc = (y + opp_y) / 2

        if self.active_point_id in [0, 2]:
            self.w = line_length(x, y, int_x, int_y) 
            self.h = line_length(opp_x, opp_y, int_x, int_y) 
        else:
            self.h = line_length(x, y, int_x, int_y) 
            self.w = line_length(opp_x, opp_y, int_x, int_y) 


    def rotate_by_active_point(self, x, y):
        """Rotate the rectangle by active point around the center. 
        Calculate new `angle` value based on x, y position. 
        This transformation is not change h, w, xc and yc, it change only `angle`. 
        We imagine the line from the (xc, yc) to (x, y) and the active point 
        should be on this line. The angle on which we need to rotate a rectangle 
        to achieve that is a delta which we need to add to the `angle` value."""
        
        if self.active_point_id is None:
            return

        # Current active point
        active_x, active_y = self.points[self.active_point_id]

        # Angle from center to new position
        angle_to_new = math.degrees(math.atan2(y - self.yc, x - self.xc))
        # Angle from center to current active point
        angle_to_current = math.degrees(math.atan2(active_y - self.yc, active_x - self.xc))

        # Calculate the difference
        angle_delta = angle_to_new - angle_to_current
        self.angle += angle_delta


class Image(Base):
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
engine = create_engine(database_path)

# Create all tables in the engine
Base.metadata.create_all(engine)

# Create a session factory
Session = scoped_session(sessionmaker(bind=engine))