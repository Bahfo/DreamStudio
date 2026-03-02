# Written By Bahaa Nofal 3/3/2026
# Backend API for DreamStudio - Run-Configuration
# Copyright 2026 - Licensed under DreamStudio's license

"""
Backend - Run - run_config.py:
A script written in Python to pass user arguments and script code to Runtime File Runner.
Since currently the the IDE focuses on the following languages, they would be hard-coded 
by default inside the following script:
    1. Python
    2. B-Sharp
    3. Lavender
    4. D-language
    5. C-language
"""

import subprocess

class RunFile:
    def __init__(self, code_to_run : str, arguments : list):
        self.code_to_run = code_to_run
        self.arguments = arguments

    def handle_arguments(self):
        """
        1. Language type: found by the extension of the script: The IDE will look for the
        script's extension, validates it, then pass it into the runtime runner.
        2. The current working directory: obtained via the project's directory itself and
        shall be passed directly instead of letting the user define it.
        3. Language Debugger Info: a tuple of data that is obtained to construct what to 
        pass to the runner.

        NOTE: ARGUMENTS ARE A BACKEND PROPERTY AND SHALL NOT BE UNCOVERED TO UI USAGE. THE
        STRICT USAGE REQUIRES THE LIST TO BE ANALYZED MANUALLY AS FOLLOWING:
         arg[0]: Language Type, arg[2] CWD, arg[3] Language Debugger Info

        Please follow that structure whenever you are calling this API.
        """

    def run_script(self):
        subprocess.run()