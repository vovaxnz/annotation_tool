import os
from exceptions import MessageBoxException
from gui import MainWindow
from gui_utils import SettingsManager
from config import settings


class Application:
    def __init__(self):

        if settings.has_empty:
            SettingsManager()
            try:
                os.makedirs(settings.data_dir, exist_ok=True)
            except:
                data_dir = settings.data_dir
                settings.data["data_dir"] = None
                settings.save_settings()
                raise MessageBoxException(f"Unable to create data_dir in '{data_dir}'")
        self.main_window = MainWindow()

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        self.initialize_gui()


app = Application()
app.run()