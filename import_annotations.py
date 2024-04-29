

import json
import os
from typing import Dict, List, Tuple

from api_requests import get_project_data
from enums import AnnotationStage, FigureType
from exceptions import MessageBoxException
from file_processing.file_transfer import download_file
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
            {"name": "truck", "color": "yellow", "hotkey": "1", "type": "BBOX", "attributes": "..."},
        ], 
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
        label = Label.get(name=label_dict["name"], figure_type=label_dict["type"])

        attributes = label_dict.get("attributes")
        if attributes is not None:
            attributes = json.dumps(attributes)

        if label is None:
            label = Label(
                name=label_dict["name"],
                color=label_dict["color"],
                hotkey=label_dict["hotkey"],
                type=label_dict["type"],
                attributes=attributes
            )
        else:
            label.color = label_dict["color"]
            label.hotkey = label_dict["hotkey"]
            label.attributes = attributes
        label.save()
 
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
                image.delete()
            else:
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
                keypoints_data=json.dumps(kgroup_data["points"])
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

    annotation_stage, annotation_mode, project_uid = get_project_data(project_id)
    
    pm = PathManager(project_id)

    download_file(
        uid=project_uid, 
        file_name=os.path.basename(pm.figures_ann_path), 
        save_path=pm.figures_ann_path, 
    )
    if annotation_stage is AnnotationStage.CORRECTION:
        download_file(
            uid=project_uid, 
            file_name=os.path.basename(pm.review_ann_path), 
            save_path=pm.review_ann_path, 
        )
    download_file(
        uid=project_uid, 
        file_name=os.path.basename(pm.meta_ann_path), 
        save_path=pm.meta_ann_path, 
    )

    img_ann_number = len(open_json(pm.figures_ann_path))
    img_number = len(os.listdir(pm.images_path))
    if img_number != img_ann_number:
        raise MessageBoxException(f"The project {project_id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")


    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        img_dir=pm.images_path,
        meta_ann_path=pm.meta_ann_path,
        overwrite=True,
    )
