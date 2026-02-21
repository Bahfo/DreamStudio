from PIL import Image
import customtkinter as ctk

bsharp = Image.open(r"icons\types\b_sharp.png")
binary = Image.open(r"icons\types\bin.png")
c_f = Image.open(r"icons\types\c.ico")
cmake = Image.open(r"icons\types\cmake.png")
cpp = Image.open(r"icons\types\cpp.png")
c_sharp = Image.open(r"icons\types\csharp.ico")
css = Image.open(r"icons\types\css.png")
folder = Image.open(r"icons\types\folder.png")
git = Image.open(r"icons\types\git.png")
html_ = Image.open(r"icons\types\html.png")
javascript = Image.open(r"icons\types\javascript.ico")
jpeg = Image.open(r"icons\types\jpeg.png")
pycache = Image.open(r"icons\types\pyc.png")
python = Image.open(r"icons\types\python.ico")
ruby = Image.open(r"icons\types\ruby.ico")
rust = Image.open(r"icons\types\rust.ico")
shell = Image.open(r"icons\types\shell.png")
swift = Image.open(r"icons\types\swift.ico")
typescript = Image.open(r"icons\types\typescript.ico")

default = Image.open(r"icons\types\file.png")

bsharp_img = ctk.CTkImage(bsharp, bsharp, (15, 15))
binary_img = ctk.CTkImage(binary, binary, (15, 15))
c_file = ctk.CTkImage(c_f, c_f, (15, 15))
cmake_file = ctk.CTkImage(cmake, cmake, (15, 15))
cpp_file = ctk.CTkImage(cpp, cpp, (15, 15))
c_sharp_file = ctk.CTkImage(c_sharp, c_sharp, (15, 15))
css_file = ctk.CTkImage(css, css, (15, 15))
folder_img = ctk.CTkImage(folder, folder, (15, 15))
git_file = ctk.CTkImage(git, git, (15, 15))
html_file = ctk.CTkImage(html_, html_, (15, 15))
javascript_file = ctk.CTkImage(javascript, javascript, (15, 15))
jpeg_file = ctk.CTkImage(jpeg, jpeg, (15, 15))
pycache_file = ctk.CTkImage(pycache, pycache, (15, 15))
python_file = ctk.CTkImage(python, python, (15, 15))
ruby_file = ctk.CTkImage(ruby, ruby, (15, 15))
rust_file = ctk.CTkImage(rust, rust, (15, 15))
shell_file = ctk.CTkImage(shell, shell, (15, 15))
swift_file = ctk.CTkImage(swift, swift, (15, 15))
typescript_file = ctk.CTkImage(typescript, typescript, (15, 15))
default_img = ctk.CTkImage(default, default, (15, 15))

ICONS = {
    "bsharp": bsharp_img,
    "bin": binary_img,
    "c": c_file,
    "cmake": cmake_file,
    "cpp": cpp_file,
    "csharp": c_sharp_file,
    "cs": c_sharp_file,
    "css": css_file,
    "folder": folder_img,
    "git": git_file,
    "html": html_file,
    "js": javascript_file,
    "jpeg": jpeg_file,
    "pyc": pycache_file,
    "py": python_file,
    "rb": ruby_file,
    "rs": rust_file,
    "sh": shell_file,
    "swift": swift_file,
    "ts": typescript_file,
    "default": default_img
}
