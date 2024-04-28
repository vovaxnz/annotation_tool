import os

from config import settings


class PathManager():

    def __init__(self, project_id: int):
        self.project_name = str(project_id).zfill(5)
        os.makedirs(self.project_path, exist_ok=True)
        os.makedirs(self.project_db_dir, exist_ok=True)

    @property
    def project_path(self):
        return os.path.join(settings.data_dir, "data", self.project_name)
    
    @property
    def project_db_dir(self):
        return os.path.join(settings.data_dir, "db", "projects")

    @property
    def db_path(self):
        return os.path.join("sqlite:////", self.project_db_dir.lstrip("/"), f"{self.project_name}.sqlite")
    
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
    
    