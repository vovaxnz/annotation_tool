import os

from path_manager import BasePathManager


class LabelingPathManager(BasePathManager):

    def __init__(self, project_id: int):
        super().__init__(project_id)

    @property
    def figures_ann_path(self):  # Labeling
        return os.path.join(self.project_path, f"figures.json")

    @property
    def review_ann_path(self):  # Labeling
        return os.path.join(self.project_path, f"review.json")

    @property
    def images_path(self):  # Labeling
        return os.path.join(self.project_path, f"images")

    @property
    def archive_path(self):
        return os.path.join(self.project_path, f"archive.zip")
