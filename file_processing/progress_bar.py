
import time
import tkinter as tk
import threading
from tkinter import ttk


class ProcessingProgressBar:
    def __init__(self, window_title: str = None, root: tk.Tk = None):
        if window_title is None:
            window_title = "Loading"

        if root is not None:
            self.root = tk.Toplevel(root)
        else:
            self.root = tk.Tk()
        
        self.root.title(window_title)

        self.gui_close_event = threading.Event()
        self.terminate_processing = threading.Event()
        self.processing_complete = threading.Event()

        self.processed_percent = 0
        self.processed_gb = 0
        self.speed = 0
        self.remaining_time = 0

        self.setup_gui()
        self.start_processing_thread()

    def setup_gui(self):
        def check_close():
            if self.gui_close_event.is_set():
                self.root.destroy()
            else:
                self.root.after(100, check_close)

        window_width, window_height = 450, 100
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{int(x)}+{int(y)}')

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.percentage_label = tk.Label(self.root, text="Starting...")
        self.size_label = tk.Label(self.root, text="0M")
        self.speed_label = tk.Label(self.root, text="0MB/s")
        self.remaining_time_label = tk.Label(self.root, text="Remaining time ...")

        self.root.grid_columnconfigure((0, 1, 2), weight=1)
        self.root.grid_rowconfigure((0, 1, 2), weight=1)

        self.progress.grid(row=0, column=0, columnspan=3, pady=20, padx=10, sticky="nsew")
        self.percentage_label.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.size_label.grid(row=2, column=0, sticky="nsew")
        self.speed_label.grid(row=2, column=1, sticky="nsew")
        self.remaining_time_label.grid(row=2, column=2, sticky="nsew")

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.root.after(100, self.update_progress_bar)
        self.root.after(100, check_close)

    def start_processing_thread(self):
        self.processing_thread = threading.Thread(target=self.process_data, daemon=True)
        self.processing_thread.start()

    def process_data(self):
        try:
            total_steps = 100
            for i in range(total_steps + 1):
                if self.terminate_processing.is_set():
                    break
                time.sleep(0.1)
                self.processed_percent = i
                self.processed_gb = i * 0.01
                self.speed = 5 + (i * 0.1)
                self.remaining_time = (total_steps - i) * 0.1
            self.processing_complete.set()
        except Exception as e:
            print(f"Processing error: {e}")
            self.processing_complete.set()

    def on_window_close(self):
        self.terminate_processing.set()
        self.gui_close_event.set()

    def update_progress_bar(self):
        self.progress["value"] = self.processed_percent
        self.percentage_label["text"] = f"Completed: {self.processed_percent:.2f} %"

        if self.processed_gb < 1:
            size_mb = self.processed_gb * 1024
            self.size_label["text"] = f"Completed: {size_mb:.2f} MB"
        else:
            self.size_label["text"] = f"Completed: {self.processed_gb:.2f} GB"

        self.speed_label["text"] = f"Speed: {self.speed:.2f} MB/S"

        hours, remainder = divmod(int(self.remaining_time), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.remaining_time_label["text"] = f"Remaining: {hours:02}:{minutes:02}:{seconds:02}"

        if self.processing_complete.is_set():
            self.gui_close_event.set()

        self.root.update_idletasks()
        if not self.gui_close_event.is_set():
            self.root.after(100, self.update_progress_bar)


