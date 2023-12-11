import argparse

from models import Image, Rectangle
from utils import open_json

parser = argparse.ArgumentParser()
parser.add_argument("--ann", type=str) 
parser.add_argument("--overwrite", action="store_true", help="Overwrite images and rectangles which already in the database") 
args = parser.parse_args()

annotations = open_json(args.ann)

for img_name, rects_data in annotations.items():
    image = Image.get(name=img_name)
    if image is not None:
        if args.rewrite:
            print("Image", img_name, "is already in the database, overwriting")
            image.delete()
        else:
            print("Image", img_name, "is already in the database, skipping")
            continue
    img = Image(name=img_name)
    for rd in rects_data:
        rect = Rectangle(
            xc=rd["xc"],
            yc=rd["yc"],
            h=rd["h"],
            w=rd["w"],
            angle=rd["angle"]
        )
        img.rectangles.append(rect)
    img.save()