import json
import os
import tkinter as tk

from annotation_widgets.io import AbstractAnnotationIO
from api_requests import get_project_data
from enums import AnnotationStage
from exceptions import MessageBoxException
from file_processing.file_transfer import FileTransferClient, download_file, upload_file
from file_processing.unzipping import ArchiveUnzipper
from gui_utils import get_loading_window
from models import Value, ProjectData
from utils import check_correct_json, get_img_size, open_json, save_json
from .bboxes.models import BBox
from .keypoints.models import KeypointGroup
from .models import Label, LabeledImage, ReviewLabel
from .path_manager import LabelingPathManager
from .segmentation.models import Mask


class ImageLabelingIO(AbstractAnnotationIO):

    def get_path_manager(self, project_id: int):
        return LabelingPathManager(project_id)

    def download_project(self, root: tk.Tk):
        """Downloads data and annotations from the server. Shows loading window while downloading"""

        loading_window = get_loading_window(text="Downloading annotations...", root=root)
        if not os.path.isfile(self.pm.meta_ann_path) or not check_correct_json(self.pm.meta_ann_path):
            download_file(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.meta_ann_path),
                save_path=self.pm.meta_ann_path,
            )
        if not os.path.isfile(self.pm.figures_ann_path) or not check_correct_json(self.pm.figures_ann_path):
            download_file(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.figures_ann_path),
                save_path=self.pm.figures_ann_path,
            )

        if self.project_data.stage is AnnotationStage.CORRECTION:
            if not check_correct_json(self.pm.review_ann_path):
                download_file(
                    uid=self.project_data.uid,
                    file_name=os.path.basename(self.pm.review_ann_path),
                    save_path=self.pm.review_ann_path,
                )

        img_ann_number = len(open_json(self.pm.figures_ann_path))
        if os.path.isdir(self.pm.images_path):
            img_number = len(os.listdir(self.pm.images_path))
        else:
            img_number = 0

        loading_window.destroy()
        if not os.path.isdir(self.pm.images_path) or img_number != img_ann_number:
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=self.project_data.uid,
                file_name=os.path.basename(self.pm.archive_path),
                save_path=self.pm.archive_path,
            )
            au = ArchiveUnzipper(window_title="Unzip progress", root=root)
            au.unzip(self.pm.archive_path, self.pm.images_path)
            if os.path.isfile(self.pm.archive_path):
                os.remove(self.pm.archive_path)

        img_number = len(os.listdir(self.pm.images_path))
        if img_number != img_ann_number:
            raise MessageBoxException(f"The project {self.project_data.id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")

    def import_project(self, overwrite: bool = False): 
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
        Value.update_value("item_id", 0, overwrite=False)

        figures_data = open_json(self.pm.figures_ann_path )
        meta_data = open_json(self.pm.meta_ann_path)

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
        for img_name in os.listdir(self.pm.images_path): 
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
                width, height = get_img_size(os.path.join(self.pm.images_path, img_name))
            
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
        if os.path.isfile(self.pm.review_ann_path ):
            review_data = open_json(self.pm.review_ann_path )
            limages = list()
            for img_name in os.listdir(self.pm.images_path):
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

    def _export_figures(self, figures_ann_path: str):
        figures_dict = dict()
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

    def _export_review(self, review_ann_path):
        review_label_dict = dict()
        for limage in LabeledImage.all(): 
            if len(limage.review_labels) > 0:
                review_label_dict[limage.name] = [
                    {"label": rlabel.label, "x": rlabel.x, "y": rlabel.y}
                    for rlabel in limage.review_labels
                ]
        save_json(review_label_dict, review_ann_path) 

    def overwrite_annotations(self):
        """Force download and overwrite annotations in the database"""

        project_id, project_uid = self.project_data.id, self.project_data.uid

        annotation_stage, annotation_mode = get_project_data(project_uid)
        
        download_file(
            uid=project_uid, 
            file_name=os.path.basename(self.pm.figures_ann_path), 
            save_path=self.pm.figures_ann_path, 
        )
        if annotation_stage is AnnotationStage.CORRECTION:
            download_file(
                uid=project_uid, 
                file_name=os.path.basename(self.pm.review_ann_path), 
                save_path=self.pm.review_ann_path, 
            )
        download_file(
            uid=project_uid, 
            file_name=os.path.basename(self.pm.meta_ann_path), 
            save_path=self.pm.meta_ann_path, 
        )

        img_ann_number = len(open_json(self.pm.figures_ann_path))
        img_number = len(os.listdir(self.pm.images_path))

        if img_number != img_ann_number:
            raise MessageBoxException(f"The project {project_id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")

        self.import_project(overwrite=True)

    def _upload_annotation_results(self):
        if self.project_data.stage in [AnnotationStage.ANNOTATE, AnnotationStage.CORRECTION]:
            self._export_figures(figures_ann_path=self.pm.figures_ann_path)
            upload_file(self.project_data.uid, self.pm.figures_ann_path)
        elif self.project_data.stage is AnnotationStage.REVIEW:
            self._export_review(review_ann_path=self.pm.review_ann_path)
            upload_file(self.project_data.uid, self.pm.review_ann_path)

    def _remove_after_completion(self):
        """Don`t remove after first step of annotation in order to not download again before a correction stage"""
        if self.project_data.stage is not AnnotationStage.ANNOTATE:
            self.remove_project()
