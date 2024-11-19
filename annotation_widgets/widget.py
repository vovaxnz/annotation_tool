from typing import Callable
from .io import AbstractAnnotationIO
from .logic import AbstractAnnotationLogic
import tkinter as tk

from models import ProjectData
 
 
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
        self.logic.save_state() 
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

    def overwrite_annotations(self):
        self.io.download_and_overwrite_annotations()

    def remove_project(self):
        self.io.remove_project()

    def complete_annotation(self, root: tk.Tk): 
        self.logic.save_item()
        self.logic.save_state()
        self.io.complete_annotation(duration_hours=self.logic.duration_hours, root=root)
