import tkinter as tk
from abc import abstractmethod
from typing import Callable, Tuple
from tkinter import messagebox

from annotation_widgets.io import AbstractAnnotationIO
from annotation_widgets.logic import AbstractAnnotationLogic
from annotation_widgets.models import CheckResult
from models import ProjectData
from gui_utils import get_loading_window
from models import ProjectData
from utils import check_url_rechable
from config import settings

class AbstractAnnotationWidget(tk.Frame): 
    def __init__(self, root: tk.Tk, io: AbstractAnnotationIO, logic: AbstractAnnotationLogic, project_data: ProjectData):
        super().__init__(root)
        self.parent=root
        self.io: AbstractAnnotationIO = io
        self.logic: AbstractAnnotationLogic = logic
        self.project_data: ProjectData = project_data

        self.close_callback: Callable = None

    @property
    def items_number(self):
        return self.logic.items_number
    
    @property
    def project_id(self):
        return self.logic.project_data.id

    def close(self):
        self.logic.save_item()
        self.destroy()

        if self.close_callback:
            self.close_callback()

    def set_close_callback(self, callback):
        self.close_callback = callback

    def add_menu_items(self, root: tk.Tk):
        """Here you can add additinal menu items specific to the widget"""
        pass

    def schedule_update(self):
        pass

    def go_to_id(self, id: int):
        """Move to i`th element"""
        self.logic.go_to_id(id)
        self.schedule_update()

    def on_overwrite(self):
        """Steps after rewritting annotations, specific for widget"""
        pass
    
    def overwrite_annotations(self):

        if not check_url_rechable(settings.api_url):
            messagebox.showinfo("Error", "Unable to reach a web service")
            return

        agree = messagebox.askokcancel("Overwrite", "Are you sure you want to download annotations and overwrite your annotations with them? All your work will be overwritten")
        if agree:
            root = get_loading_window(text="Downloading and overwriting annotations...", root=self.parent)
            self.io.download_and_overwrite_annotations()
            self.logic.load_item()
            root.destroy()
            self.on_overwrite()
            messagebox.showinfo("Success", "The annotations have been overwritten")

    def remove_project(self):
        self.io.remove_project()

    @abstractmethod
    def check_before_completion(self) -> CheckResult:
        raise NotImplementedError

    def complete_annotation(self, root: tk.Tk):
        self.logic.stop_tracking()
        self.io.complete_annotation(duration_hours=self.logic.duration_hours, root=root)
