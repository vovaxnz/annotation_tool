import argparse
from gui import MainWindow
from interaction import UserInteraction, InputHandler
from labeling import LabelingApp


class Application:
    def __init__(self, img_dir: str):
        """
        Initialize the application.
        """
        self.labeling_app = LabelingApp(img_dir) 
        self.user_interaction = UserInteraction(self.labeling_app)
        self.main_window = MainWindow(canvas=self.labeling_app.canvas, user_interaction=self.user_interaction)
        self.input_handler = InputHandler(self.user_interaction)

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        """ Run the application"""
        self.initialize_gui()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", type=str)
    args = parser.parse_args()

    app = Application(img_dir=args.img)
    app.run()