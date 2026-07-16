# Function to get project type and info.

import os
import pathlib
import logging

logger = logging.getLogger(__name__)


# TODO: Implement this function
def get_project_info(project_dir):
    """
    Function to display info from .dreamstudio file.
    """
    _file_info = os.path.join(project_dir, ".dreamstudio")

    try:
        with open(_file_info, "r") as file:
            content = file.read()

    except Exception as e:
        logger.error("The .dreamstudio file cannot be found.")
