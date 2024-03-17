import os
import time
from api_requests import complete_task, get_project_ids, get_project_data
from config import AnnotationStage
from exceptions import MessageBoxException
from gui import MainWindow, ProjectSelector, get_loading_window
from import_annotations import export_figures, export_review, import_project
from labeling_app.factory import get_labeling_app
from labeling_app.labeling import LabelingApp
from models import Value, configure_database
from path_manager import PathManager
from file_transfer import FileTransferClient
from utils import open_json
from tkinter import messagebox


class Application:
    def __init__(self, labeling_app: LabelingApp):
        self.main_window = MainWindow(app=labeling_app)

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        self.initialize_gui()


def start():
    loading_window = get_loading_window(text="Getting your active projects...")
    available_project_ids = get_project_ids()
    loading_window.destroy()
    ps = ProjectSelector(available_project_ids)
    project_id: int = ps.select()
    if project_id is None: 
        return

    loading_window = get_loading_window(text="Downloading annotations...")
    annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path = get_project_data(project_id)
    pm = PathManager(project_id)
    ftc = FileTransferClient()
    print(annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path)

    if not os.path.isfile(pm.figures_ann_path):
        ftc.download(
            local_path=pm.figures_ann_path, 
            remote_path=figures_ann_path,
            show_progressbar=False
        )
    if annotation_stage in [AnnotationStage.CORRECTION, AnnotationStage.REVIEW] and not os.path.isfile(pm.review_ann_path):
        ftc.download(
            local_path=pm.review_ann_path, 
            remote_path=review_ann_path,
            show_progressbar=False
        )

    img_ann_number = len(open_json(pm.figures_ann_path)["images"])
    if os.path.isdir(pm.images_path):
        img_number = len(os.listdir(pm.images_path))
    else:
        img_number = 0

    loading_window.destroy()
    if not os.path.isdir(pm.images_path) or img_number != img_ann_number:
        ftc.download(
            local_path=pm.images_path, 
            remote_path=img_path,
        )
    img_number = len(os.listdir(pm.images_path))
    if img_number != img_ann_number:
        raise MessageBoxException(f"The project {project_id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")

    loading_window = get_loading_window(text="Loading project...")
    configure_database(pm.db_path)
    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        img_dir=pm.images_path,
        overwrite=False,
    )           
    labeling_app: LabelingApp = get_labeling_app(
        img_dir=pm.images_path, 
        annotation_stage=annotation_stage, 
        annotation_mode=annotation_mode,
        project_id=project_id
    )
    loading_window.destroy()
    app = Application(labeling_app=labeling_app)
    app.run()

    if labeling_app.ready_for_export:

        loading_window = get_loading_window(text="Uploading completed project...")

        if annotation_stage in [AnnotationStage.ANNOTATE, AnnotationStage.CORRECTION]:
            export_figures(figures_ann_path=pm.figures_ann_path)
            ftc.upload(
                local_path=pm.figures_ann_path, 
                remote_path=figures_ann_path,
                show_progressbar=False
            )
        elif annotation_stage is AnnotationStage.REVIEW:
            export_review(review_ann_path=pm.review_ann_path)
            ftc.upload(
                local_path=pm.review_ann_path, 
                remote_path=review_ann_path,
                show_progressbar=False
            )
        complete_task(project_id=project_id, duration_hours=labeling_app.duration_hours)
        Value.update_value("img_id", 0, overwrite=False)
        messagebox.showinfo("Success", "Task completed")
        loading_window.destroy()



if __name__ == "__main__":
    start()