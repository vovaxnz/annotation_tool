from typing import List, Tuple
import requests
from config import AnnotationStage, AnnotationMode, api_token, api_url
from exceptions import MessageBoxException


def get_project_ids() -> List[int]:
    url = f'{api_url}/api/annotation/project_ids/'

    data = {'user_token': api_token}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(response.json()["message"])
    
    return response.json()["project_ids"]


def get_project_data(project_id: int) -> Tuple[AnnotationStage, AnnotationMode, str, str]:
    "annotation_stage, annotation_mode, img_path, ann_path"
    url = f'{api_url}/api/annotation/get_project_data/{project_id}/'

    data = {'user_token': api_token}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(response.json()["message"])

    response_json = response.json()

    annotation_stage = getattr(AnnotationStage, response_json["annotation_stage"])
    annotation_mode = getattr(AnnotationMode, response_json["annotation_mode"])
    img_path = response_json["img_path"]
    review_ann_path = response_json["review_ann_path"]
    figures_ann_path = response_json["figures_ann_path"]

    return annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path


def complete_task(project_id: int, duration_hours: float):
    url = f'{api_url}/api/annotation/complete_task/{project_id}/' # Change stage of annotation project

    data = {'user_token': api_token, 'duration_hours': duration_hours}
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise MessageBoxException(response.json()["message"])