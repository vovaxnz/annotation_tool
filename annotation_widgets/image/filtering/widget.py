from annotation_widgets.image.filtering.gui import FilteringStatusBar
from annotation_widgets.image.filtering.io import ImageFilteringIO
from annotation_widgets.image.filtering.logic import ImageFilteringLogic
from annotation_widgets.image.widget import ImageAnnotationWidget
import tkinter as tk


class ImageFilteringWidget(ImageAnnotationWidget):
    def __init__(self, root: tk.Tk, io: ImageFilteringIO, logic: ImageFilteringLogic):
        super().__init__(root, io, logic)

    def set_up_status_bar(self):
        self.status_bar = FilteringStatusBar(parent=self.container, logic=self.logic)

    def initialize(self):
        print("Initializing Image Filtering Widget with Filtering IO and Logic")
