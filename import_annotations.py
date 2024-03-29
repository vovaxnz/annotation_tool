

import json
import os
from typing import Dict, List, Tuple

from api_requests import get_project_data
from enums import FigureType
from file_transfer import FileTransferClient
from models import KeypointGroup, Label, LabeledImage, BBox, Mask, ReviewLabel, Value
from path_manager import PathManager
from utils import open_json, save_json
from PIL import Image


def get_img_size(img_path: str) -> Tuple[int, int]:
    """Returns width and height of img"""
    assert os.path.isfile(img_path), f"{img_path} is not found"
    im = Image.open(img_path)
    frame_width, frame_height = im.size
    return int(frame_width), int(frame_height)



def import_project(
        figures_ann_path: str, 
        review_ann_path: str, 
        meta_ann_path: str,
        img_dir: str, 
        overwrite: bool = False
    ):
    """
    review_ann format:
    {
        "img_name.jpg": [{"text": "...", "x": ..., "y": ...}, ...],
        ...
    }

    meta ann format:
    {
        "review_labels": [
            {"name": "Add object", "color": "yellow", "hotkey": "1", "type": "REVIEW_LABEL"}
        ], 
        "labels": [
            {"name": "truck", "color": "yellow", "hotkey": "1", "type": "BBOX"},
        ], 
        (Optional) "keypoint_connections": [{"from": "fl", "to": "bl", "color": "red"}, ...]
        (Optional) "keypoint_info": {"fl": {"x": 0, "y": 0, "color": "orange"}, ...} # 
    }

    figures_ann format:
    {
        "img_name.jpg": {
            "trash": false, 
            "bboxes": [], 
            "masks": {class_name: rle}, 
            "kgroups": [],
        },
    }
    """
    
    # Set current image id to 0
    Value.update_value("img_id", 0, overwrite=False)

    figures_data = open_json(figures_ann_path)
    meta_data = open_json(meta_ann_path)

    # Labels
    for label_dict in meta_data["labels"] + meta_data["review_labels"]:
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
    value = meta_data.get("keypoint_connections")
    if value is not None:
        Value.update_value(name="keypoint_connections", value=json.dumps(value))

    # Keypoint Positions
    value = meta_data.get("keypoint_info")
    if value is not None:
        Value.update_value(name="keypoint_info", value=json.dumps(value))

    # Figures
    limages = list()
    for img_name in os.listdir(img_dir): 
        img_info = figures_data.get(img_name)
        if img_info is not None:
            trash_tag = img_info.get("trash", False)
            bboxes = img_info.get("bboxes", list())
            kgroups = img_info.get("kgroups", list())
            masks = img_info.get("masks", dict())
            width, height = img_info["width"], img_info["height"]
        else:
            trash_tag = False
            bboxes = list()
            kgroups = list()
            masks = dict()
            width, height = get_img_size(os.path.join(img_dir, img_name))
        
        image = LabeledImage.get(name=img_name)
        if image is not None:
            if overwrite:
                print("LabeledImage", img_name, "is already in the database, overwriting")
                image.delete()
            else:
                print("LabeledImage", img_name, "is already in the database, skipping")
                continue

        img = LabeledImage(name=img_name, height=height, width=width)
        
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
        
        # Masks
        for label_name, rle in masks.items():
            mask = Mask(
                label=label_name,
                rle=rle,
                height=img.height,
                width=img.width,
            )
            img.masks.append(mask)
        
        # Trash
        img.trash = trash_tag

        limages.append(img)
    LabeledImage.save_batch(limages)

    # Review labels
    if os.path.isfile(review_ann_path):
        review_data = open_json(review_ann_path)
        limages = list()
        for img_name in os.listdir(img_dir):
            image = LabeledImage.get(name=img_name)
            if len(image.review_labels) > 0:
                continue
            review_data_for_image = review_data.get(image.name)
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
    figures_dict = dict()
    print("Exporting figures...")
    for limage in LabeledImage.all():
        figures_dict[limage.name] = {
            "trash": limage.trash, 
            "bboxes": [{"x1": bbox.x1, "y1": bbox.y1, "x2": bbox.x2, "y2": bbox.y2, "label": bbox.label} for bbox in limage.bboxes],
            "kgroups": [{"points": json.loads(kgroup.serialize_keypoints(kgroup.keypoints)), "label": kgroup.label} for kgroup in limage.kgroups],
            "masks": {mask.label: mask.rle for mask in limage.masks},
            "height": limage.height,
            "width": limage.width
        }
    save_json(figures_dict, figures_ann_path) 


def export_review(review_ann_path):
    review_label_dict = dict()
    print("Exporting review labels...")
    for limage in LabeledImage.all(): 
        if len(limage.review_labels) > 0:
            review_label_dict[limage.name] = [
                {"label": rlabel.label, "x": rlabel.x, "y": rlabel.y}
                for rlabel in limage.review_labels
            ]
    save_json(review_label_dict, review_ann_path) 


def overwrite_annotations(project_id):

    annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path, meta_ann_path = get_project_data(project_id)
    
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
    ftc.download(
        local_path=pm.meta_ann_path, 
        remote_path=meta_ann_path,
        show_progressbar=False
    )

    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        img_dir=pm.images_path,
        meta_ann_path=pm.meta_ann_path,
        overwrite=True,
    )
