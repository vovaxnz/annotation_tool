from annotation_widgets.image.filtering.io import ImageFilteringIO
from annotation_widgets.image.filtering.logic import ImageFilteringLogic
from annotation_widgets.widget import AbstractAnnotationWidget


class ImageFilteringWidget(AbstractAnnotationWidget):
    def __init__(self, io: ImageFilteringIO, logic: ImageFilteringLogic):
        super().__init__(io, logic)

    def initialize(self):
        print("Initializing Image Filtering Widget with Filtering IO and Logic")
