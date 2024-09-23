from .bboxes.models import BBox
from .keypoints.models import KeypointGroup
from .models import Figure, ReviewLabel
from .segmentation.models import Mask
from enums import FigureType


from typing import Dict


FigureTypes: Dict[FigureType, Figure] = {
    FigureType.KGROUP: KeypointGroup,
    FigureType.BBOX: BBox,
    FigureType.REVIEW_LABEL: ReviewLabel,
    FigureType.MASK: Mask
}