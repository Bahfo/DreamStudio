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
from PIL import Image

CONFIG_FILE = r"themes/config/config.json"
REFRESH_INTERVAL_MINUTES = 2
REFRESH_INTERVAL_MS = REFRESH_INTERVAL_MINUTES * 60 * 1000

icon_paths = {
    "manage": r"assets/system/manager.png",
    "problem": r"assets/system/problem.png",
    "ver": r"assets/system/manager.png",
    "warning": r"assets/system/warning.png",
}

ctk_icons = {
    "search_photo": (r"assets/system/search.png", (24, 24)),
    "open_photo": (r"assets/system/open_folder.png", (24, 24)),
    "settings_photo": (r"assets/system/settings.png", (24, 24)),
    "save_photo": (r"assets/system/save_file.png", (24, 24)),
    "user_photo": (r"assets/system/user.png", (24, 24)),
}

allowed_extensions = {
    ".py",
    ".txt",
    ".c",
    ".cpp",
    ".json",
    ".docx",
    ".ppt",
    ".pptx",
    ".apk",
    ".cpp",
    ".cs",
    ".cc",
    ".cxx",
    ".html",
    ".js",
    ".java",
    ".swift",
    ".rb",
    ".ts",
    ".jsx",
    ".py",
    ".h",
}

# _file = Image.open()
# _folder =
# _settings =
# _save =
# _print =

# file_image = ctk.CTkImage()

explr_btn = r"assets/system/newvar.png"
find_btn_img = r"assets/system/folder.png"
save_btn_img = r"assets/system/save_file.png"
trk_chngs_img = r"assets/system/changes.png"
cmpr_chngs_img = r"assets/system/compare.png"
rn_img = r"assets/system/start.png"
dbg_img = r"assets/system/bug.png"
cnfg_img = r"assets/system/manager.png"
styles_img = r"assets/system/styles.png"
addons_img = r"assets/system/console.png"
ide_ = Image.open(r"assets/logos/dreamStudio_icon.png")
ide_icon = ctk.CTkImage(ide_, ide_, (20, 20))
