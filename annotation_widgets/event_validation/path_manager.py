import os

from path_manager import BasePathManager


class EventValidationPathManager(BasePathManager):

    def __init__(self, project_id: int):
        super().__init__(project_id)

    @property
    def archive_path(self):
        return os.path.join(self.project_path, f"archive.zip")

    @property
    def video_path(self):
        return os.path.join(self.project_path, f"videos")

    @property
    def images_path(self):
        return os.path.join(self.project_path, f"images")

    @property
    def event_validation_results_json_path(self):
        return os.path.join(self.project_path, f"event_validation_results.json")
