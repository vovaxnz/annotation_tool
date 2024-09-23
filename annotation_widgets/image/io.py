

from enum import Enum, auto
import json
import os
import shutil
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List

from annotation_widgets.image.filtering.logic import ImageFilteringLogic
from annotation_widgets.image.filtering.models import ClassificationImage
from annotation_widgets.image.labeling.bboxes.models import BBox
from annotation_widgets.image.labeling.keypoints.models import KeypointGroup
from annotation_widgets.image.labeling.logic import ImageLabelingLogic
from annotation_widgets.image.labeling.models import Label, LabeledImage, ReviewLabel
from annotation_widgets.image.labeling.segmentation.models import Mask
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from api_requests import complete_task, get_project_data
from db import configure_database
from enums import AnnotationMode, AnnotationStage, FigureType
from exceptions import MessageBoxException
from file_processing.file_transfer import FileTransferClient, download_file, upload_file
from file_processing.unzipping import ArchiveUnzipper
from gui_utils import get_loading_window
from models import ProjectData, Value
from path_manager import PathManager
from utils import check_correct_json, get_img_size, open_json, save_json





class AbstractAnnotationIO:
    """
    Importing, exporting data
    """
    #  TODO: Segregate logic into image labeling and image filtering

    def import_project( 
            self,
            project_data: ProjectData,
            overwrite: bool = False
        ): 


        pm = PathManager(project_data.id) 

        figures_ann_path=pm.figures_ann_path 
        review_ann_path=pm.review_ann_path 
        meta_ann_path=pm.meta_ann_path,
        img_dir=pm.images_path, 

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


    def _export_selected_frames(self, output_path: str):
        result = {"names": list(), "ids": list()}
        for limage in ClassificationImage.all(): 
            if limage.selected:
                if limage.name is not None:
                    result["names"].append(limage.name)
                elif limage.img_id is not None:
                    result["ids"].append(limage.img_id)
        save_json(result, output_path) 
    

    def overwrite_annotations(self, project_id, project_uid):

        annotation_stage, annotation_mode = get_project_data(project_uid)
        
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


        self.import_project(
            figures_ann_path=pm.figures_ann_path,
            review_ann_path=pm.review_ann_path,
            img_dir=pm.images_path,
            meta_ann_path=pm.meta_ann_path,
            overwrite=True,
        )


    def remove_project(self, project_id: int):
        pm = PathManager(project_id)
        if os.path.isdir(pm.project_path):
            shutil.rmtree(pm.project_path)
        if os.path.isfile(pm.db_local_path):
            os.remove(pm.db_local_path)


    def complete_annotation(self, annotation_logic: AbstractImageAnnotationLogic, root: tk.Tk):
        project_id = annotation_logic.project_id
        pm = PathManager(project_id)
        if annotation_logic.ready_for_export:
            loading_window = get_loading_window(text="Finishing project...", root=root)
            if annotation_logic.annotation_mode is AnnotationMode.FILTERING:
                self._export_selected_frames(output_path=pm.selected_frames_json_path)
                upload_file(annotation_logic.project_uid, pm.selected_frames_json_path)
            else:

                if annotation_logic.annotation_stage in [AnnotationStage.ANNOTATE, AnnotationStage.CORRECTION]:
                    self._export_figures(figures_ann_path=pm.figures_ann_path)
                    upload_file(annotation_logic.project_uid, pm.figures_ann_path)
                elif annotation_logic.annotation_stage is AnnotationStage.REVIEW:
                    self._export_review(review_ann_path=pm.review_ann_path)
                    upload_file(annotation_logic.project_uid, pm.review_ann_path)

            if os.path.isfile(pm.statistics_path):
                upload_file(annotation_logic.project_uid, pm.statistics_path)

            complete_task(project_uid=annotation_logic.project_uid, duration_hours=annotation_logic.duration_hours)
            Value.update_value("img_id", 0, overwrite=True)

            if annotation_logic.annotation_stage in [AnnotationStage.CORRECTION, AnnotationStage.REVIEW, AnnotationStage.FILTERING]:
                if os.path.isdir(pm.project_path):
                    shutil.rmtree(pm.project_path)
                if os.path.isfile(pm.db_local_path):
                    os.remove(pm.db_local_path)

            messagebox.showinfo("Success", "Project completed")
            loading_window.destroy()


    def _download_annotation_project(self, project_data: ProjectData, root: tk.Tk):
        pm = PathManager(project_data.id)

        loading_window = get_loading_window(text="Downloading annotations...", root=root)
        if not os.path.isfile(pm.meta_ann_path) or not check_correct_json(pm.meta_ann_path):
            download_file(
                uid=project_data.uid,
                file_name=os.path.basename(pm.meta_ann_path),
                save_path=pm.meta_ann_path,
            )
        if not os.path.isfile(pm.figures_ann_path) or not check_correct_json(pm.figures_ann_path):
            download_file(
                uid=project_data.uid,
                file_name=os.path.basename(pm.figures_ann_path),
                save_path=pm.figures_ann_path,
            )

        if project_data.stage is AnnotationStage.CORRECTION:
            if not check_correct_json(pm.review_ann_path):
                download_file(
                    uid=project_data.uid,
                    file_name=os.path.basename(pm.review_ann_path),
                    save_path=pm.review_ann_path,
                )

        img_ann_number = len(open_json(pm.figures_ann_path))
        if os.path.isdir(pm.images_path):
            img_number = len(os.listdir(pm.images_path))
        else:
            img_number = 0

        loading_window.destroy()
        if not os.path.isdir(pm.images_path) or img_number != img_ann_number:
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=project_data.uid,
                file_name=os.path.basename(pm.archive_path),
                save_path=pm.archive_path,
            )
            au = ArchiveUnzipper(window_title="Unzip progress", root=root)
            au.unzip(pm.archive_path, pm.images_path)
            if os.path.isfile(pm.archive_path):
                os.remove(pm.archive_path)

        img_number = len(os.listdir(pm.images_path))
        if img_number != img_ann_number:
            raise MessageBoxException(f"The project {project_data.id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")


    def _download_filtering_project(self, project_data: ProjectData, root: tk.Tk):
        pm = PathManager(project_data.id)
        if not os.path.isfile(pm.video_path):
            ftc = FileTransferClient(window_title="Downloading progress", root=root)
            ftc.download(
                uid=project_data.uid,
                file_name=os.path.basename(pm.video_path),
                save_path=pm.video_path,
            )


    def download_project(self, project_data: ProjectData, root: tk.Tk):
        if project_data.mode is AnnotationMode.FILTERING:
            self._download_filtering_project(project_data=project_data, root=root)
        else:
            self._download_annotation_project(project_data=project_data, root=root)


