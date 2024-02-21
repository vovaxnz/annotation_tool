import os

from config import data_dir


class PathManager():

    def __init__(self, project_id: int):
        self.project_name = str(project_id).zfill(5)
        os.makedirs(self.project_path, exist_ok=True)
        os.makedirs(self.annotation_home_path, exist_ok=True)

    @property
    def project_path(self):
        return os.path.join(data_dir, self.project_name)
    
    @property
    def annotation_home_path(self):
        return os.path.join(os.path.expanduser("~"), ".annotation")

    @property
    def db_path(self):
        # Store db in home because transactions are processed 10x faster on ssd.
        return os.path.join("sqlite:////", self.annotation_home_path.lstrip("/"), f"{self.project_name}.sqlite")
    
    @property
    def figures_ann_path(self):
        return os.path.join(self.project_path, f"figures.json")
    
    @property
    def review_ann_path(self):
        return os.path.join(self.project_path, f"review.json")
    
    @property
    def images_path(self):
        return os.path.join(self.project_path, f"images")