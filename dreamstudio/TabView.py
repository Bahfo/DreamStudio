from PIL import Image
import customtkinter as ctk
import dreamstudio.utils.table as table
import dreamstudio.menu_builders as uniwidgets
from dreamstudio.utils.treeview import FileTree

project_image = ctk.CTkImage(light_image=Image.open(r"icons\system\projectType.png"),
                             dark_image =Image.open(r"icons\system\projectType.png"),
                             size=(16,16))

ctk.set_appearance_mode("dark")

number_of_files : int = 4

class TabView:
    def __init__(self,
                 master,
                 width : int = 370,
                 height : int = 500,
                 corner_radius = 0,
                 border_width = 1,
                 border_color = None,
                 background_corner_colors = None,
                 overwrite_preferred_drawing_method = None,
                 **kwargs):

        self.mainFrame = ctk.CTkFrame(master=master,
                                      width=width,
                                      height=height,
                                      corner_radius=corner_radius,
                                      bg_color=["#F5F5F5", "#1E1E1E"],
                                      fg_color=["#F5F5F5", "#1E1E1E"],
                                      border_width=border_width,
                                      border_color=border_color,
                                      background_corner_colors=background_corner_colors,
                                      overwrite_preferred_drawing_method=overwrite_preferred_drawing_method)
        self.mainFrame.place(x=0, y=0)

        ############################################################
        # SOLUTION EXPLORER
        ############################################################

        self.solutionExplorerFrame = ctk.CTkFrame(self.mainFrame,
                                                  width=width,
                                                  height=height,
                                                  border_color=border_color,
                                                  border_width=1,
                                                  fg_color=["#F5F5F5", "#1E1E1E"],
                                                  corner_radius=0)

        self.explnLabel = ctk.CTkLabel(self.solutionExplorerFrame,
                                       text=f"  Solution: {number_of_files} files found",
                                       font=("Segoe UI", 12),
                                       fg_color=["#F5F5F5", "#1E1E1E"],
                                       width=width-2,
                                       image=project_image,
                                       compound="left",
                                       height=18,
                                       justify="left",
                                       anchor="w",
                                       text_color=["#1E1E1E", "#F5F5F5"])
        self.explnLabel.place(x=5, y=5)

        ############################################################
        # Gadgets Frame in Solution Explorer
        ############################################################

        self.gadgetsFrame = ctk.CTkFrame(self.solutionExplorerFrame,
                                         width=width,
                                         height=26,
                                         fg_color=["#F5F5F5", "#1E1E1E"],
                                         border_width=1,
                                         corner_radius=0,
                                         border_color=["#C8C8C8", "#444444"])
        self.gadgetsFrame.place(x=0, y=26)

        self.newFileBtn = uniwidgets.SmallButton(self.gadgetsFrame,
                                                 image_path=r"icons\system\newnew.png")
        self.newFileBtn.place(x=2,y=2)

        self.newDirBtn = uniwidgets.SmallButton(self.gadgetsFrame,
                                                 image_path=r"icons\system\newDir.png")
        self.newDirBtn.place(x=26,y=2)

        self.refreshBtn = uniwidgets.SmallButton(self.gadgetsFrame,
                                                 image_path=r"icons\system\refreshDir.png")
        self.refreshBtn.place(x=50,y=2)

        self.collapseBtn = uniwidgets.SmallButton(self.gadgetsFrame,
                                                 image_path=r"icons\system\collapse.png")
        self.collapseBtn.place(x=74,y=2)

        self.searchBar = ctk.CTkEntry(self.gadgetsFrame,
                                      fg_color=["#F5F5F5", "#1E1E1E"],
                                      border_color=["#C8C8C8", "#444444"],
                                      border_width=1,
                                      height=20,
                                      font=("Segoe UI", 12),
                                      width=250,
                                      corner_radius=0,
                                      placeholder_text="🔍 Search Solution Explorer")
        self.searchBar.place(x=(width-252),y=2)

        self.treeView = FileTree(master= self.solutionExplorerFrame, width=350, height=550)
        self.treeView.place(x=5,y=60)

        ############################################################
        # PROPERTIES FRAME
        ############################################################
        self.propertiesFrame = ctk.CTkFrame(self.mainFrame,
                                                  width=width,
                                                  height=height,
                                                  border_width=border_width,
                                                  border_color=border_color,
                                                  fg_color=["#F5F5F5", "#1E1E1E"],
                                                  corner_radius=0)

        self.propertiesFrame.pack_propagate(False)

        self.explnLabel1 = ctk.CTkLabel(self.propertiesFrame,
                                       text=f"Project Properties",
                                       font=("Segoe UI", 12),
                                       fg_color=["#F5F5F5", "#1E1E1E"],
                                       width=width,
                                       height=18,
                                       justify="left",
                                       anchor="w",
                                       text_color=["#1E1E1E", "#F5F5F5"])
        self.explnLabel1.place(x=8, y=5)

        self.properties_table = table.CTkTable(self.propertiesFrame,
                                                  row=7,
                                                  column=2,
                                                  padx=0,
                                                  pady=0,
                                                  border_width=1,
                                                  border_color="#808080",
                                                  corner_radius=0,
                                                  font=("Segoe UI",12),
                                                  header_color=["#C3C3C3","#2D2D2D"],
                                                  colors=[self.propertiesFrame.cget("fg_color"),
                                                          self.propertiesFrame.cget("fg_color")],
                                                  width=176,
                                                  height=18)
        self.properties_table.place(x=8,y=28)
        self.properties_table.insert(row=0,column=0,value="Property")
        self.properties_table.insert(row=0,column=1,value="Value")
        self.properties_table.insert(row=1,column=0,value="Classes")
        self.properties_table.insert(row=2,column=0,value="Functions")
        self.properties_table.insert(row=3,column=0,value="Variables")
        self.properties_table.insert(row=4,column=0,value="Decorations")
        self.properties_table.insert(row=5,column=0,value="Imports")
        self.properties_table.insert(row=6,column=0,value="Exceptions")

        self.solutionPropertiesLabel = ctk.CTkLabel(
            self.propertiesFrame,
            text="Solution Properties",
            width=60,
            font=("Segoe UI",12),
            justify="left",
            anchor="w"
        )
        self.solutionPropertiesLabel.place(x=8,y=186)

        self.solution_table = table.CTkTable(self.propertiesFrame,
                                                  row=5,
                                                  column=2,
                                                  padx=0,
                                                  pady=0,
                                                  border_width=1,
                                                  border_color="#808080",
                                                  corner_radius=0,
                                                  font=("Segoe UI",12),
                                                  header_color=["#C3C3C3","#2D2D2D"],
                                                  colors=[self.propertiesFrame.cget("fg_color"),
                                                          self.propertiesFrame.cget("fg_color")],
                                                  width=176,
                                                  height=18)
        self.solution_table.place(x=8,y=216)
        self.solution_table.insert(row=0,column=0,value="Solution Name")
        self.solution_table.insert(row=1,column=0,value="Output Type")
        self.solution_table.insert(row=2,column=0,value="Architecture")
        self.solution_table.insert(row=3,column=0,value="Operating System")
        self.solution_table.insert(row=4,column=0,value="Dependencies")

        ############################################################
        # GIT FRAME
        ############################################################
        self.gitChanges = ctk.CTkFrame(self.mainFrame,
                                         width=width,
                                         height=height,
                                         border_width=border_width,
                                         border_color=border_color,
                                         fg_color=["#F5F5F5", "#1E1E1E"],
                                         corner_radius=0)

        self.gitChanges.pack_propagate(False)

        ############################################################
        # TAB CHANGER
        ############################################################
        
        self.tabChanger = ctk.CTkFrame(width=width,
                                       master=self.mainFrame,
                                       height=(height/16),
                                       corner_radius=0,
                                       border_width=0,
                                       fg_color=["#E3E3E3", "#2B2B2B"],
                                       bg_color=["#E3E3E3", "#2B2B2B"])
        self.tabChanger.place(
            relx=0,
            rely=1.0,
            anchor="sw",
            relwidth=1.0)

        self.slnExplrBtn = ctk.CTkButton(master=self.tabChanger,
                                         width=50,
                                         height=(height/17),
                                         text="Solution Explorer ",
                                         text_color=["#262626", "#E3E3E3"],
                                         corner_radius=6,
                                         hover=False,
                                         border_width=0,
                                         font=("Segoe UI",12),
                                         fg_color=["#F5F5F5", "#1E1E1E"])
        self.slnExplrBtn.place(x=8,y=-5)

        self.propertiesBtn = ctk.CTkButton(master=self.tabChanger,
                                         width=50,
                                         height=(height/17),
                                         text="      Properties      ",
                                         text_color=["#262626", "#E3E3E3"],
                                         corner_radius=6,
                                         hover=False,
                                         border_width=0,
                                         font=("Segoe UI",12),
                                         fg_color=["#F5F5F5", "#1E1E1E"])
        self.propertiesBtn.place(x=118,y=-5)

        self.gitReposBtn = ctk.CTkButton(master=self.tabChanger,
                                         width=50,
                                         height=(height/17),
                                         text=" Git Repositories ",
                                         text_color=["#262626", "#E3E3E3"],
                                         corner_radius=6,
                                         hover=False,
                                         border_width=0,
                                         font=("Segoe UI",12),
                                         fg_color=["#F5F5F5", "#1E1E1E"])
        self.gitReposBtn.place(x=222,y=-5)

        self.slnExplrBtn.configure(
            command=lambda: self.show_side_frame(self.solutionExplorerFrame, self.slnExplrBtn))

        self.propertiesBtn.configure(
            command=lambda: self.show_side_frame(self.propertiesFrame, self.propertiesBtn))
        
        self.gitReposBtn.configure(
            command=lambda: self.show_side_frame(self.gitChanges, self.gitReposBtn))
        
        self.show_side_frame(self.solutionExplorerFrame, self.slnExplrBtn)

    def show_side_frame(self, frame, active_btn):
        for f in (self.solutionExplorerFrame, self.propertiesFrame, self.gitChanges):
            f.pack_forget()
        for b in (self.slnExplrBtn, self.propertiesBtn, self.gitReposBtn):
            b.configure(fg_color=["#E3E3E3", "#2B2B2B"])
            b.configure(border_color = ["#E3E3E3", "#2B2B2B"])

        frame.pack(fill="both", expand=True)
        active_btn.configure(fg_color=["#F5F5F5", "#1E1E1E"])
        active_btn.configure(border_color = ["#A8A8A8", "#555555"])

if __name__ == '__main__':
    window = ctk.CTk()
    window.geometry("500x500")
    tabview = TabView(master=window, fg_color="#3B3B3B", width=370)
    window.mainloop()