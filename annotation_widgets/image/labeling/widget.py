from annotation_widgets.image.labeling.gui import AnnotationStatusBar
from annotation_widgets.image.labeling.io import ImageLabelingIO
from annotation_widgets.image.labeling.logic import ImageLabelingLogic
from annotation_widgets.image.labeling.models import Label
from annotation_widgets.image.widget import ImageAnnotationWidget
from jinja2 import Environment, FileSystemLoader
from config import templates_path
import tkinter as tk

from gui_utils import show_html_window
from models import ProjectData


class ImageLabelingWidget(ImageAnnotationWidget):
    def __init__(self, root: tk.Tk, io: ImageLabelingIO, logic: ImageLabelingLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

    def set_up_status_bar(self):
        self.status_bar = AnnotationStatusBar(parent=self.container, logic=self.logic)

    def show_classes(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_figure_labels()
        ]
        
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        show_html_window(root=self, title="Classes", html_content=html_content)

    def show_review_labels(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_review_labels()
        ]
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        show_html_window(root=self, title="Classes", html_content=html_content)

    def add_menu_items(self, root: tk.Tk):
        assert root.help_menu is not None
        assert root.file_menu is not None
        root.file_menu.add_command(label="Download and overwrite annotations", command=self.overwrite_annotations)
        root.help_menu.add_command(label="Classes", command=self.show_classes)
        root.help_menu.add_command(label="Review Labels", command=self.show_review_labels)

    def initialize(self):
        print("Initializing Image Labeling Widget with Labeling IO and Logic")
