from annotation_widgets.image.filtering.io import ImageFilteringIO
from annotation_widgets.image.filtering.logic import ImageFilteringLogic
from annotation_widgets.image.filtering.widget import ImageFilteringWidget
from annotation_widgets.image.labeling.io import ImageLabelingIO
from annotation_widgets.image.labeling.logic import ImageLabelingLogic
from annotation_widgets.image.labeling.widget import ImageLabelingWidget
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from db import configure_database
from enums import AnnotationMode
from gui import AbstractAnnotationWidget
from gui_utils import get_loading_window
from models import ProjectData
from path_manager import PathManager
from utils import save_json


import tkinter as tk

from enum import Enum, auto


class AnnotationWidgetType(Enum):
    BBOX = auto()
    SEGMENTATION = auto()
    KEYPOINTS = auto()
    FILTERING = auto()
    EVENT_VALIDATION = auto()


class AnnotationWidgetFactory:
    def get_widget(self, widget_type: AnnotationWidgetType) -> AbstractAnnotationWidget:
        if widget_type is AnnotationWidgetType.BBOX:
            io = ImageLabelingIO()
            logic = ImageLabelingLogic()
            return ImageLabelingWidget(io, logic)
        elif widget_type is AnnotationWidgetType.FILTERING:
            io = ImageFilteringIO()
            logic = ImageFilteringLogic()
            return ImageFilteringWidget(io, logic)
        else:
            raise ValueError(f"Unknown widget type: {widget_type}")


def get_widget(project_data: ProjectData, root: tk.Tk) -> AbstractImageAnnotationLogic:
    # TODO: Make it return a Widget and Use AnnotationWidgetFactory.get_widget()

    pm = PathManager(project_data.id)

    save_json(project_data.to_json(), pm.state_path)

    download_project(project_data=project_data, root=root)

    loading_window = get_loading_window(text="Loading project...", root=root)

    configure_database(pm.db_path)
    if project_data.mode is AnnotationMode.FILTERING:
        annotation_logic = ImageFilteringLogic(
            data_path=pm.video_path,
            project_data=project_data,
        )
    else:
        import_project(
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