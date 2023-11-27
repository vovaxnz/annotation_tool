from tkinter import Tk
from gui import MainWindow
from core import CoordinateTransformer, ImageCanvas
from interaction import UserInteraction, InputHandler
from persistence import DatabaseManager


class Application:
    def __init__(self):
        """
        Initialize the application.
        """
        self.ct = CoordinateTransformer(
            homography_matrix_path="cam_data/5d3dca7b-7a0a-c71d-5986-12e2d039f619/homography_matrix_view_to_scheme.json",
            homography_matrix_reversed_path="cam_data/5d3dca7b-7a0a-c71d-5986-12e2d039f619/homography_matrix_scheme_to_view.json", 
        )
        self.canvas = ImageCanvas(width=1920, height=1080, ct=self.ct)  # Example size
        self.db_manager = DatabaseManager(db_path="db.sqlite")  # Replace with actual database path
        self.user_interaction = UserInteraction(self.canvas, db_manager=self.db_manager)
        self.main_window = MainWindow(canvas=self.canvas, user_interaction=self.user_interaction)
        self.input_handler = InputHandler(self.user_interaction)

        # Initialize GUI
        self.initialize_gui()

    def initialize_gui(self):
        """ Initialize the graphical user interface. """
        self.main_window.mainloop()

    def run(self):
        """ Run the application. """
        self.initialize_gui()

    def close(self):
        """ Close the application and clean up resources. """
        self.db_manager.close()

# The below lines will start the application when the script is run
if __name__ == "__main__":
    app = Application()
    try:
        app.run()
    finally:
        app.close()
