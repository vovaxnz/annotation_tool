import os
from api_requests import get_project_ids, get_project_data
from exceptions import MessageBoxException
from gui import MainWindow
from import_annotations import import_project
from labeling import AnnotationStage, LabelingApp, get_labeling_app
from models import configure_database
from path_manager import PathManager
from file_transfer import FileTransferClient
from utils import open_json
from config import address
import tkinter as tk


class Application:
    def __init__(self, labeling_app: LabelingApp):
        self.main_window = MainWindow(app=labeling_app)

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        self.initialize_gui()


class ProjectSelector:
    def __init__(self, project_ids):
        self.project_ids = project_ids
        self.selected_project_id = None

    def select(self):
        self.root = tk.Tk()
        self.root.title("Select Project")

        if not self.project_ids:
            self._display_no_projects_message()
        else:
            self._create_project_buttons()

        self.root.mainloop()
        return self.selected_project_id

    def _create_project_buttons(self):
        label = tk.Label(self.root, text="Select project", font=('Helvetica', 16))
        label.pack(pady=10)
        for id in self.project_ids:
            button = tk.Button(self.root, text=str(id), command=lambda id=id: self._select_project(id))
            button.pack(pady=5, padx=10, fill=tk.X)

    def _display_no_projects_message(self):
        label = tk.Label(self.root, text="You don't have any projects", font=('Helvetica', 16))
        label.pack(pady=10)
        ok_button = tk.Button(self.root, text="OK", command=self.root.destroy)
        ok_button.pack(pady=5)

    def _select_project(self, id):
        self.selected_project_id = id
        self.root.destroy()


def start():
    available_project_ids = get_project_ids()
    ps = ProjectSelector(available_project_ids)
    project_id: int = ps.select()
    if project_id is None: 
        return

    annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path = get_project_data(project_id)
    pm = PathManager(project_id)
    ftc = FileTransferClient(address)
    print(annotation_stage, annotation_mode, img_path, figures_ann_path, review_ann_path)

    if not os.path.isfile(pm.figures_ann_path):
        ftc.download(
            local_path=pm.figures_ann_path, 
            remote_path=figures_ann_path,
        )
    if annotation_stage == AnnotationStage.CORRECTION or annotation_stage == AnnotationStage.REVIEW:
        ftc.download(
            local_path=pm.review_ann_path, 
            remote_path=review_ann_path,
            skip_unavailable=True
        )

    img_ann_number = len(open_json(pm.figures_ann_path)["images"])
    if os.path.isdir(pm.images_path):
        img_number = len(os.listdir(pm.images_path))
    else:
        img_number = 0

    if not os.path.isdir(pm.images_path) or img_number != img_ann_number:
        ftc.download(
            local_path=pm.images_path, 
            remote_path=img_path,
        )

    img_number = len(os.listdir(pm.images_path))
    if img_number != img_ann_number:
        raise MessageBoxException(f"The project {project_id} has a different number of images and annotations. Re-lauch application to download again or, if that doesn't help, ask to fix the project")

    configure_database(pm.db_path)

    import_project(
        figures_ann_path=pm.figures_ann_path,
        review_ann_path=pm.review_ann_path,
        img_dir=pm.images_path,
        overwrite=False,
    )
                
    labeling_app: LabelingApp = get_labeling_app(
        img_dir=pm.images_path, 
        export_path=pm.figures_ann_path,
        annotation_stage=annotation_stage, 
        annotation_mode=annotation_mode
    )
    app = Application(labeling_app=labeling_app)
    app.run()


if __name__ == "__main__":
    start()