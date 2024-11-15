from .gui import FilteringStatusBar
from .io import ImageFilteringIO
from .logic import ImageFilteringLogic
from annotation_widgets.image.widget import AbstractImageAnnotationWidget
import tkinter as tk

from models import ProjectData


class ImageFilteringWidget(AbstractImageAnnotationWidget):
    def __init__(self, root: tk.Tk, io: ImageFilteringIO, logic: ImageFilteringLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

    def set_up_status_bar(self):
        self.status_bar = FilteringStatusBar(parent=self, logic=self.logic)
