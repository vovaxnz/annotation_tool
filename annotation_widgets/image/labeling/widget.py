from annotation_widgets.image.labeling.io import ImageLabelingIO
from annotation_widgets.image.labeling.logic import ImageLabelingLogic
from annotation_widgets.widget import AbstractAnnotationWidget


class ImageLabelingWidget(AbstractAnnotationWidget):
    def __init__(self, io: ImageLabelingIO, logic: ImageLabelingLogic):
        super().__init__(io, logic)

    def initialize(self):
        print("Initializing Image Labeling Widget with Labeling IO and Logic")
