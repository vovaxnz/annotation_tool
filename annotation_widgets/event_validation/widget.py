

from .logic import EventValidationLogic
from .io import EventValidationIO
from annotation_widgets.widget import AbstractAnnotationWidget
import tkinter as tk

from models import ProjectData


class EventValidationWidget(AbstractAnnotationWidget):
    def __init__(self, root: tk.Tk, io: EventValidationIO, logic: EventValidationLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)
        ...
