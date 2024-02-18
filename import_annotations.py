

import os
from typing import Dict, List
from models import Label, LabeledImage, BBox, ReviewLabel, Value
from utils import open_json


def import_project(figures_ann_path: str, review_ann_path: str, img_dir: str, overwrite: bool = False):
    """
    review_ann format:
    {
        "img_name.jpg": [{"text": "...", "x": ..., "y": ...}], 
        ...
    }
    figures_ann format:
    {
        "labels": [{"name": "", "color": "yellow", "hotkey": "1"}], 
        "images": {"img_name.jpg": {"bboxes": [], "masks": []}}},
    }
    """
    
    # Set current image id to 0
    Value.update_value("img_id", 0, overwrite=False)

    # Figures
    figures_data = open_json(figures_ann_path)

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

    # Review labels
    if os.path.isfile(review_ann_path):
        review_labels = open_json(review_ann_path)
        for img_name in os.listdir(img_dir):
            image = LabeledImage.get(name=img_name)
            image.clear_review_labels()
            review_labels_for_image = review_labels.get(image.name)
            if review_labels_for_image is not None:
                for review_label_dict in review_labels_for_image:
                    rl = ReviewLabel(
                        x=review_label_dict["x"],
                        y=review_label_dict["y"],
                        text=review_label_dict["text"],
                    )
                    image.review_labels.append(rl)
                img.save()