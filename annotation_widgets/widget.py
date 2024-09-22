from annotation_widgets.gui import AbstractAnnotationGUI
from annotation_widgets.image.io import AbstractAnnotationIO
from annotation_widgets.logic import AbstractAnnotationLogic


class AbstractAnnotationWidget:
    def __init__(self, io: AbstractAnnotationIO, logic: AbstractAnnotationLogic, gui: AbstractAnnotationGUI):
        self.io = io
        self.logic = logic
        self.gui = gui
        self.initialize()

    def initialize(self):
        raise NotImplementedError()


    # IO
    def import_project(self):
        self.io.import_project()

    def overwrite_annotations(self):
        self.io.overwrite_annotations()

    def remove_project(self):
        self.io.remove_project()

    def complete_annotation(self):
        self.io.complete_annotation()
