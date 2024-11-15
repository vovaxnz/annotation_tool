from annotation_widgets.image.labeling.bboxes.figure_controller import BBoxFigureController
from annotation_widgets.image.labeling.figure_controller import ObjectFigureController
from annotation_widgets.image.labeling.keypoints.figure_controller import KGroupFigureController
from annotation_widgets.image.labeling.segmentation.figure_controller import MaskFigureController
from enums import AnnotationMode


ControllerByMode = {
    AnnotationMode.OBJECT_DETECTION: BBoxFigureController,
    AnnotationMode.KEYPOINTS: KGroupFigureController,
    AnnotationMode.SEGMENTATION: MaskFigureController
}