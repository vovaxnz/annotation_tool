import json
from typing import Dict, List
from annotation_widgets.image.models import Label
from annotation_widgets.io import AbstractAnnotationIO




class ImageIO(AbstractAnnotationIO):

    def overwrite_labels(self, labels_data: List[Dict]):

        for label_dict in labels_data:
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