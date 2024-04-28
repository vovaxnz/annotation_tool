from dataclasses import dataclass
from typing import List, Tuple
import requests
from config import settings
from enums import AnnotationMode, AnnotationStage
from exceptions import MessageBoxException


@dataclass
class ProjectData:
    id: int
    uid: str
    stage: AnnotationStage
    mode: AnnotationMode


def get_projects_data() -> List[ProjectData]: 
    url = f'{settings.api_url}/api/annotation/projects_data/'

    data = {'user_token': settings.token}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(f"Unable to get projects data. {response.status_code}")
    
    projects = response.json()["projects"]

    result = list()
    for project in projects:
        result.append(
            ProjectData(
                id=project["id"],
                uid=project["uid"],
                stage=getattr(AnnotationStage, project["annotation_stage"]),
                mode=getattr(AnnotationMode, project["annotation_mode"])
            )
        )
    return result


def get_project_data(project_id: int) -> Tuple[AnnotationStage, AnnotationMode, str]:
    "annotation_stage, annotation_mode, img_path, ann_path"
    url = f'{settings.api_url}/api/annotation/get_project_data/{project_id}/'

    data = {'user_token': settings.token}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(response)

    response_json = response.json()

    annotation_stage = getattr(AnnotationStage, response_json["annotation_stage"])
    annotation_mode = getattr(AnnotationMode, response_json["annotation_mode"])
    project_uid = response_json["project_uid"]

    return annotation_stage, annotation_mode, project_uid


def complete_task(project_id: int, duration_hours: float):
    url = f'{settings.api_url}/api/annotation/complete_task/{project_id}/' # Change stage of annotation project

    data = {'user_token': settings.token, 'duration_hours': duration_hours}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        try: 
            message = response.json()
        except:
            message = "Internal Server Error"
        raise MessageBoxException(message)