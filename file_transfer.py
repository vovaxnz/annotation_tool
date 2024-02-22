import time
import tkinter as tk
from subprocess import Popen, PIPE, STDOUT
import os
import threading
from tkinter import ttk
from config import address

from exceptions import MessageBoxException


class FileTransferClient:
    def __init__(self):
        self.address = address
        self.error_line = ""
        self.last_line = ""
        self.rsync_process = None
        self.gui_close_event = threading.Event() # signal the GUI to close

    def setup_gui(self):
        def check_close():
            if self.gui_close_event.is_set():
                self.root.destroy()
            else:
                self.root.after(100, check_close)
        
        self.root = tk.Tk()
        self.root.title("File Transfer Progress")
        

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

        self.root.mainloop()

    def on_window_close(self):
        if self.rsync_process is not None:
            self.rsync_process.terminate()
        self.gui_close_event.set()

    def update_progress_bar(self):

        try:
            size, percent, speed, remaining_time = self.last_line.split()
            completed_part = float(percent.replace("%", ""))
        except Exception as e:
            self.root.after(100, self.update_progress_bar)
            return

        self.progress["value"] = completed_part
        self.percentage_label["text"] = f"Completed: {percent}"
        self.size_label["text"] = f"Transferred: {size}"
        self.speed_label["text"] = f"Speed: {speed}"
        self.remaining_time_label["text"] = f"Remaining: {remaining_time}"
        self.root.update_idletasks()
        self.root.after(100, self.update_progress_bar)

    def read_rsync_output(self):
        for line in iter(self.rsync_process.stdout.readline, ''):
            if "xfr" in line:
                continue
            self.last_line = line
            if "rsync" in line:
                self.error_line += line
            print(line)

    def run_command(self, command):
        self.rsync_process = Popen(command, stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, text=True)
        self.rsync_process.wait()
        self.gui_close_event.set()
        
    def execute_with_gui(self, command, ignore_errors: bool = False, show_progressbar = True):
        self.gui_close_event.clear()
        
        rsync_thread = threading.Thread(target=self.run_command, args=(command,), daemon=True)
        rsync_thread.start()
        time.sleep(2)
        read_output_thread = threading.Thread(target=self.read_rsync_output, daemon=True)
        read_output_thread.start()

        if show_progressbar:
            self.setup_gui()

        read_output_thread.join()
        rsync_thread.join()
        
        if self.rsync_process.returncode not in [0, 20]: # 20 - Received SIGUSR1 or SIGINT
            if ignore_errors:
                return
            raise MessageBoxException(f"File transfer failed with error: {self.error_line}")
        
    def download(self, local_path: str, remote_path: str, skip_unavailable: bool = False, show_progressbar: bool = True):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        command = ["rsync", "-azh", "--info=progress2", f"{self.address}:{remote_path}", local_path]
        self.execute_with_gui(command, ignore_errors=skip_unavailable, show_progressbar=show_progressbar)
        if not os.path.isfile(local_path) and not os.path.isdir(local_path):
            if skip_unavailable:
                return
            raise MessageBoxException(f"The object {remote_path} is not downloaded")

    def upload(self, remote_path: str, local_path: str, show_progressbar: bool = True):
        command = ["rsync", "-azh", "--info=progress2", local_path, f"{self.address}:{remote_path}"]
        self.execute_with_gui(command, show_progressbar=show_progressbar)


if __name__ == "__main__":
    ftc = FileTransferClient()
    ftc.download(remote_path="/media/data3/vv/supervisely_projects/dataset_tube-tube_keypoints_2024-02-13-19-17-20_fe854c08/img", local_path="/media/vova/data/viz/tem12")
    