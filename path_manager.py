import os
from typing import List

from config import settings
from enums import AnnotationMode, AnnotationStage
from models import ProjectData
from utils import get_datetime_str, open_json


def get_local_projects_data() -> List[ProjectData]: 
    result = list()
    for project_name in os.listdir(os.path.join(settings.data_dir, "data")):
        pm = PathManager(project_id=project_name)
        if pm.is_valid:
            result.append(get_project_data_from_json(pm.state_path))
    return result


def get_project_data_from_json(json_path) -> ProjectData:
    data = open_json(json_path)
    return ProjectData(
        id=data["id"],
        uid=data["uid"],
        stage=getattr(AnnotationStage, data["stage"]),
        mode=getattr(AnnotationMode, data["mode"]),
    )


class PathManager():  # TODO: Implement a concrete path manager for each annotation_widget inherited from AbstractPathManager

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
    def videos_folder_path(self):
        return os.path.join(self.project_path, f"videos")

    @property
    def images_folder_path(self):
        return os.path.join(self.project_path, f"images")

    @property
    def video_path(self):
        return os.path.join(self.project_path, f"video.mp4")
    
    @property
    def selected_frames_json_path(self):
        return os.path.join(self.project_path, f"selected_frames.json")

    @property
    def event_validation_results_json_path(self):
        return os.path.join(self.project_path, f"event_validation_results.json")

    @property
    def state_path(self):
        return os.path.join(self.project_path, f"state.json")
    
    @property
    def statistics_path(self):
        for file_name in os.listdir(self.project_path):
            if "statistics" in file_name:
                return os.path.join(self.project_path, file_name)
        return os.path.join(self.project_path, f"statistics_{get_datetime_str()}.txt")
    
    @property
    def is_valid(self) -> bool:
        if not os.path.isfile(self.state_path):
            return False
        if not os.path.isfile(self.db_local_path):
            return False
        return True
