from typing import Optional
from config import AnnotationMode, AnnotationStage
from labeling_app.bbox import BboxLabelingApp
from labeling_app.keypoints import KeypointLabelingApp
from labeling_app.labeling import LabelingApp
from labeling_app.review import ReviewLabelingApp


def get_labeling_app(img_dir: str, annotation_mode: AnnotationMode, annotation_stage: AnnotationStage, project_id: int) -> Optional[LabelingApp]:

    if annotation_stage is AnnotationStage.CORRECTION:
        review_labeling_app = ReviewLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            project_id=project_id
        )
    else:
        review_labeling_app = None


    if annotation_mode is AnnotationMode.OBJECT_DETECTION:
        labeling_app = BboxLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            secondary_visualizer=review_labeling_app,
            project_id=project_id
        )
    elif annotation_mode is AnnotationMode.KEYPOINTS:
        labeling_app = KeypointLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            secondary_visualizer=review_labeling_app,
            project_id=project_id
        )
    else:
        raise RuntimeError(f"Annotation mode {annotation_mode.name} is not supported")

    if annotation_stage is AnnotationStage.REVIEW:
        labeling_app.show_label_names = True
        labeling_app = ReviewLabelingApp(
            img_dir=img_dir,
            annotation_stage=annotation_stage,
            annotation_mode=annotation_mode,
            secondary_visualizer=labeling_app,
            project_id=project_id
        )

    return labeling_app