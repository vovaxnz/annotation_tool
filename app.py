import argparse
from gui import MainWindow
from import_annotations import import_project
from labeling import LabelingApp, get_labeling_app, AnnotationMode
from models import configure_database
from utils import open_json


class Application:
    def __init__(self, labeling_app: LabelingApp):
        self.main_window = MainWindow(app=labeling_app)

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        self.initialize_gui()



if __name__ == "__main__":

    img_dir = "data/img"

    configure_database("sqlite:///data/db.sqlite")
    import_project(
        data=open_json("data/ann.json"),
        img_dir=img_dir,
        overwrite=False,
    )
                
    labeling_app: LabelingApp = get_labeling_app(
        img_dir=img_dir, 
        export_path="data/exported.json", 
        review_mode=False, 
        annotation_mode=AnnotationMode.BBOXES
    )
    app = Application(labeling_app=labeling_app)
    app.run()

# def start(project_id: int):
#     # Get project directory name and path
#     ...
    
#     # if there is no directory, 

#         # Create a directory for project
#         ...

#         # get path to images and annotation via api
#         ...

#         # Download annotations via ssh
#         ...

#         # Download images via ssh (if they are not downloaded already)
#         ...

#         # Add annotations to the database if database is not yet created inside the project directory
#         ...

#         configure_database(database_path)
#         import_project(
#             data: List[Dict],
#             overwrite: bool = False,
#         )
#         # Add images from the directory to the database
#         img_names = sorted(os.listdir(img_dir))
#         for img_name in self.img_names:
#             img_object = LabeledImage.get(name=img_name)
#             if img_object is None:
#                 img_object = LabeledImage(name=img_name)
#                 img_object.save()
                
#     labeling_app: LabelingApp = get_labeling_app(
#         img_dir="/home/vova/code/annotation_tool/data/img", 
#         export_path="/home/vova/code/annotation_tool/data/exported.json", 
#         review_mode=False, 
#         annotation_mode=...
#     )
#     app = Application(labeling_app=labeling_app)
#     app.run()


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--n", type=int)
#     args = parser.parse_args()
#     start(project_id=args.n)