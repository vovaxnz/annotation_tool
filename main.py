import os
import shutil
import sys
import threading
from typing import Callable, List
from annotation_widgets.factory import get_io, get_widget

import tkinter as tk
from annotation_widgets.models import CheckResult
from api_requests import get_projects_data
from enums import AnnotationStage
from exceptions import handle_exception
from annotation_widgets.widget import AbstractAnnotationWidget
from gui_utils import IdForm, MessageBox, ProjectSelector, SettingsManager, get_loading_window, show_html_window

from tkinter import messagebox
from models import ProjectData
from config import templates_path
from config import settings

import subprocess


from path_manager import BasePathManager, get_local_projects_data
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

        # AbstractAnnotationWidget cell, make it expandable
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1) 


        self.annotation_widget: AbstractAnnotationWidget = None
        self.status_bar = None
        
        # Create a menu bar
        self.menu_bar = tk.Menu(self)

        # Create a menu and add it to the menu bar
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)

        self.menu_bar.add_cascade(label="Project", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.update_menu(initial=True)
        
        # Attach the menu bar to the window
        self.config(menu=self.menu_bar)
        
        # Remove completed projects
        thread = threading.Thread(target=self.remove_completed_projects)
        thread.daemon = True 
        thread.start()

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
            self.file_menu.add_command(label="Go to ID", command=self.go_to_id) 
            self.file_menu.add_command(label="Complete the project", command=self.complete_project)

    def set_annotation_widget(self, project_data: ProjectData): 
        self.annotation_widget: AbstractAnnotationWidget = get_widget(root=self.container, project_data=project_data)
        self.update_menu()
        self.annotation_widget.add_menu_items(self) 

    def remove_annotation_widget(self):
        if self.annotation_widget is not None:
            self.annotation_widget.close()
            self.annotation_widget = None
            self.update_menu(initial=True)

    def open_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)

        try:
            projects_data = get_projects_data()
        except:
            messagebox.showinfo("Error", "Unable to get projects from a web service. You`ll be shown only already downloaded projects.")
            projects_data = get_local_projects_data()
    
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            if self.annotation_widget is not None:
                self.remove_annotation_widget()
            self.set_annotation_widget(project_data)
            self.title(f"Project {project_data.id}")

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
            io = get_io(project_data)
            io.download_project(root=self)


    def remove_project(self):
        projects_data = get_local_projects_data(with_broken_projects=True)
        ps = ProjectSelector(projects_data, root=self, title="Select project to remove", description="Select project to remove\nfrom your computer. \nThis will remove project files \nfrom your computer, \nbut not from eg-ml")
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            pm = BasePathManager(project_id=project_data.id)
            if os.path.isdir(pm.project_path):
                shutil.rmtree(pm.project_path)
            if self.annotation_widget is not None:
                if self.annotation_widget.project_id == project_data.id:
                    self.remove_annotation_widget()
                    self.title(f"Annotation tool")
            messagebox.showinfo("Project removed", f"Project {project_data.id} removed")

    def complete_project(self):
        agree = messagebox.askokcancel("Project Completion", "Are you sure you want to complete the project?")
        if agree:
            check_result: CheckResult = self.annotation_widget.check_before_completion()
            if not check_result.ready_to_complete:
                messagebox.showerror(title="Project can not be completed", message=check_result.message)
            else:
                if check_url_rechable(settings.api_url):
                    self.annotation_widget.complete_annotation(root=self)
                    self.remove_annotation_widget()
                    self.title(f"Annotation tool")
                else:
                    messagebox.showinfo("Error", "Unable to reach a web service. Project is not completed. You can complete it later after resume access to the web service.")

    def remove_completed_projects(self):
        local_projects_data = get_local_projects_data(with_broken_projects=True)
        if len(local_projects_data) > 0:
            projects_data: List[ProjectData] = get_projects_data(only_assigned_to_user=False)
            active_project_uids = [project.uid for project in projects_data]
            local_projects_to_remove: List[ProjectData] = list()
            for local_project in local_projects_data:
                if local_project.uid not in active_project_uids:
                    local_projects_to_remove.append(local_project)
            for project_data in local_projects_to_remove:
                pm = BasePathManager(project_id=project_data.id)
                if os.path.isdir(pm.project_path):
                    shutil.rmtree(pm.project_path)


    def open_settings(self):
        SettingsManager(root=self, at_exit=lambda : self.annotation_widget.schedule_update() if self.annotation_widget is not None else None)
        
    def go_to_id(self):
        form = IdForm(root=self, max_id=self.annotation_widget.items_number) 
        element_id = form.get_id()
        if element_id is not None:
            self.annotation_widget.go_to_id(element_id - 1)

    def on_window_close(self):
        if self.annotation_widget is not None:
            self.annotation_widget.close()
        self.destroy()

    def update_tool(self):
        """Pulls git repository"""
        agree = messagebox.askokcancel("Tool update", "Are you sure you want to update annotation tool?")
        if agree:
            root_path = os.path.dirname(os.path.abspath(__file__))

            result = subprocess.run(["git", "-C", root_path, "pull"], capture_output=True, text=True)

            message = f"{result.stdout}\n{result.stderr}"
            if "Updating" in message:
                message= message + "\n\nSuccess\n\nRe-open the tool for the changes to take effect"

            MessageBox(message)

    def show_hotkeys(self):
        template_path = os.path.join(templates_path, "hotkeys.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        show_html_window(self, title="Hotkeys", html_content=html_content)

    def show_how(self):
        template_path = os.path.join(templates_path, "how.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        show_html_window(self, title="How to use this tool?", html_content=html_content)

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        handle_exception(exc_type, exc_value, exc_traceback)
