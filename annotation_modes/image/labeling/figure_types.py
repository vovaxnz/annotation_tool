from annotation_modes.image.labeling.bboxes.models import BBox
from annotation_modes.image.labeling.keypoints.models import KeypointGroup
from annotation_modes.image.labeling.models import Figure, ReviewLabel
from annotation_modes.image.labeling.segmentation.models import Mask
from enums import FigureType


from typing import Dict


FigureTypes: Dict[FigureType, Figure] = {
    FigureType.KGROUP: KeypointGroup,
    FigureType.BBOX: BBox,
    FigureType.REVIEW_LABEL: ReviewLabel,
    FigureType.MASK: Mask
}