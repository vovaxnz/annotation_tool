from annotation_widgets.image.filtering.io import ImageFilteringIO
from annotation_widgets.image.filtering.logic import ImageFilteringLogic
from annotation_widgets.image.filtering.widget import ImageFilteringWidget
from annotation_widgets.image.io import AbstractAnnotationIO
from annotation_widgets.image.labeling.io import ImageLabelingIO
from annotation_widgets.image.labeling.logic import ImageLabelingLogic
from annotation_widgets.image.labeling.widget import ImageLabelingWidget
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from db import configure_database
from enums import AnnotationMode
from annotation_widgets.widget import AbstractAnnotationWidget
from gui_utils import get_loading_window
from models import ProjectData
from path_manager import PathManager
from utils import save_json


import tkinter as tk

from enum import Enum, auto


def get_io(annotation_mode: AnnotationMode) -> AbstractAnnotationIO:
    if annotation_mode in [
            AnnotationMode.OBJECT_DETECTION,
            AnnotationMode.SEGMENTATION,
            AnnotationMode.KEYPOINTS
        ]:
        return ImageLabelingIO()
    elif annotation_mode is AnnotationMode.FILTERING:
        return ImageFilteringIO()
    else:
        raise ValueError(f"Unknown annotation_mode: {annotation_mode}")


def get_widget(root: tk.Tk, project_data: ProjectData) -> AbstractAnnotationWidget:
    if project_data.mode is AnnotationMode.OBJECT_DETECTION:
        io = ImageLabelingIO()
        logic = ImageLabelingLogic()
        return ImageLabelingWidget(root, io, logic, project_data)
    elif project_data.mode is AnnotationMode.FILTERING:
        io = ImageFilteringIO()
        logic = ImageFilteringLogic()
        return ImageFilteringWidget(root, io, logic, project_data)
    else:
        raise ValueError(f"Unknown annotation_mode: {project_data.mode}")


def load_project(project_data: ProjectData, root: tk.Tk) -> AbstractImageAnnotationLogic:
    # TODO: Incapsulate to Annoation Widgets and move to main.py to appropriate method
    # widget.download_project()
    # widget.import_project()

    pm = PathManager(project_data.id)
    io = get_io(project_data.mode)

    save_json(project_data.to_json(), pm.state_path)

    io.download_project(project_data=project_data, root=root)

    loading_window = get_loading_window(text="Loading project...", root=root)

    configure_database(pm.db_path)
    if project_data.mode is AnnotationMode.FILTERING:
        annotation_logic = ImageFilteringLogic(
            data_path=pm.video_path,
            project_data=project_data,
        )
    else:
        io.import_project(
            figures_ann_path=pm.figures_ann_path,
            review_ann_path=pm.review_ann_path,
            meta_ann_path=pm.meta_ann_path,
            img_dir=pm.images_path,
            overwrite=False,
        )
        annotation_logic = ImageLabelingLogic(
            data_path=pm.images_path,
            project_data=project_data,
        )
    loading_window.destroy()
    return annotation_logic