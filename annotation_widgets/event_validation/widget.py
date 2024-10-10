import tkinter as tk

from annotation_widgets.widget import AbstractAnnotationWidget
from models import ProjectData
from .gui import EventValidationStatusBar, EventValidationSideBar
from .io import EventValidationIO
from .logic import EventValidationLogic
from ..image.canvas import BaseCanvasView


class EventValidationWidget(AbstractAnnotationWidget):
    def __init__(self, root: tk.Tk, io: EventValidationIO, logic: EventValidationLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

        self.pack(side="top", fill="both", expand=True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=40)

        # Canvas
        self.canvas_view = BaseCanvasView(self, root=self, logic=self.logic)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")

        # Side Bar
        self.set_up_side_bar()
        assert self.side_bar is not None
        self.side_bar.grid(row=0, column=1, sticky="nsew")

        # Status Bar
        self.set_up_status_bar()
        assert self.status_bar is not None
        self.status_bar.grid(row=1, column=0, sticky="nsew")

    def set_up_side_bar(self):
        self.side_bar = EventValidationSideBar(self, logic=self.logic)

    def set_up_status_bar(self):
        self.status_bar = EventValidationStatusBar(self, logic=self.logic)
