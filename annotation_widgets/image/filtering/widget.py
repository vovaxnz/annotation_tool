from .gui import FilteringStatusBar
from .io import ImageFilteringIO
from .logic import ImageFilteringLogic
from annotation_widgets.image.widget import ImageAnnotationWidget
import tkinter as tk

from models import ProjectData


class ImageFilteringWidget(ImageAnnotationWidget):
    def __init__(self, root: tk.Tk, io: ImageFilteringIO, logic: ImageFilteringLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

    def set_up_status_bar(self):
        self.status_bar = FilteringStatusBar(parent=self.container, logic=self.logic)

    def initialize(self):
        print("Initializing Image Filtering Widget with Filtering IO and Logic")
