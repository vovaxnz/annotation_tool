from tkinter import Tk
from gui import MainWindow
from core import ImageCanvas, DatabaseManager
from interaction import UserInteraction, InputHandler
from persistence import SQLiteAdapter

class Application:
    def __init__(self):
        """
        Initialize the application.
        """
        self.root = Tk()
        self.main_window = MainWindow()
        self.canvas = ImageCanvas(width=800, height=600)  # Example size
        self.db_manager = DatabaseManager(db_path="path_to_your_database.db")  # Replace with actual database path
        self.sqlite_adapter = SQLiteAdapter(db_path="path_to_your_database.db")  # Replace with actual database path
        self.user_interaction = UserInteraction(self.canvas)
        self.input_handler = InputHandler(self.user_interaction)

        # Set up database connection
        self.setup_database()

        # Initialize GUI
        self.initialize_gui()

    def setup_database(self):
        """ Set up the database connection. """
        self.sqlite_adapter.connect()

    def initialize_gui(self):
        """ Initialize the graphical user interface. """
        self.main_window.mainloop()

    def run(self):
        """ Run the application. """
        self.initialize_gui()

    def close(self):
        """ Close the application and clean up resources. """
        self.sqlite_adapter.close()
        self.root.destroy()

# The below lines will start the application when the script is run
if __name__ == "__main__":
    app = Application()
    try:
        app.run()
    finally:
        app.close()
