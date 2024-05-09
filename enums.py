from enum import Enum
from typing import Dict



class AnnotationStage(Enum):
    ANNOTATE = "ANNOTATE"
    REVIEW = "REVIEW"
    CORRECTION = "CORRECTION"
    DONE = "DONE"
    FILTERING = "FILTERING"


class AnnotationMode(Enum):
    OBJECT_DETECTION = "OBJECT_DETECTION"
    SEGMENTATION = "SEGMENTATION"
    KEYPOINTS = "KEYPOINTS"
    FILTERING = "FILTERING"


class FigureType(Enum):
    BBOX = "BBOX"
    MASK = "MASK"
    KGROUP = "KGROUP"
    REVIEW_LABEL = "REVIEW_LABEL"


