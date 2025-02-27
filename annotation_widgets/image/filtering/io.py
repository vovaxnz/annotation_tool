import json
import os
import tkinter as tk
from tkinter import messagebox

from annotation_widgets.io import AbstractAnnotationIO
from file_processing.file_transfer import FileTransferClient, upload_file
from utils import save_json, open_json
from .models import ClassificationImage
from .path_manager import FilteringPathManager
from ..labeling.models import Label


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
        for label_dict in meta_data["labels"]:
            label = Label.get(name=label_dict["name"], figure_type=label_dict["type"])

            attributes = label_dict.get("attributes")
            if attributes is not None:
                attributes = json.dumps(attributes)

            if label is None:
                label = Label(
                    name=label_dict["name"],
                    color=label_dict["color"],
                    hotkey=label_dict["hotkey"],
                    type=label_dict["type"],
                    attributes=attributes
                )
            else:
                label.color = label_dict["color"]
                label.hotkey = label_dict["hotkey"]
                label.attributes = attributes
            label.save()

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
