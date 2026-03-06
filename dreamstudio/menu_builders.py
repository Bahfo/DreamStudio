# Written by Bahaa Nofal - 11/12/2025
# A special implementation of CustomTkinter suitable for DreamStudio
# Universal Widgets: Custom IronKinter script for building DreamStudio's
# environment. DO NOT PUBLISH OR COPY IN ANY METHOD OR WAY BY ANY MEAN,
# THIS SCRIPT IS ACCESIABLE ONLY UNDER THE AGREEMENT OF A DEVELOPER
# WORKING IN DREAMSTUIO'S ENVIRONMENT.

"""
COPYRIGHT 2026 DREAMSTUDIO - EX_TECHNOLOGIES - ALL RIGHTS RESREVED
Ironkinter is a supplementary header file wrapped above customtkinter
that imporves widgets creation, adds additional widgets, and animations.

The above copyright shall be included in all copies or substantial 
portions of the software.

Please note that DreamStudio's universal widgets wrappers is not a 
subject to publish. You got access to this file only as a developer
under the DreamStudio's agreement. The free publishable version and
edited for user experience is available under Ironkinter's framework,
which is a general purpose wrapper around tkinter that improves overall
performance, increasing thread acceptability and adds the same widgets
from DreamStudio's development environment. 
"""

import customtkinter as ctk
from dreamstudio.utils.colorDialog import ColorDialog
from dreamstudio.utils.largeButton import LargeButton
from dreamstudio.utils.layoutsTab import LayoutsTab
from dreamstudio.utils.largeButton import LargeButton
from dreamstudio.utils.linkLabel import LinkLabel
from dreamstudio.utils.smallButton import SmallButton
from dreamstudio.utils.toolTip import ToolTip
from dreamstudio.utils.horizontalButton import HorizontalButton
from dreamstudio.utils.verticalButton import VerticalButton
from dreamstudio.utils.animations import *


CONFIG_FILE = r"themes/config/config.json"
REFRESH_INTERVAL_MINUTES = 2
REFRESH_INTERVAL_MS = REFRESH_INTERVAL_MINUTES * 60 * 1000

icon_paths = {
    "load_ico": r"icons/system/load.png",
    "refresh_ico": r"icons/system/refresh.png",
    "console": r"icons/system/console.png",
    "debug": r"icons/system/debug.png",
    "manage": r"icons/system/manager.png",
    "problem": r"icons/system/problem.png",
    "ver": r"icons/system/version.png",
    "warning": r"icons/system/warning.png",
}

ctk_icons = {
    "search_photo": (r"icons/system/search.png", (24, 24)),
    "open_photo": (r"icons/system/open_folder.png", (24, 24)),
    "settings_photo": (r"icons/system/settings.png", (24, 24)),
    "save_photo": (r"icons/system/save_file.png", (24, 24)),
    "user_photo": (r"icons/system/user.png", (24, 24)),
}

arrow_icons = {
    "downArrow": (r"icons/system/down_arrow.png", (8, 8)),
    "upArrow": (r"icons/system/up_arrow.png", (8, 8)),
    "rightArrow": (r"icons/system/right_arrow.png", (8, 8)),
    "stepTo": (r"icons/system/stepTo.png", (20, 20)),
    "stepOut": (r"icons/system/stepOut.png", (20, 20)),
    "stepOver": (r"icons/system/stepOver.png", (20, 20)),
    "runToCursor": (r"icons/system/runToCursor.png", (20, 20)),
    "toggleCursor": (r"icons/system/toggle.png", (20, 20)),
}

allowed_extensions = {
    ".py",".txt",".c",".cpp",".json",".docx",".ppt",".pptx",".apk",
    ".cpp",".cs",".cc",".cxx",".html",".js",".java",".swift",".rb",
    ".ts",".jsx",".py",".h"}
