from gui import MainWindow
from trash.app import Application

class Application:
    def __init__(self):
        self.main_window = MainWindow()

    def initialize_gui(self):
        self.main_window.mainloop()

    def run(self):
        self.initialize_gui()


app = Application()
app.run()