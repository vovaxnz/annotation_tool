import json
import tkinter as tk

from jinja2 import Environment, FileSystemLoader

from annotation_widgets.image.widget import AbstractImageAnnotationWidget
from config import templates_path
from gui_utils import show_html_window
from models import ProjectData, Value
from .gui import FilteringStatusBar
from .io import ImageFilteringIO
from .logic import ImageFilteringLogic


class ImageFilteringWidget(AbstractImageAnnotationWidget):
    def __init__(self, root: tk.Tk, io: ImageFilteringIO, logic: ImageFilteringLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

    def set_up_status_bar(self):
        self.status_bar = FilteringStatusBar(parent=self, logic=self.logic)

    def add_menu_items(self, root: tk.Tk):
        assert root.help_menu is not None
        root.help_menu.add_command(label="Classes", command=self.show_classes)
