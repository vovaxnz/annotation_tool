from enum import Enum


class AnnotationStage(Enum):
    ANNOTATE = "ANNOTATE"
    REVIEW = "REVIEW"
    CORRECTION = "CORRECTION"
    DONE = "DONE"
    FILTERING = "FILTERING"
    EVENT_VALIDATION = "EVENT_VALIDATION"


class AnnotationMode(Enum):
    OBJECT_DETECTION = "OBJECT_DETECTION"
    SEGMENTATION = "SEGMENTATION"
    KEYPOINTS = "KEYPOINTS"
    FILTERING = "FILTERING"
    EVENT_VALIDATION = "EVENT_VALIDATION"


class FigureType(Enum):
    BBOX = "BBOX"
    MASK = "MASK"
    KGROUP = "KGROUP"
    REVIEW_LABEL = "REVIEW_LABEL"


class EventValidationAnswerOptions(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNRECOGNIZED = "UNRECOGNIZED"

    @classmethod
    def values(cls):
        return [i.value for i in cls]


class EventViewMode(Enum):
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
