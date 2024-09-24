from annotation_widgets.io import AbstractAnnotationIO
from .image.filtering.io import ImageFilteringIO
from .image.filtering.logic import ImageFilteringLogic
from .image.filtering.widget import ImageFilteringWidget
from .image.labeling.io import ImageLabelingIO
from .image.labeling.logic import ImageLabelingLogic
from .image.labeling.widget import ImageLabelingWidget
from enums import AnnotationMode
from .widget import AbstractAnnotationWidget
from models import ProjectData


import tkinter as tk



def get_io(project_data: ProjectData) -> AbstractAnnotationIO:
    if project_data.mode in [
            AnnotationMode.OBJECT_DETECTION,
            AnnotationMode.SEGMENTATION,
            AnnotationMode.KEYPOINTS
        ]:
        return ImageLabelingIO(project_data)
    elif project_data.mode is AnnotationMode.FILTERING:
        return ImageFilteringIO(project_data)
    else:
        raise ValueError(f"Unknown annotation_mode: {project_data.mode}")


def get_widget(root: tk.Tk, project_data: ProjectData) -> AbstractAnnotationWidget:
    # TODO: Instantiate  io and logic inside the Widget constructor to prevent receiving different project_data by them

    if project_data.mode in [
            AnnotationMode.OBJECT_DETECTION,
            AnnotationMode.SEGMENTATION,
            AnnotationMode.KEYPOINTS
        ]:
        io = ImageLabelingIO(project_data)
        io.initialize_project(root)
        logic = ImageLabelingLogic(
            data_path=io.pm.images_path,
            project_data=project_data
        )
        return ImageLabelingWidget(root, io, logic, project_data)
    elif project_data.mode is AnnotationMode.FILTERING:
        io = ImageFilteringIO(project_data)
        io.initialize_project(root)
        logic = ImageFilteringLogic(
            data_path=io.pm.video_path,
            project_data=project_data
        )
        return ImageFilteringWidget(root, io, logic, project_data)
    else:
        raise ValueError(f"Unknown annotation_mode: {project_data.mode}")


