import os
import sys
import time
from typing import Callable, List, Tuple
from annotation_widgets.image.filtering.gui import FilteringStatusBar
from annotation_widgets.image.labeling.gui import AnnotationStatusBar
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from api_requests import get_projects_data
from enums import AnnotationMode
from exceptions import handle_exception
from annotation_widgets.widget import download_project
from gui_utils import ImageIdForm, MessageBox, ProjectSelector, SettingsManager, get_loading_window
from annotation_widgets.widget import complete_annotation, get_widget, overwrite_annotations, remove_project
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
from jinja2 import Environment, FileSystemLoader
import tkinterweb
from models import ProjectData
from annotation_widgets.image.labeling.models import Label
from config import templates_path
from config import settings

import subprocess

from pynput.keyboard import Listener

from path_manager import get_local_projects_data
from utils import check_url_rechable
from tkinter import PhotoImage


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        icon = PhotoImage(file=os.path.join(os.path.dirname(os.path.realpath(__file__)), "icon.png"))
        self.iconphoto(True, icon)
        self.title(f"Annotation tool")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        # Create a container frame for better layout control
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)

        # TODO: Status bar should be a part of AbstractAnnotationWidget and we should use a a single cell
        # Use grid layout within the container
        self.container.grid_rowconfigure(0, weight=1)  # AbstractAnnotationWidget row, make it expandable
        self.container.grid_columnconfigure(0, weight=1)  # Single column for simplicity
        self.container.grid_rowconfigure(1, weight=0, minsize=40) # container for StatusBar

        self.annotation_widget = None
        self.status_bar = None
        
        # Create a menu bar
        self.menu_bar = tk.Menu(self)

        # Create a menu and add it to the menu bar
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)

        self.menu_bar.add_cascade(label="Project", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.update_menu(initial=True)
        
        # Check if running on macOS
        if sys.platform == "darwin":
            # For macOS, setting the menu on the root should automatically handle it,
            # but if it doesn't appear in the top bar, we force it here
            self.tk.call('tk::mac::standardAboutPanel')

        # Attach the menu bar to the window
        self.config(menu=self.menu_bar)
        
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

    def update_menu(self, initial=False):
        # Clear existing menu items
        self.file_menu.delete(0, 'end')
        self.help_menu.delete(0, 'end')

        # Add basic menu items
        self.file_menu.add_command(label="Open", command=self.open_project)
        self.file_menu.add_command(label="Download", command=self.download_project)
        self.file_menu.add_command(label="Settings", command=self.open_settings)
        self.file_menu.add_command(label="Update tool", command=self.update_tool)
        self.file_menu.add_command(label="Remove project by ID", command=self.remove_project)
        self.help_menu.add_command(label="How to use this tool?", command=self.show_how)
        self.help_menu.add_command(label="Hotkeys", command=self.show_hotkeys)
        
        # Add dynamic items only after initial setup
        if not initial:
            self.file_menu.add_command(label="Go to image", command=self.go_to_image_id) 
            self.file_menu.add_command(label="Complete the project", command=self.complete_project)
            if self.annotation_widget.logic.annotation_mode is AnnotationMode.FILTERING:
                return
            self.file_menu.add_command(label="Download and overwrite annotations", command=self.annotation_widget.overwrite_annotations)
            self.help_menu.add_command(label="Classes", command=self.show_classes)
            self.help_menu.add_command(label="Review Labels", command=self.show_review_labels)

    def set_annotation_widget(self, annotation_logic: AbstractImageAnnotationLogic): 
        # TODO: Use AnnotationWidgetFactory to get an AnnotationWidget
        self.annotation_widget = AbstractAnnotationWidget(self.container, root=self, logic=annotation_logic)
        self.annotation_widget.grid(row=0, column=0, sticky="nsew")  # Make AbstractAnnotationWidget expand in all directions
        self.annotation_widget.set_close_callback(self.destroy)

        if annotation_logic.annotation_mode is AnnotationMode.FILTERING:
            self.status_bar = FilteringStatusBar(self.container, annotation_logic)
        else:
            self.status_bar = AnnotationStatusBar(self.container, annotation_logic)

        self.status_bar.grid(row=1, column=0, sticky='ew')  # StatusBar at the bottom, expanding horizontally

    def remove_annotation_widget(self):
        if self.annotation_widget is not None:
            self.annotation_widget.logic.save_image()
            self.annotation_widget.logic.save_state()
            self.annotation_widget.destroy()
            self.annotation_widget = None

        if self.status_bar is not None:
            self.status_bar.destroy()
            self.status_bar = None 

    def open_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)
        
        try:
            projects_data = get_projects_data()
        except:
            messagebox.showinfo("Error", "Unable to reach a web service. You`ll be shown only already downloaded projects.")
            projects_data = get_local_projects_data()
    
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            if self.annotation_widget is not None:
                self.remove_annotation_widget()
            annotation_logic = get_widget(project_data, root=self) # TODO: Create a widget here using an AbstractWidgetFactory
            self.set_annotation_widget(annotation_logic)
            self.title(f"Project {project_data.id}")
            self.update_menu()

    def download_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)

        try:
            projects_data = get_projects_data()
        except:
            messagebox.showinfo("Error", "Unable to reach a web service. You can not download a project now.")
            return
        
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            download_project(project_data=project_data, root=self)


    def remove_project(self):
        projects_data = get_local_projects_data()
        ps = ProjectSelector(projects_data, root=self, title="Select project to remove", description="Select project to remove\nfrom your computer. \nThis will remove project files \nfrom your computer, \nbut not from eg-ml")
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            remove_project(project_id=project_data.id)
            messagebox.showinfo("Project removed", f"Project {project_data.id} removed")
            if self.annotation_widget is not None:
                if self.annotation_widget.logic.project_id == project_data.id:
                    self.remove_annotation_widget()
                    self.update_menu(initial=True)
                    self.title(f"Annotation tool")

    def complete_project(self):
        agree = messagebox.askokcancel("Project Completion", "Are you sure you want to complete the project?")
        if agree:
            self.annotation_widget.logic.save_image()
            self.annotation_widget.logic.save_state()
            self.annotation_widget.logic.ready_for_export = True
            if check_url_rechable(settings.api_url):
                # TODO: self.annotation_widget.complete_annotation()
                complete_annotation(self.annotation_widget.logic, root=self)
            else:
                messagebox.showinfo("Error", "Unable to reach a web service. Project is not completed. You can complete it later after resume access to the web service.")
        self.remove_annotation_widget()
        self.update_menu(initial=True)
        self.title(f"Annotation tool")

    
    def update_tool(self):

        agree = messagebox.askokcancel("Tool update", "Are you sure you want to update annotation tool?")
        if agree:
            root_path = os.path.dirname(os.path.abspath(__file__))
            print(root_path)

            result = subprocess.run(["git", "-C", root_path, "pull"], capture_output=True, text=True)

            message = f"{result.stdout}\n{result.stderr}"
            if "Updating" in message:
                message= message + "\n\nSuccess\n\nRe-open the tool for the changes to take effect"

            MessageBox(message)

    def set_update_annotation_widget(self):
        if self.annotation_widget is not None:
            self.annotation_widget.update_frame=True

    def open_settings(self):
        SettingsManager(root=self, at_exit=lambda : self.set_update_annotation_widget())
        
    def go_to_image_id(self):
        form = ImageIdForm(root=self, max_id=self.annotation_widget.logic.img_number)
        img_id = form.get_image_id()
        if img_id is not None:
            self.annotation_widget.logic.go_to_image_by_id(img_id - 1)
            self.annotation_widget.update_frame = True

    def on_window_close(self):
        if self.annotation_widget is not None:
            self.annotation_widget.logic.save_image()
            self.annotation_widget.logic.save_state()
        self.destroy()

    def _show_html_window(self, title, html_content):
        window = tk.Toplevel(self)
        window.title(title)

        html_frame = tkinterweb.HtmlFrame(window, messages_enabled=False)
        html_frame.load_html(html_content)
        html_frame.pack(fill="both", expand=True)

        window.update_idletasks()
        window.update()

    def show_hotkeys(self):
        template_path = os.path.join(templates_path, "hotkeys.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        self._show_html_window(title="Hotkeys", html_content=html_content)

    def show_how(self):
        template_path = os.path.join(templates_path, "how.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        self._show_html_window(title="How to use this tool?", html_content=html_content)

    def show_classes(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_figure_labels()
        ]
        
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        self._show_html_window(title="Classes", html_content=html_content)

    def show_review_labels(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_review_labels()
        ]
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        self._show_html_window(title="Classes", html_content=html_content)

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        handle_exception(exc_type, exc_value, exc_traceback)



