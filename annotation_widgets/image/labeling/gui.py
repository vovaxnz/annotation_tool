from annotation_widgets.image.labeling.logic import ImageLabelingLogic


import tkinter as tk
from tkinter import font, ttk




class AnnotationStatusBar(tk.Frame): 
    def __init__(self, parent, logic: ImageLabelingLogic, **kw):
        super().__init__(parent, **kw)
        self.logic: ImageLabelingLogic = logic

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.class_label = tk.Label(self, bd=1)
        self.trash_label = tk.Label(self, bd=1)
        self.hidden_label = tk.Label(self, bd=1)
        self.blur_label = tk.Label(self, bd=1)
        self.item_id_label = tk.Label(self, bd=1)
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

        self.class_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=3, sticky='ns')

        self.trash_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep3 = ttk.Separator(self, orient='vertical')
        sep3.grid(row=0, column=5, sticky='ns')

        self.hidden_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep4 = ttk.Separator(self, orient='vertical')
        sep4.grid(row=0, column=7, sticky='ns')

        self.blur_label.grid(row=0, column=8, sticky='ew', padx=15)
        sep4 = ttk.Separator(self, orient='vertical')
        sep4.grid(row=0, column=9, sticky='ns')

        self.item_id_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=11, sticky='ns')

        self.speed_label.grid(row=0, column=12, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=13, sticky='ns')

        self.processed_label.grid(row=0, column=14, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=15, sticky='ns')

        self.progress_bar.grid(row=0, column=16, sticky='ew', padx=15)
        self.columnconfigure(16, weight=1)  # Make progress bar expand
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=17, sticky='ns')

        self.duration_label.grid(row=0, column=18, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=19, sticky='ns')

    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130)))
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)

        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.class_label, self.trash_label, self.hidden_label, self.blur_label,
                       self.item_id_label, self.speed_label, self.processed_label, self.duration_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data = self.logic.status_data

        # Update labels
        self.mode_label.config(text=f"Mode: {status_data.annotation_mode}: {status_data.annotation_stage}")
        self.class_label.config(text=f"Class: {status_data.selected_class}", bg=status_data.class_color)
        trash_text = "Trash" if status_data.is_trash else "not Trash"
        trash_color = "red" if status_data.is_trash else self.trash_label.master.cget('bg')
        self.trash_label.config(text=trash_text, bg=trash_color)

        hidden_text = "All Visible"
        hidden_text = "Review Hidden" if status_data.review_labels_hidden else hidden_text
        hidden_text = "All Hidden" if status_data.figures_hidden  else hidden_text

        hidden_color = self.hidden_label.master.cget('bg') if hidden_text == "All Visible" else "blue"
        self.hidden_label.config(text=hidden_text, bg=hidden_color)

        self.blur_label.config(text="Blur: ON" if status_data.blur_render else "Blur: OFF")

        self.item_id_label.config(text=f"Img id: {status_data.item_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")

        position_percent = int((status_data.item_id + 1) / status_data.number_of_items * 100)
        self.processed_label.config(text=f"Position: {position_percent} % ({status_data.item_id + 1}/{status_data.number_of_items})")
        self.progress_bar["value"] = position_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")

        # Schedule the next update
        self.after(10, self.update_status)