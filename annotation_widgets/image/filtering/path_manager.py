import os

from path_manager import BasePathManager


class FilteringPathManager(BasePathManager):
    def __init__(self, project_id: int):
        super().__init__(project_id)

    @property
    def video_path(self):
        return os.path.join(self.project_path, f"video.mp4")

    @property
    def selected_frames_json_path(self):
        return os.path.join(self.project_path, f"selected_frames.json")

    @property
    def archive_path(self):
        return
