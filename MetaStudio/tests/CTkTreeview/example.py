import customtkinter as ctk

from .treeview import CTkTreeview
from .utils import grid


def main():
    app = ctk.CTk()
    app.title("CTkTreeview Example")
    frame = ctk.CTkFrame(app, width=500)
    frame.pack(fill="both")

    tree = CTkTreeview(frame, columns=["First", "Last", "Age"], selectmode="browse")
    grid(tree, column=0, row=0)
    app.after(100, lambda: print(app.geometry()))

    with tree.headings() as th:
        th.text("First", "First Name")
        th.text("Last", "Last Name")
        th.text("Age", "Age")

    with tree.columns() as tc:
        tc.width("#0", 30)
        tc.minwidth("#0", 30)

    tree.insert("", "end", values=("John", "Smith", "30"))
    tree.insert("", "end", values=("Jane", "Doe", "28"))
    tree.insert("", "end", values=("Andrew", "Johnson", "27"))

    app.mainloop()


if __name__ == "__main__":
    main()
