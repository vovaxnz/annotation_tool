import os
from typing import List

from config import settings
from enums import AnnotationMode, AnnotationStage
from models import ProjectData
from utils import get_datetime_str, open_json


def get_local_projects_data() -> List[ProjectData]: 
    result = list()
    if os.path.isdir(os.path.join(settings.data_dir, "data")):
        for project_name in os.listdir(os.path.join(settings.data_dir, "data")):
            pm = BasePathManager(project_id=project_name)
            if pm.is_valid:
                result.append(ProjectData.from_json(open_json(pm.state_path)))
    return result



class BasePathManager:

    def __init__(self, project_id: int):
        self.project_name = str(project_id).zfill(5)
        os.makedirs(self.project_path, exist_ok=True)

    @property
    def project_path(self):  # Common
        return os.path.join(settings.data_dir, "data", self.project_name)
    
    @property
    def db_local_path(self):  # Common
        return os.path.join(self.project_path, f"db.sqlite")

    @property
    def db_path(self):  # Common
        return os.path.join("sqlite:////", self.db_local_path.lstrip(os.sep))

    @property
    def state_path(self):  # Common
        return os.path.join(self.project_path, f"state.json")

    @property
    def meta_ann_path(self):  # EventValidation, Labeling
        return os.path.join(self.project_path, f"meta.json")

    @property
    def statistics_path(self):  # Common
        for file_name in os.listdir(self.project_path):
            if "statistics" in file_name:
                return os.path.join(self.project_path, file_name)
        return os.path.join(self.project_path, f"statistics_{get_datetime_str()}.txt")

    @property
    def is_valid(self) -> bool:  # Common
        if not os.path.isfile(self.state_path):
            return False
        if not os.path.isfile(self.db_local_path):
            return False
        return True
