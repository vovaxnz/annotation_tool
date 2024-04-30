import os
import time
from api_requests import ProjectData, complete_task, get_project_data
from enums import AnnotationMode, AnnotationStage
from exceptions import MessageBoxException
from file_processing.file_transfer import FileTransferClient, download_file, upload_file
from file_processing.unzipping import ArchiveUnzipper
from gui_utils import  get_loading_window
from import_annotations import export_figures, export_review, import_project
from labeling import LabelingApp
from models import Value, configure_database
from path_manager import PathManager
from utils import open_json
from tkinter import messagebox
import shutil
import tkinter as tk



def download_project(project_data: ProjectData, root: tk.Tk):
    annotation_stage, annotation_mode, project_uid, project_id = project_data.stage, project_data.mode, project_data.uid, project_data.id
    pm = PathManager(project_data.id)

    loading_window = get_loading_window(text="Downloading annotations...", root=root)
    if not os.path.isfile(pm.meta_ann_path):
        download_file(
            uid=project_uid, 
            file_name=os.path.basename(pm.meta_ann_path), 
            save_path=pm.meta_ann_path, 
        )
    if not os.path.isfile(pm.figures_ann_path):
        download_file(
            uid=project_uid, 
            file_name=os.path.basename(pm.figures_ann_path), 
            save_path=pm.figures_ann_path, 
        )
    if annotation_stage is AnnotationStage.CORRECTION and not os.path.isfile(pm.review_ann_path):
        download_file(
            uid=project_uid, 
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
            uid=project_uid, 
            file_name=os.path.basename(pm.archive_path), 
            save_path=pm.archive_path, 
        )
        au = ArchiveUnzipper(window_title="Unzip progress", root=root)
        au.unzip(pm.archive_path, pm.images_path)
        if os.path.isfile(pm.archive_path):
            os.remove(pm.archive_path)

    img_number = len(os.listdir(pm.images_path))
    if img_number != img_ann_number:
        raise MessageBoxException(f"The project {project_id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")



def get_labeling_app(project_data: ProjectData, root: tk.Tk) -> LabelingApp:
    annotation_stage, annotation_mode, project_uid, project_id = project_data.stage, project_data.mode, project_data.uid, project_data.id
    pm = PathManager(project_data.id)
    
    download_project(project_data=project_data, root=root)

    loading_window = get_loading_window(text="Loading project...", root=root)
    configure_database(pm.db_path)
    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        meta_ann_path=pm.meta_ann_path,
        img_dir=pm.images_path,
        overwrite=False,
    )   
    labeling_app = LabelingApp(
        img_dir=pm.images_path,
        annotation_stage=annotation_stage,
        annotation_mode=annotation_mode,
        project_id=project_id,
        project_uid=project_uid
    )
    loading_window.destroy()
    return labeling_app
    

def complete_annotation(labeling_app: LabelingApp, root: tk.Tk):
    project_id = labeling_app.project_id
    pm = PathManager(project_id)
    if labeling_app.ready_for_export:
        loading_window = get_loading_window(text="Uploading completed project...", root=root)
        if labeling_app.annotation_stage in [AnnotationStage.ANNOTATE, AnnotationStage.CORRECTION]:
            export_figures(figures_ann_path=pm.figures_ann_path)
            upload_file(labeling_app.project_uid, pm.figures_ann_path)
        elif labeling_app.annotation_stage is AnnotationStage.REVIEW:
            export_review(review_ann_path=pm.review_ann_path)
            upload_file(labeling_app.project_uid, pm.review_ann_path)
        complete_task(project_id=project_id, duration_hours=labeling_app.duration_hours)
        Value.update_value("img_id", 0, overwrite=False)

        if labeling_app.annotation_stage == AnnotationStage.CORRECTION:
            if os.path.isdir(pm.project_path):
                shutil.rmtree(pm.project_path)
            if os.path.isfile(pm.db_local_path):
                os.remove(pm.db_local_path)
        
        messagebox.showinfo("Success", "Project completed")
        loading_window.destroy()
