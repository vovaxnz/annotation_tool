from abc import ABC
import os
import shutil
from tkinter import messagebox
import tkinter as tk

from api_requests import complete_task
from db import configure_database
from enums import AnnotationStage
from file_processing.file_transfer import upload_file
from gui_utils import get_loading_window
from models import ProjectData, Value
from path_manager import BasePathManager
from utils import save_json


class AbstractAnnotationIO(ABC):
    
    def __init__(self, project_data: ProjectData):
        self.project_data: ProjectData = project_data
        self.pm: BasePathManager = self.get_path_manager(project_data.id)

    @property
    def stage(self) -> AnnotationStage:
        stage_name = Value.get_value(name="annotation_stage")
        if stage_name is not None:
            getattr(AnnotationStage, stage_name)
        else:
            return AnnotationStage.UNKNOWN
    
    def update_stage(self, stage: AnnotationStage):
        Value.update_value("annotation_stage", stage.name, overwrite=True)
    
    def change_stage_at_completion(self):
        self.update_stage(AnnotationStage.DONE)

    @property
    def should_be_overwritten(self) -> bool:
        return self.stage is AnnotationStage.UNKNOWN

    def initialize_project(self, root: tk.Tk):
        save_json(self.project_data.to_json(), self.pm.state_path)
        configure_database(self.pm.db_path)
        self.download_project(root=root)
        if self.should_be_overwritten:
            loading_window = get_loading_window(text="Overwritting project...", root=root)
            self.overwrite_project()
            self.reset_counters()
            loading_window.destroy()
        self.update_stage(self.project_data.stage)
        assert not self.should_be_overwritten, f"Current stage is {self.stage}, new stage is {self.project_data.stage}"
     
    def reset_counters(self):
        Value.update_value("item_id", 0)
        Value.update_value("duration_hours", 0)
        Value.update_value("processed_item_ids", [])

    def get_path_manager(self, project_id: int): 
        """Returns BasePathManager class"""
        raise NotImplementedError()

    def download_project(self, root: tk.Tk):
        """Downloads data and annotations from the server. 
        Shows loading window while downloading"""
        raise NotImplementedError()

    def overwrite_project(self):
        """Overwrites data in database with data from project json files"""
        raise NotImplementedError()
    
    def download_and_overwrite_annotations(self):
        """Force download and overwrite annotations in the database"""
        raise NotImplementedError()

    def _upload_annotation_results(self):
        """Uploads annotation results to the server"""
        raise NotImplementedError()

    def _remove_after_completion(self):
        """Override this method to change how project files 
        should be removed after project completion"""
        self.remove_project()

    def complete_annotation(self, duration_hours: float, root: tk.Tk):
        loading_window = get_loading_window(text="Finishing project...", root=root)
        if os.path.isfile(self.pm.statistics_path):
            upload_file(self.project_data.uid, self.pm.statistics_path)
        self._upload_annotation_results()
        complete_task(project_uid=self.project_data.uid, duration_hours=duration_hours)
        self.reset_counters()
        self.change_stage_at_completion()
        self._remove_after_completion()
        messagebox.showinfo("Success", "Project completed")
        loading_window.destroy()

    def remove_project(self):
        if os.path.isdir(self.pm.project_path):
            shutil.rmtree(self.pm.project_path)
        if os.path.isfile(self.pm.db_local_path):
            os.remove(self.pm.db_local_path)
