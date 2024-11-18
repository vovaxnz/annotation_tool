from json import JSONDecodeError
from typing import List, Tuple
from urllib.error import HTTPError

import requests
from config import settings
from enums import AnnotationMode, AnnotationStage
from exceptions import MessageBoxException
from models import ProjectData


def get_projects_data() -> List[ProjectData]: 
    url = f'{settings.api_url}/api/annotation/projects_data/'

    data = {'user_token': settings.token}

    for i in range(2):
        response = requests.post(url, json=data)

        if response.status_code == 200:
        
            projects = response.json()["projects"]

            result = list()
            for project in projects:
                result.append(ProjectData.from_json(project))
            return result
    
    raise MessageBoxException(f"Unable to get projects data. {response.status_code}")


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


def get_completed_projects_data() -> List[str]:
    url = f'{settings.api_url}/api/annotation/completed_projects_data/'

    data = {'user_token': settings.token}

    projects_data = []

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get("projects_uids", [])
    except (HTTPError, JSONDecodeError) as e:
        pass
