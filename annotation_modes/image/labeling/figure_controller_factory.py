from annotation_modes.image.labeling.bboxes.figure_controller import BBoxFigureController
from annotation_modes.image.labeling.figure_controller import ObjectFigureController
from annotation_modes.image.labeling.keypoints.figure_controller import KGroupFigureController
from annotation_modes.image.labeling.segmentation.figure_controller import MaskFigureController
from enums import AnnotationMode


ControllerByMode = { # TODO: Use Factory
    AnnotationMode.OBJECT_DETECTION: BBoxFigureController,
    AnnotationMode.KEYPOINTS: KGroupFigureController,
    AnnotationMode.SEGMENTATION: MaskFigureController
}