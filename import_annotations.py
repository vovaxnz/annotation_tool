

import os
from typing import Dict, List
from models import Label, LabeledImage, BBox, Value


def import_project(data: List[Dict], img_dir: str, overwrite: bool = False):
    """
    {
        "labels": {"name": "", "color": "yellow", "hotkey": "1"}, 
        "images": {"img_name.jpg": {"bboxes": [], "masks": [], "review_labels": []}}},
        "review_mode": False,
        "annotation_mode": "BBOXES",
    }
    """
    
    # Set current image id to 0
    Value.update_value("img_id", 0, overwrite=False)



    for label_dict in data["labels"]:
        label = Label(
            name=label_dict["name"],
            color=label_dict["color"],
            hotkey=label_dict["hotkey"]
        )
        label.save()
        
    for img_name in os.listdir(img_dir):
        img_info = data["images"].get(img_name)
        if img_info is not None:
            bboxes = img_info["bboxes"]
            masks = img_info["masks"]
        else:
            bboxes = list()
            masks = list()

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
        img.save()