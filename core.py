"""
LOG Workspace for DreamStudio IDE
"""
import customtkinter as ctk
import dreamstudio_main
import json
import time
import os

from pathlib import Path
from project_types import *

#####################################################
# ERRORS
#####################################################
ERROR_NO_INITIAL_CONFIG = """Bootstrapping Failed:
No initial window was found, or not root directory was configured.\n
"""

ERROR_NO_INFO_FOUND = """Bootstrapping Failed:
No information for the project was given, terminated cretaing file,
terminated DreamStudio because project initialization information was
not given, or perhaps a further crash happened.\n

For further information, read the documentation.
"""

ERROR_NO_TYPE_GIVEN = """Bootstrapping Failed:
No given project type. DreamStudio terminated.\n
"""

UNEXPECTED_ERROR_OCCURED = """Project Creation Failed:
Unexpected error happened while creating project's folders. Terminated.\n
"""

class DreamStudioErrors(Exception):

    _ERRORS = {
        (1,1) : ERROR_NO_INITIAL_CONFIG,
        (1,2) : ERROR_NO_INFO_FOUND,
        (1,3) : ERROR_NO_TYPE_GIVEN,

        (2,1) : UNEXPECTED_ERROR_OCCURED
    }

    def __init__(self,
                 error_code : int,
                 error_description_code : int, 
                 root_cause : None,
                 window_cause: None):
        self.error_code = error_code
        self.error_desc_code = error_description_code

        message = self._ERRORS.get((error_code,
                                    error_description_code),
                                   "Unknown IDE Error")
        super.__init__(message)

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
    pass

class Analytics:
    pass
