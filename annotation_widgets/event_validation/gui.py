import tkinter as tk
from collections import OrderedDict
from tkinter import font, ttk

from .logic import EventValidationLogic


class EventValidationStatusBar(tk.Frame):
    def __init__(self, parent, logic: EventValidationLogic, **kw):
        super().__init__(parent, **kw)
        self.logic: EventValidationLogic = logic

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.item_id_label = tk.Label(self, bd=1)
        self.speed_label = tk.Label(self, bd=1)
        self.processed_label = tk.Label(self, bd=1)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.duration_label = tk.Label(self, bd=1)

        # Video frame info label
        self.frame_info_label = tk.Label(self, bd=1)

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

        self.item_id_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=3, sticky='ns')

        self.speed_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=5, sticky='ns')

        self.processed_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=7, sticky='ns')

        self.progress_bar.grid(row=0, column=8, sticky='ew', padx=15)
        self.columnconfigure(12, weight=1)  # Make progress bar expand
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=9, sticky='ns')

        self.duration_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=11, sticky='ns')

        # Video Frames info label (initially hidden)
        self.frame_info_label.grid(row=0, column=12, sticky='ew', padx=15)


    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130)))
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)

        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.item_id_label, self.speed_label, self.processed_label, self.duration_label,
                       self.frame_info_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data = self.logic.status_data

        # Update labels
        self.mode_label.config(text=f"Mode: Event Validation")
        self.item_id_label.config(text=f"Item id: {status_data.item_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")

        position_percent = int((status_data.item_id + 1) / status_data.number_of_items * 100)
        self.processed_label.config(text=f"Position: {position_percent} % ({status_data.item_id + 1}/{status_data.number_of_items})")
        self.progress_bar["value"] = position_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")

        if self.logic.video_mode:
            self.frame_info_label.config(text=f"Frame info: {self.logic.current_frame_number + 1} / {self.logic.number_of_frames}")
            self.frame_info_label.grid()
        else:
            self.frame_info_label.grid_remove()

        # Schedule the next update
        self.after(10, self.update_status)


class EventValidationSideBar(tk.Frame):
    def __init__(self, parent, logic, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.logic = logic
        self.parent = parent

        self.question_frames = []
        self.answer_vars = OrderedDict()
        self.answer_buttons = OrderedDict()

        self.logic.on_item_change(self.update_display)
        self.create_question_widgets()

        self.comment_label = tk.Label(self, text="Comment")
        self.comment_label.pack(anchor="w", padx=10, pady=2)
        self.comment_entry = tk.Text(self, wrap="word", height=2, width=40)
        self.comment_entry.pack(anchor="w", padx=10, pady=2)

        self.comment_entry.bind("<Escape>", self.save_comment)

        self.update_display()

    def update_display(self):
        self.update_question_widgets()
        self.update_comment_display()

    def update_comment_display(self):
        comment = self.logic.comment
        self.comment_entry.delete("1.0", tk.END)
        self.comment_entry.insert("1.0", comment)

    def save_comment(self, event=None):
        new_comment = self.comment_entry.get("1.0", tk.END).strip()
        self.logic.update_comment(new_comment)
        self.master.canvas_view.focus_set()

    def create_question_widgets(self):
        for question in self.logic.questions:
            frame = tk.Frame(self)
            frame.pack(anchor="w", padx=10, pady=2)
            tk.Label(frame, text=question).pack(anchor='w', pady=2)

            initial_value = self.logic.answers[question] if self.logic.answers is not None else ""
            answer_var = tk.StringVar(value=initial_value)
            self.answer_vars[question] = answer_var

            self.answer_buttons[question] = []

            for option in self.logic.questions_map[question].keys():  #  List of possible answers per question
                rb = tk.Radiobutton(
                    frame,
                    text=option,
                    variable=answer_var,
                    value=option,
                    command=lambda q=question, selected=option: self.save_answer(q, selected)
                )
                rb.pack(anchor='w', padx=5)
                self.answer_buttons[question].append(rb)
            self.apply_color(question, initial_value)

    def update_question_widgets(self):
        for question, answer_var in self.answer_vars.items():
            answer_var.set(self.logic.answers.get(question))
            selected_answer = self.logic.answers.get(question)
            self.apply_color(question, selected_answer)

    def save_answer(self, question, selected_answer):
        self.logic.update_answer(question, selected_answer)
        self.apply_color(question, selected_answer)

    def apply_color(self, question, selected_answer):

        if question in self.answer_buttons:
            default_bg = tk.Radiobutton.cget(self, "bg")
            for rb in self.answer_buttons[question]:
                rb.config(bg=default_bg)

            if selected_answer in self.logic.questions_map[question]:
                for rb in self.answer_buttons[question]:
                    if rb.cget("text") == selected_answer:
                        rb.config(bg=self.logic.questions_map[question][selected_answer])
