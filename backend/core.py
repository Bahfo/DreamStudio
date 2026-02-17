"""
LOG Workspace for DreamStudio IDE
"""
import customtkinter as ctk

import json
import time
import os

from pathlib import Path
from bridge_handler import *
from threading import Thread
from tkinter import messagebox
from queue import Queue, Empty
from project_types import *
from watchdog.observers import Observer

class Workspace:
    """
    Responsible for initializing the workspace where the project will be created at.
    Bootstraps the entire project from scratch given the directory and name specified
    by the user, as well as the project type. 
    Creates a JSON file and a .gitignore file by default.
    """
    def __init__(self,
                 root_window : ctk.CTk,
                 root_directory : str,
                 configuration_json : json.__file__,
                 workspace_directory : str, 
                 project_langauge : str,
                 project_type : str, 
                 project_name : str):

        self.root_window = root_window
        self.root_directory = root_directory
        self.configuration_json = configuration_json
        self.project_type = project_type
        self.project_language = project_langauge
        self.project_name = project_name
        self.workspace_directory = Path(workspace_directory) / self.project_name

        self.bootstrap()
        self.return_directory_for_tree()
        self.check_root_directory()

    def _match_project_with_type(self):
        match self.project_type:
            case "console":
                return PYTHON_CONSOLE_APP
            case _:
                raise DreamStudioErrors(1,3)

    def bootstrap(self):
        """
        Bootstraps and initializes a project from scratch based on user's defined project type.
        Should take in consideration all user requirements (name, path, etc.) and resolve into
        a working project structure.
        NOTE: Projects are configured using the config.json file. Any changes to some fields in 
        this file should be resolved and corrected immediately by the core.
        """
        if (self.configuration_json is None):
            raise DreamStudioErrors(1,1)
        
        if (self.workspace_directory is None
            or self.project_type is None
            or self.project_language is None
            or self.project_name is None):
            raise DreamStudioErrors(1,2)
        
        # Creating a project directory with the specified-checked information:
        try:
            self.JSON_FILE_DIRECTORY = self.workspace_directory / f"{self.project_name}/config.json"
            self.gitignore_file = self.workspace_directory / ".gitignore"
            self.json_data = self._match_project_with_type()

            for subfolder in ["src", "imports", "tests", "others"]:
                (self.workspace_directory / subfolder).mkdir(exist_ok=True)

            with self.JSON_FILE_DIRECTORY.open('w', encoding='utf-8') as file:
                json.dump(self.json_data, file, indent=4)

            with self.gitignore_file.open('w', encoding='utf-8') as git_file:
                git_file.write("")

        except Exception as e:
            raise DreamStudioErrors(2,1) from e
        
    def return_directory_for_tree(self):
        return self.workspace_directory

    def check_root_directory(self):
        if self.root_directory is None:
            self.root_directory = os.getcwd()

class WatchDog:
    def __init__(self, gui_callback=None):
        """
        gui_callback: function that receives stable events (for GUI updates)
        """
        self.event_queue = Queue()
        self.debouncer = Debouncer(delay=0.2, output_queue=self.event_queue)
        self.handler = WatchdogBridgeHandler(self.debouncer)
        self.observer = Observer()
        self.gui_callback = gui_callback  # optional GUI hook
        self.worker_thread = None
        self.loop_thread = None

    # Start background threads
    def start_tracker(self, project_path):
        self.observer.schedule(self.handler, path=project_path, recursive=True)
        self.observer.start()
        print(f"Tracker started on: {project_path}")

        # Debouncer worker
        self.worker_thread = Thread(target=self.debouncer_worker, daemon=True)
        self.worker_thread.start()

        # Event loop thread
        self.loop_thread = Thread(target=self.looping, daemon=True)
        self.loop_thread.start()

    def debouncer_worker(self):
        while True:
            self.debouncer.poll()
            time.sleep(0.05)

    def looping(self):
        while True:
            stable_event = self.event_queue.get()
            # Call C engine or GUI callback
            if self.gui_callback:
                self.gui_callback(stable_event)
            else:
                print(f"Stable event: {stable_event}")

    # Stop observer and threads (call on GUI exit)
    def stop_tracker(self):
        self.observer.stop()
        self.observer.join()
        print("Tracker stopped")

class Analytics:
    pass
