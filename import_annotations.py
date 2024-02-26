

import os
from typing import Dict, List

from tqdm import tqdm
from api_requests import get_project_data
from file_transfer import FileTransferClient
from models import IssueName, Label, LabeledImage, BBox, ReviewLabel, Value
from path_manager import PathManager
from utils import open_json, save_json


def import_project(figures_ann_path: str, review_ann_path: str, img_dir: str, overwrite: bool = False):
    """
    review_ann format:
    {
        "labels": [{"name": "", "color": "yellow", "hotkey": "1"}], 
        "images": {"img_name.jpg": [{"text": "...", "x": ..., "y": ...}, ...]},
    }
    figures_ann format:
    {
        "labels": [{"name": "", "color": "yellow", "hotkey": "1"}], 
        "images": {"img_name.jpg": {"bboxes": [], "masks": []}}},
    }
    """
    
    # Set current image id to 0
    Value.update_value("img_id", 0, overwrite=False)

    figures_data = open_json(figures_ann_path)

    # Labels
    for label_dict in figures_data["labels"]:
        label = Label.get_by_name(name=label_dict["name"])
        if label is None:
            label = Label(
                name=label_dict["name"],
                color=label_dict["color"],
                hotkey=label_dict["hotkey"]
            )
        else:
            label.color = label_dict["color"]
            label.hotkey = label_dict["hotkey"]
        label.save()

    # Figures
    limages = list()
    for img_name in os.listdir(img_dir): 
        img_info = figures_data["images"].get(img_name)
        if img_info is not None:
            bboxes = img_info.get("bboxes", list())
            # masks = img_info.get("masks", list())
        else:
            bboxes = list()
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
        
        for bbox in bboxes:
            rect = BBox(
                x1=bbox["x1"],
                y1=bbox["y1"],
                x2=bbox["x2"],
                y2=bbox["y2"],
                label=bbox["label"],
            )
            img.bboxes.append(rect)
        limages.append(img)
    LabeledImage.save_batch(limages)

    # review_ann format:
    # {
    #     "issues": [{"name": "", "color": "yellow", "hotkey": "1"}], 
    #     "images": {"img_name.jpg": [{"text": "...", "x": ..., "y": ...}, ...]},
    # }
    if os.path.isfile(review_ann_path):
        review_data = open_json(review_ann_path)
        
        # Issue names
        for issue_dict in review_data["issues"]:
            issue = IssueName.get_by_name(name=issue_dict["name"])
            if issue is None:
                issue = IssueName(
                    name=issue_dict["name"],
                    color=issue_dict["color"],
                    hotkey=issue_dict["hotkey"]
                )
            else:
                issue.color = issue_dict["color"]
                issue.hotkey = issue_dict["hotkey"]
            issue.save()
        
        # Review labels
        limages = list()
        for img_name in os.listdir(img_dir):
            image = LabeledImage.get(name=img_name)
            if image.reviewed:
                continue
            if len(image.review_labels) > 0:
                continue
            review_data_for_image = review_data["images"].get(image.name)
            if review_data_for_image is not None:
                for review_label_dict in review_data_for_image:
                    rl = ReviewLabel(
                        x=review_label_dict["x"],
                        y=review_label_dict["y"],
                        text=review_label_dict["text"],
                    )
                    image.review_labels.append(rl)
                limages.append(image)
        LabeledImage.save_batch(limages)


def export_figures(figures_ann_path: str):
    figures_dict = {
        "labels": [{"name": l.name, "color": l.color, "hotkey": l.hotkey} for l in Label.all()], 
        "images": dict()
    }
    for limage in tqdm(LabeledImage.all(), desc=f"Exporting figures"):
        figures_dict["images"][limage.name] = {
            "trash": limage.trash, 
            "bboxes": [{"x1": bbox.x1, "y1": bbox.y1, "x2": bbox.x2, "y2": bbox.y2, "label": bbox.label} for bbox in limage.bboxes],
            # "masks": [{"rle": mask.rle,  "label": mask.label} for mask in image.masks]
        }
    save_json(figures_dict, figures_ann_path) 


def export_review(review_ann_path):
    review_label_dict = {
        "issues": [{"name": issue.name, "color": issue.color, "hotkey": issue.hotkey} for issue in IssueName.all()], 
        "images": dict()
    }
    for limage in tqdm(LabeledImage.all(), desc=f"Exporting review labels"): 
        if len(limage.review_labels) > 0:
            review_label_dict["images"][limage.name] = [
                {"text": rlabel.text, "x": rlabel.x, "y": rlabel.y}
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