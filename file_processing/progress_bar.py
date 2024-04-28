
import tkinter as tk
import threading
from tkinter import ttk


class ProcessingProgressBar:
    def __init__(self, window_title: str, root: tk.Tk):
        self.gui_close_event = threading.Event() # signal the GUI to close
        self.terminate_processing = False  # Flag to signal the processing thread to stop
        self.processing_complete = False  # Flag to signal that the processing has completed
        self.window_title: str = window_title

        self.processed_percent = 0
        self.processed_gb = 0
        self.speed = 0
        self.remaining_time = 0
        self.processing_complete = False

        self.setup_gui(root=root)

    def setup_gui(self, root: tk.Tk):
        def check_close():
            if self.gui_close_event.is_set():
                self.root.destroy()
            else:
                self.root.after(100, check_close)
        
        self.root = tk.Toplevel(root)
        self.root.title(self.window_title)
        
        # Set window size
        window_width = 450
        window_height = 100

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate x and y coordinates for the Tk root window
        x = (screen_width/2) - (window_width/2)
        y = (screen_height/2) - (window_height/2)

        # Set the dimensions of the window and where it is placed
        self.root.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.percentage_label = tk.Label(self.root, text="Starting...")
        self.size_label = tk.Label(self.root, text="0M")
        self.speed_label = tk.Label(self.root, text="0MB/s")
        self.remaining_time_label = tk.Label(self.root, text="Remaining time ...")

        # Configure the grid to be responsive
        self.root.grid_columnconfigure(0, weight=1)  # Make the column expandable
        self.root.grid_rowconfigure(0, weight=1)  # Make the first row expandable
        self.root.grid_rowconfigure(1, weight=1)  # Make the second row expandable
        self.root.grid_rowconfigure(2, weight=1)  # Make the third row expandable
        
        # Configure the grid to be responsive
        self.root.grid_columnconfigure(0, weight=1)  # Make the first column expandable
        self.root.grid_columnconfigure(1, weight=1)  # Make the second column expandable
        self.root.grid_columnconfigure(2, weight=1)  # Make the third column expandable

        # Adjust the progress bar
        self.progress.grid(row=0, column=0, columnspan=3, pady=20, padx=10, sticky="nsew")

        # Adjust the labels with 'sticky="nsew"' to center them
        self.percentage_label.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.size_label.grid(row=2, column=0, sticky="nsew")
        self.speed_label.grid(row=2, column=1, sticky="nsew")
        self.remaining_time_label.grid(row=2, column=2, sticky="nsew")

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.root.after(100, self.update_progress_bar)
        self.root.after(100, check_close)


    def on_window_close(self):
        self.terminate_processing = True  # Signal the download thread to stop
        self.gui_close_event.set()  # Signal GUI close event
        if self.root is not None:
            self.root.destroy()

    def update_progress_bar(self):
        self.progress["value"] = self.processed_percent
        self.percentage_label["text"] = f"Completed: {self.processed_percent:.2f} %"
        
        if self.processed_gb < 1:
            size_mb = self.processed_gb * 1024  # Convert GB to MB
            self.size_label["text"] = f"Completed: {size_mb:.2f} MB"
        else:
            self.size_label["text"] = f"Completed: {self.processed_gb:.2f} GB"
        
        self.speed_label["text"] = f"Speed: {self.speed:.2f} MB/S"
        
        hours, remainder = divmod(int(self.remaining_time), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.remaining_time_label["text"] = f"Remaining: {hours:02}:{minutes:02}:{seconds:02}"
        
        if self.processing_complete:
            self.root.after(1000, self.root.destroy)  # Delay slightly before closing

        self.root.update_idletasks()
        if not self.processing_complete:
            self.root.after(100, self.update_progress_bar)  # Continue updating if not complete

