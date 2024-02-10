

from typing import Dict, List
from models import Image, Rectangle
from utils import open_json


def import_project(
    data: List[Dict],
    db_path: str, # TODO: Use separate db for each project
    overwrite: bool = False,
):
    """
    {"labels": {"name": "", "color": "yellow"}, "images": {"bboxes": [], "masks": [], "name": ""}}}
    
    """
    
    # TODO: Set current image id to 0
    ...

    # TODO: Add labels and their colors
    ...


    for img_info in data["images"]:
        bboxes = img_info["bboxes"]
        masks = img_info["masks"]
        img_name = img_info["name"]

        image = Image.get(name=img_name)
        if image is not None:
            if overwrite:
                print("Image", img_name, "is already in the database, overwriting")
                image.delete()
            else:
                print("Image", img_name, "is already in the database, skipping")
                continue
        img = Image(name=img_name)
        
        for bbox in bboxes:
            rect = Rectangle(
                x1=bbox["x1"],
                y1=bbox["y1"],
                x2=bbox["x2"],
                y2=bbox["y2"],
                label=bbox["label"],
            )
            img.rectangles.append(rect)
        img.save()