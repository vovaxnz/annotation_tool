from json import JSONDecodeError
from typing import List, Optional, Tuple
from urllib.error import HTTPError

import requests
from config import settings
from enums import AnnotationMode, AnnotationStage
from exceptions import MessageBoxException
from models import ProjectData
from path_manager import get_local_projects_data


def get_projects_data(only_assigned_to_user: bool = True, raise_error: bool = True) -> Optional[List[ProjectData]]:
    url = f'{settings.api_url}/api/annotation/projects_data/'
    data = {'user_token': settings.token}

    try:
        response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if raise_error:
            raise MessageBoxException(f"Unable to connect to the server: {e}")
        else:
            return None

    projects = response.json().get("projects", [])
    result = [
        ProjectData.from_json(project)
        for project in projects
        if not only_assigned_to_user or project.get("assigned_to_user", True)
    ]

    return result


def get_project_data(project_uid: str) -> Tuple[AnnotationStage, AnnotationMode]:
    "annotation_stage, annotation_mode, img_path, ann_path"
    url = f'{settings.api_url}/api/annotation/get_project_data/{project_uid}/'

    data = {'user_token': settings.token}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(response)

    response_json = response.json()

    annotation_stage = getattr(AnnotationStage, response_json["annotation_stage"])
    annotation_mode = getattr(AnnotationMode, response_json["annotation_mode"])

    return annotation_stage, annotation_mode


def complete_task(project_uid: int, duration_hours: float):
    url = f'{settings.api_url}/api/annotation/complete_task/{project_uid}/' # Change stage of annotation project

    data = {'user_token': settings.token, 'duration_hours': duration_hours}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        try: 
            message = response.json()
        except:
            message = f"Internal Server Error with project uid {project_uid}"
        raise MessageBoxException(message)
