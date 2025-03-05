import json
import os
import tkinter as tk
from tkinter import messagebox

from annotation_widgets.image.io import ImageIO
from file_processing.file_transfer import FileTransferClient, upload_file
from utils import check_correct_json, save_json, open_json
from .models import ClassificationImage
from .path_manager import FilteringPathManager
from annotation_widgets.image.models import Label


class ImageFilteringIO(ImageIO):

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
        if not os.path.isfile(self.pm.meta_ann_path) or not check_correct_json(self.pm.meta_ann_path):
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.meta_ann_path),
                save_path=self.pm.meta_ann_path,
            )

    def overwrite_project(self):
        """
            meta ann format:
        {
            "labels": [
                {"name": "truck", "color": "yellow", "hotkey": "1", "type": "BBOX", "attributes": "..."},
            ],
        }
        """
        assert os.path.isfile(self.pm.meta_ann_path), "File 'meta.json' does not exist"
        meta_data = open_json(self.pm.meta_ann_path)

        # Labels
        self.overwrite_labels(labels_data=meta_data["labels"])

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
