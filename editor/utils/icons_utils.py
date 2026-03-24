from PIL import Image
import customtkinter as ctk

assembly = Image.open("assets/types/asm.png")
bsharp = Image.open("assets/types/b_sharp.png")
binary = Image.open("assets/types/bin.png")
c_f = Image.open("assets/types/c.png")
cmake = Image.open("assets/types/cmake.png")
cpp = Image.open("assets/types/cpp.png")
csv = Image.open("assets/types/csv.png")
c_sharp = Image.open("assets/types/csharp.png")
css = Image.open("assets/types/css.png")
d_ = Image.open("assets/types/d.png")
docker = Image.open("assets/types/docker.png")
flutter = Image.open("assets/types/flutter.png")
fsharp = Image.open("assets/types/fsharp.png")
folder = Image.open("assets/types/folder.png")
git = Image.open("assets/types/git.png")
go = Image.open("assets/types/go.png")
html_ = Image.open("assets/types/html.png")
ipynb = Image.open("assets/types/ipynb.png")
javascript = Image.open("assets/types/javascript.png")
jpeg = Image.open("assets/types/jpeg.png")
md = Image.open("assets/types/md.png")
pdf = Image.open("assets/types/pdf.png")
pycache = Image.open("assets/types/pyc.png")
python = Image.open("assets/types/python.png")
rar = Image.open("assets/types/rar.png")
ruby = Image.open("assets/types/ruby.png")
rust = Image.open("assets/types/rust.png")
shell = Image.open("assets/types/shell.png")
svg = Image.open("assets/types/svg.png")
swift = Image.open("assets/types/swift.png")
typescript = Image.open("assets/types/typescript.png")
vb = Image.open("assets/types/vb.png")
vs = Image.open("assets/types/vs.png")
vscode = Image.open("assets/types/vscode.png")
default = Image.open("assets/types/file.png")


assembly_img = ctk.CTkImage(assembly, assembly, (13, 13))
bsharp_img = ctk.CTkImage(bsharp, bsharp, (15, 15))
binary_img = ctk.CTkImage(binary, binary, (15, 15))
c_file = ctk.CTkImage(c_f, c_f, (15, 15))
cmake_file = ctk.CTkImage(cmake, cmake, (15, 15))
cpp_file = ctk.CTkImage(cpp, cpp, (15, 15))
csv_file = ctk.CTkImage(csv, csv, (15, 15))
c_sharp_file = ctk.CTkImage(c_sharp, c_sharp, (15, 15))
css_file = ctk.CTkImage(css, css, (15, 15))
d_file = ctk.CTkImage(d_, d_, (15, 15))
docker_file = ctk.CTkImage(docker, docker, (15, 15))
folder_img = ctk.CTkImage(folder, folder, (15, 15))
flutter_file = ctk.CTkImage(flutter, flutter, (15, 15))
fsharp_file = ctk.CTkImage(fsharp, fsharp, (15, 15))
git_file = ctk.CTkImage(git, git, (15, 15))
go_file = ctk.CTkImage(go, go, (15, 15))
html_file = ctk.CTkImage(html_, html_, (15, 15))
ipynb_file = ctk.CTkImage(ipynb, ipynb, (15, 15))
javascript_file = ctk.CTkImage(javascript, javascript, (15, 15))
jpeg_file = ctk.CTkImage(jpeg, jpeg, (15, 15))
md_file = ctk.CTkImage(md, md, (15, 15))
pdf_file = ctk.CTkImage(pdf, pdf, (12, 12))
pycache_file = ctk.CTkImage(pycache, pycache, (15, 15))
python_file = ctk.CTkImage(python, python, (15, 15))
rar_file = ctk.CTkImage(rar, rar, (15, 15))
ruby_file = ctk.CTkImage(ruby, ruby, (15, 15))
rust_file = ctk.CTkImage(rust, rust, (15, 15))
shell_file = ctk.CTkImage(shell, shell, (15, 15))
svg_file = ctk.CTkImage(svg, svg, (15,15))
swift_file = ctk.CTkImage(swift, swift, (15, 15))
typescript_file = ctk.CTkImage(typescript, typescript, (15, 15))
visual_basic = ctk.CTkImage(vb, vb, (15, 15))
vs_config = ctk.CTkImage(vs, vs, (15, 15))
vscode_config = ctk.CTkImage(vscode, vscode, (15, 15))
default_img = ctk.CTkImage(default, default, (15, 15))

ICONS = {
    "asm": assembly_img,
    "bat": shell_file,
    "bsharp": bsharp_img,
    "bin": binary_img,
    "c": c_file,
    "cmake": cmake_file,
    "cpp": cpp_file,
    "csharp": c_sharp_file,
    "cs": c_sharp_file,
    "csv": csv_file,
    "css": css_file,
    "d": d_file,
    "docker" : docker_file,
    "folder": folder_img,
    "fish": shell_file,
    "flutter": flutter_file,
    "fsharp": fsharp_file,
    "git": git_file,
    "go": go_file,
    "gif": jpeg_file,
    "html": html_file,
    "ipynb": ipynb_file,
    "ico": jpeg_file,
    "js": javascript_file,
    "jpeg": jpeg_file,
    "md": md_file,
    "pdf": pdf_file,
    "png": jpeg_file,
    "ps1": shell_file,
    "pyc": pycache_file,
    "py": python_file,
    "rar": rar_file,
    "rb": ruby_file,
    "rs": rust_file,
    "sh": shell_file,
    "svg": svg_file,
    "swift": swift_file,
    "ts": typescript_file,
    "vb": visual_basic,
    "vs": vs_config,
    "vscode": vscode_config,
    "default": default_img
}
