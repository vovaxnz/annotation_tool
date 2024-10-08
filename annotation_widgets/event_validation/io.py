import json
import os
import tkinter as tk
from tkinter import messagebox

from annotation_widgets.event_validation.models import Event
from annotation_widgets.io import AbstractAnnotationIO
from file_processing.file_transfer import FileTransferClient, upload_file
from file_processing.unzipping import ArchiveUnzipper
from models import Value
from utils import save_json, open_json


class EventValidationIO(AbstractAnnotationIO):

    def download_project(self, root: tk.Tk):
        """Downloads data and annotations from the server. Shows loading window while downloading"""
        if not os.path.isfile(self.pm.archive_path):
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.archive_path),
                save_path=self.pm.archive_path,
            )
        self.unzip_project_archive(root=root)

    def unzip_project_archive(self, root: tk.Tk):
        au = ArchiveUnzipper(window_title="Unzip progress", root=root)
        au.unzip(self.pm.archive_path, self.pm.project_path)
        if os.path.isfile(self.pm.archive_path):
            os.remove(self.pm.archive_path)

    def import_project(self, overwrite: bool = False):
        fields = open_json(self.pm.meta_ann_path)
        Value.update_value("fields", json.dumps(fields), overwrite=False)

        events = []
        for idx, item in enumerate(sorted(os.listdir(self.pm.images_folder_path))):
            event_uid = item.split("_")[1].split(".")[0]
            events.append(Event(item_id=idx, uid=event_uid))

        Event.save_new_in_bulk(events)


    def overwrite_annotations(self):
        """Force download and overwrite annotations in the database"""
        messagebox.showinfo("Not implemented", "Unable to overwrite annotations for this type of projects")

    def _export_event_validation_results(self, output_path: str):
        """
        JSON Output format:
        {
            "fields": [
                "Has person on truck FP more than 4 frames in a row? (TRUE/FALSE)",
                "Has person on truck  FN more than 4 frames in a row? (TRUE/FALSE)",
                "Status (TP/FP)"
            ],
            "events" {
                "76a4365d-25cb-4403-a76e-cfe70016a8e7": ["True", None, "TP"],
                ...
            }
        }
        """
        result = {"fields": Value.get_value("fields"), "events": {}}

        for event in Event.all():
            result["events"][event.uid] = event.custom_fields

        save_json(result, output_path)

    def _upload_annotation_results(self):
        self._export_event_validation_results(output_path=self.pm.event_validation_results_json_path)
        upload_file(self.project_data.uid, self.pm.event_validation_results_json_path)
