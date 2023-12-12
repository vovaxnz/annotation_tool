import argparse
from gui import MainWindow
from interaction import UserInteraction, InputHandler
from labeling import LabelingApp


class Application:
    def __init__(self, img_dir: str, export_path: str):
        """
        Initialize the application.
        """
        self.labeling_app = LabelingApp(img_dir, export_path=export_path) 
        self.main_window = MainWindow(app=self.labeling_app)


    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        """ Run the application"""
        self.initialize_gui()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", type=str)
    parser.add_argument("--result", type=str)
    args = parser.parse_args()

    app = Application(img_dir=args.img, export_path=args.result)
    app.run()