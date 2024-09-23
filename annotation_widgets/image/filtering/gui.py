from .logic import ImageFilteringLogic

import tkinter as tk
from tkinter import font, ttk


class FilteringStatusBar(tk.Frame):
    def __init__(self, parent, logic: ImageFilteringLogic, **kw):
        super().__init__(parent, **kw)
        self.logic: ImageFilteringLogic = logic

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.delay_label = tk.Label(self, bd=1)
        self.selected_label = tk.Label(self, bd=1)
        self.img_id_label = tk.Label(self, bd=1)
        self.speed_label = tk.Label(self, bd=1)
        self.processed_label = tk.Label(self, bd=1)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.duration_label = tk.Label(self, bd=1)

        # Initialize labels and separators
        self.initialize_labels_and_separators()

        # Bind the resize event
        self.bind("<Configure>", self.on_resize)

        self.update_status()

    def initialize_labels_and_separators(self):
        # Place each label and the progress bar in the grid
        self.mode_label.grid(row=0, column=0, sticky='ew', padx=15)
        sep1 = ttk.Separator(self, orient='vertical')
        sep1.grid(row=0, column=1, sticky='ns')

        self.delay_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=3, sticky='ns')

        self.selected_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=5, sticky='ns')

        self.img_id_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=7, sticky='ns')

        self.speed_label.grid(row=0, column=8, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=9, sticky='ns')

        self.processed_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=11, sticky='ns')

        self.progress_bar.grid(row=0, column=12, sticky='ew', padx=15)
        self.columnconfigure(12, weight=1)  # Make progress bar expand
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=13, sticky='ns')

        self.duration_label.grid(row=0, column=14, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=15, sticky='ns')

    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130)))
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)

        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.delay_label, self.selected_label, self.img_id_label, self.speed_label, self.processed_label, self.duration_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data = self.logic.status_data

        # Update labels
        self.mode_label.config(text=f"Mode: Filtering")

        self.delay_label.config(text=f"Delay: {status_data.delay}")

        selected_text = "Selected: TRUE" if status_data.selected else "Selected: FALSE"
        selected_color = "lime" if status_data.selected else "gray"
        self.selected_label.config(text=selected_text, bg=selected_color)

        self.img_id_label.config(text=f"Img id: {status_data.img_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")

        position_percent = int((status_data.img_id + 1) / status_data.number_of_images * 100)
        self.processed_label.config(text=f"Position: {position_percent} % ({status_data.img_id + 1}/{status_data.number_of_images})")
        self.progress_bar["value"] = position_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")

        # Schedule the next update
        self.after(10, self.update_status)