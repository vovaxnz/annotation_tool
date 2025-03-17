import json
import os
import re
import tkinter as tk
from tkinter import messagebox

from annotation_widgets.event_validation.models import Event
from annotation_widgets.event_validation.path_manager import EventValidationPathManager
from annotation_widgets.io import AbstractAnnotationIO
from file_processing.file_transfer import FileTransferClient, download_file, upload_file
from file_processing.unzipping import ArchiveUnzipper
from models import ProjectData, Value
from utils import save_json, open_json


class EventValidationIO(AbstractAnnotationIO):

    def __init__(self, project_data: ProjectData):
        self.project_data: ProjectData = project_data
        self.pm: EventValidationPathManager = self.get_path_manager(project_data.id)

    def get_path_manager(self, project_id: int):
        return EventValidationPathManager(project_id)

    def download_project(self, root: tk.Tk):
        """Downloads data and annotations from the server. Shows loading window while downloading"""
        if not os.path.isfile(self.pm.archive_path):
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.archive_path),
                save_path=self.pm.archive_path,
            )
            download_file(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.meta_ann_path),
                save_path=self.pm.meta_ann_path,
            )
        if not os.path.isdir(self.pm.videos_path):
            assert os.path.isfile(self.pm.archive_path)
            au = ArchiveUnzipper(window_title="Unzip progress", root=root)
            au.unzip(self.pm.archive_path, self.pm.project_path)

        if not os.path.isfile(self.pm.event_validation_results_json_path):
            download_file(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.event_validation_results_json_path),
                save_path=self.pm.event_validation_results_json_path,
                ignore_404=True
            )

    def overwrite_project(self):
        fields = open_json(self.pm.meta_ann_path)

        # Converts list structure into tree structure to avoid explicit index usage further in code.
        fields_tree_data = {}

        for item in fields:
            answer_color_map = {answer: color for answer, color in zip(item["answers"], item["colors"])}
            fields_tree_data[item["question"]] = answer_color_map

        Value.update_value("fields", json.dumps(fields_tree_data), overwrite=True)

        events = []
        pattern = r'event-(?P<uid>[a-f0-9\-]+)\.[a-z0-9]+$'

        # Import Events stored in event_validation_results_json
        if os.path.isfile(self.pm.event_validation_results_json_path):
            imported_events_data = open_json(self.pm.event_validation_results_json_path)
        else:
            imported_events_data = None
        
        if imported_events_data is not None:
            if list(fields_tree_data.keys()) != imported_events_data.get("fields"):
                raise Exception(
                    f"Task {self.project_data.id}: Validation rules are different in `event_validation_results.json` and `meta.json`. "
                    f"Please reach out to Administrator to handle this issue."
                )

        for video_name in sorted(os.listdir(self.pm.videos_path)):
            match = re.search(pattern, str(video_name))
            if match:
                video_uid = match.group("uid")
                event_obj = Event(uid=video_uid)

                if imported_events_data is not None:
                    imported_event = imported_events_data.get("events", {}).get(video_uid)
                    if imported_event is not None:
                        event_obj.custom_fields = json.dumps(imported_event.get("answers"))
                        event_obj.comment = imported_event.get("comment") if imported_event.get("comment") else None

                events.append(event_obj)
            else:
                raise RuntimeError(f"Incorrect video name format {video_name}")

        assert len(events) == len(os.listdir(self.pm.videos_path))

        Event.overwrite(events)



    def download_and_overwrite_annotations(self):
        """Force download and overwrite annotations in the database"""

        download_file(
            uid=self.project_data.uid,
            file_name=os.path.basename(self.pm.event_validation_results_json_path),
            save_path=self.pm.event_validation_results_json_path,
            ignore_404=True,
        )
        download_file(
            uid=self.project_data.uid,
            file_name=os.path.basename(self.pm.meta_ann_path),
            save_path=self.pm.meta_ann_path,
        )
        self.overwrite_project()

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
                "76a4365d-25cb-4403-a76e-cfe70016a8e7": {
                    "answers": ["True", None, "TP"],
                    "comment": "..."
                }
                ...
            }
        }
        """
        fields = json.loads(Value.get_value("fields"))

        result = {"fields": list(fields.keys()), "events": {}}

        for event in Event.all():
            result["events"][event.uid] = {
                "answers": json.loads(event.custom_fields),
                "comment": event.comment
            }

        save_json(result, output_path)

    def _upload_annotation_results(self):
        self._export_event_validation_results(output_path=self.pm.event_validation_results_json_path)
        upload_file(self.project_data.uid, self.pm.event_validation_results_json_path)

    def complete_annotation(self, duration_hours: float, root: tk.Tk):
        if unanswered_events := Event.get_unvalidated_event_ids():
            messagebox.showerror(title="Validation Error", message=f"Events № {unanswered_events} are not answered. Finish them to complete the project")
        else:
            super().complete_annotation(duration_hours=duration_hours, root=root)
