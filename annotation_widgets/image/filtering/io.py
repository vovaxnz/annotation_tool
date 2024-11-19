from enum import Enum, auto
import json
import os
import shutil
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List

from annotation_widgets.io import AbstractAnnotationIO
from models import ProjectData

from .models import ClassificationImage

from file_processing.file_transfer import FileTransferClient, download_file, upload_file

from utils import  save_json
from .path_manager import FilteringPathManager


class ImageFilteringIO(AbstractAnnotationIO):

    def get_path_manager(self, project_id: int):
        return FilteringPathManager(project_id)

    def download_project(self, root: tk.Tk):
        """Downloads data and annotations from the server. Shows loading window while downloading"""
        if not os.path.isfile(self.pm.video_path):
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.video_path),
                save_path=self.pm.video_path,
            )

    def overwrite_project(self):
        """Filtering mode does not require importing anything due to the nature of the task""" 
        pass

    def download_and_overwrite_annotations(self):
        """Force download and overwrite annotations in the database"""
        messagebox.showinfo("Not implemented", "Unable to overwrite annotations for this type of projects")

    def _export_selected_frames(self, output_path: str):
        result = {"names": list(), "ids": list()}
        for limage in ClassificationImage.all(): 
            if limage.selected:
                if limage.name is not None:
                    result["names"].append(limage.name)
                elif limage.item_id is not None:
                    result["ids"].append(limage.item_id)
        save_json(result, output_path) 

    def _upload_annotation_results(self):
        self._export_selected_frames(output_path=self.pm.selected_frames_json_path)
        upload_file(self.project_data.uid, self.pm.selected_frames_json_path)
