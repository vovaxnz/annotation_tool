

import json
import os
from typing import Dict, List

from api_requests import get_project_data
from enums import FigureType
from file_transfer import FileTransferClient
from models import KeypointGroup, Label, LabeledImage, BBox, ReviewLabel, Value
from path_manager import PathManager
from utils import open_json, save_json


def import_project(figures_ann_path: str, review_ann_path: str, img_dir: str, overwrite: bool = False): # TODO: Maybe use strategy pattern or something like that (bboxes, keypoints, segmentation)?
    """
    review_ann format:
    {
        "labels": [{"name": "Add object", "color": "yellow", "hotkey": "1", "type": "REVIEW_LABEL"},], 
        "images": {"img_name.jpg": [{"text": "...", "x": ..., "y": ...}, ...]},
    }
    figures_ann format:
    {
        "labels": [{"name": "truck", "color": "yellow", "hotkey": "1", "type": "BBOX"},], 
        "images": {"img_name.jpg": {
            "trash": false, 
            "bboxes": [], 
            "masks": [], 
            "kgroups": [],
        }}},
        (Optional) "keypoint_connections": [{"from": "fl", "to": "bl", "color": "red"}, ...]
        (Optional) "keypoint_info": {"fl": {"x": 0, "y": 0, "color": "orange"}, ...} # 
    }

    """
    
    # Set current image id to 0
    Value.update_value("img_id", 0, overwrite=False)

    figures_data = open_json(figures_ann_path)
    review_data = open_json(review_ann_path)

    # Labels
    for label_dict in figures_data["labels"] + review_data["labels"]:
        label = Label.get_by_name(name=label_dict["name"])
        if label is None:
            label = Label(
                name=label_dict["name"],
                color=label_dict["color"],
                hotkey=label_dict["hotkey"],
                type=label_dict["type"]
            )
        else:
            label.color = label_dict["color"]
            label.hotkey = label_dict["hotkey"]
            label.type=label_dict["type"]
        label.save()
 
    # Keypoint Connections
    value = figures_data.get("keypoint_connections")
    if value is not None:
        Value.update_value(name="keypoint_connections", value=json.dumps(value))

    # Keypoint Positions
    value = figures_data.get("keypoint_info")
    if value is not None:
        Value.update_value(name="keypoint_info", value=json.dumps(value))

    # Figures
    limages = list()
    for img_name in os.listdir(img_dir): 
        img_info = figures_data["images"].get(img_name)
        if img_info is not None:
            trash_tag = img_info.get("trash", False)
            bboxes = img_info.get("bboxes", list())
            kgroups = img_info.get("kgroups", list())
            # masks = img_info.get("masks", list())
        else:
            trash_tag = False
            bboxes = list()
            kgroups = list()
            # masks = list()

        image = LabeledImage.get(name=img_name)
        if image is not None:
            if overwrite:
                print("LabeledImage", img_name, "is already in the database, overwriting")
                image.delete()
            else:
                print("LabeledImage", img_name, "is already in the database, skipping")
                continue
        img = LabeledImage(name=img_name)
        
        # BBoxes
        for bbox in bboxes:
            rect = BBox(
                x1=bbox["x1"],
                y1=bbox["y1"],
                x2=bbox["x2"],
                y2=bbox["y2"],
                label=bbox["label"],
            )
            img.bboxes.append(rect)

        # KGroups
        for kgroup_data in kgroups:
            kgroup = KeypointGroup(
                label=kgroup_data["label"],
                keypoint_data=json.dumps(kgroup_data["points"])
            )
            img.kgroups.append(kgroup)
        
        # Trash
        img.trash = trash_tag

        limages.append(img)
    LabeledImage.save_batch(limages)

    # Review labels
    if os.path.isfile(review_ann_path):
        limages = list()
        for img_name in os.listdir(img_dir):
            image = LabeledImage.get(name=img_name)
            if len(image.review_labels) > 0:
                continue
            review_data_for_image = review_data["images"].get(image.name)
            if review_data_for_image is not None:
                for review_label_dict in review_data_for_image:
                    rl = ReviewLabel(
                        x=review_label_dict["x"],
                        y=review_label_dict["y"],
                        label=review_label_dict["label"],
                    )
                    image.review_labels.append(rl)
                limages.append(image)
        LabeledImage.save_batch(limages)


def export_figures(figures_ann_path: str):
    figures_dict = {
        "labels": [{"name": l.name, "color": l.color, "hotkey": l.hotkey, "type": l.type} for l in Label.get_figure_labels()], 
        "images": dict()
    }
    print("Exporting figures...")
    for limage in LabeledImage.all():
        figures_dict["images"][limage.name] = {
            "trash": limage.trash, 
            "bboxes": [{"x1": bbox.x1, "y1": bbox.y1, "x2": bbox.x2, "y2": bbox.y2, "label": bbox.label} for bbox in limage.bboxes],
            "kgroups": [{"points": json.loads(kgroup.serialize_keypoints(kgroup.keypoints)), "label": kgroup.label} for kgroup in limage.kgroups],
            # "masks": [{"rle": mask.rle,  "label": mask.label} for mask in image.masks]
        }
    save_json(figures_dict, figures_ann_path) 


def export_review(review_ann_path):
    review_label_dict = {
        "labels": [{"name": label.name, "color": label.color, "hotkey": label.hotkey, "type": FigureType.REVIEW_LABEL.name} for label in Label.get_review_labels()], 
        "images": dict()
    }
    print("Exporting review labels...")
    for limage in LabeledImage.all(): 
        if len(limage.review_labels) > 0:
            review_label_dict["images"][limage.name] = [
                {"label": rlabel.label, "x": rlabel.x, "y": rlabel.y}
                for rlabel in limage.review_labels
            ]
    save_json(review_label_dict, review_ann_path) 


def overwrite_annotations(project_id):

    annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path = get_project_data(project_id)
    pm = PathManager(project_id)
    ftc = FileTransferClient()

    ftc.download(
        local_path=pm.figures_ann_path, 
        remote_path=figures_ann_path,
        show_progressbar=False
    )
    ftc.download(
        local_path=pm.review_ann_path, 
        remote_path=review_ann_path,
        show_progressbar=False
    )

    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        img_dir=pm.images_path,
        overwrite=True,
    )