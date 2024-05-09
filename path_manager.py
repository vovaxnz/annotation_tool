import os

from config import settings


class PathManager():

    def __init__(self, project_id: int):
        self.project_name = str(project_id).zfill(5)
        os.makedirs(self.project_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_local_path), exist_ok=True)

    @property
    def project_path(self):
        return os.path.join(settings.data_dir, "data", self.project_name)
    
    @property
    def db_local_path(self):
        return os.path.join(settings.data_dir, "db", "projects", f"{self.project_name}.sqlite")
    
    @property
    def db_path(self):
        return os.path.join("sqlite:////", self.db_local_path.lstrip(os.sep))
    
    @property
    def figures_ann_path(self):
        return os.path.join(self.project_path, f"figures.json")
    
    @property
    def meta_ann_path(self):
        return os.path.join(self.project_path, f"meta.json")
    
    @property
    def review_ann_path(self):
        return os.path.join(self.project_path, f"review.json")
    
    @property
    def images_path(self):
        return os.path.join(self.project_path, f"images")
    
    @property
    def archive_path(self):
        return os.path.join(self.project_path, f"archive.zip")
    
    @property
    def video_path(self):
        return os.path.join(self.project_path, f"video.mp4")
    
    @property
    def selected_frames_json_path(self):
        return os.path.join(self.project_path, f"selected_frames.json")
    
    