import tkinter as tk
from PIL import Image
import customtkinter as ctk
from typing import List,Dict
from tkinter import messagebox
import tkinter.font as tkFont

"""
EX TECHNOLOGIES SPECIAL WIDGETS IMPLEMENTATION
COPYRIGHT 2026
"""

########################################################################################
# WIDGETS
########################################################################################

class CTkTabSwitcher(ctk.CTkFrame):
    def __init__(self, master, tab_names, textbox, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.textbox = textbox
        self.placeholder = "Build code with EtherAI or start typing to dismiss"
        self.placeholder_active = False
        self.mode = self.master._get_appearance_mode()

        # Tabs frame
        self.tabs_frame = ctk.CTkFrame(self, height=29, 
                                       fg_color = "#C4C4C4" if self.mode == 'light' else "#303030")
        self.tabs_frame.pack(fill="x")
        self.tabs_frame.pack_propagate(False)

        # Tabs data
        self.tab_order = tab_names.copy()
        self.tab_labels = {}   # tab_name -> (label, button, container frame)
        self.tab_contents = {name: "" for name in tab_names}
        self.tab_saved = {name: True for name in tab_names}
        self.active_tab = None
        self.tab_count = len(tab_names)

        # Create initial tabs
        for name in self.tab_order:
            self._add_tab_header(name)

        # "+" button
        self.add_tab_button = ctk.CTkButton(
            self.tabs_frame, text="+", width=30, height=30, corner_radius=0,
            command=self._add_new_tab,
            fg_color="#303030" if self.mode == 'dark' else "#C4C4C4")
        self.add_tab_button.pack(side="right", padx=(5,0), pady=(0,2))

        # Set first active tab
        if self.tab_order:
            self._set_active_tab(self.tab_order[0])

        # Bind textbox events
        self.textbox.bind("<FocusIn>", self._on_focus_in)
        self.textbox.bind("<FocusOut>", self._on_focus_out)
        self.textbox.bind("<Key>", self._on_key_pressed)

        # Show placeholder initially if needed
        self._show_placeholder()

    # ------------------- Tabs -------------------
    def _add_tab_header(self, name):
        tab_frame = ctk.CTkFrame(self.tabs_frame, fg_color="transparent", corner_radius=0)
        tab_frame.pack(side="left", padx=(2,0), pady=(0,2))

        label = ctk.CTkLabel(tab_frame, text=name, corner_radius=0, fg_color="#404040", width=60, height=30)
        label.pack(side="left", fill="y")
        label.bind("<Button-1>", lambda e, n=name: self._set_active_tab(n))

        self.btn = ctk.CTkButton(tab_frame, text="x", width=25, height=30, corner_radius=0,
                            fg_color="#303030" if self.mode == 'dark' else "#C4C4C4",
                            text_color="#303030" if self.mode == 'light' else "#C4C4C4",
                            border_width=0,
                            command=lambda n=name: self._close_tab(n))
        self.btn.pack(side="left", fill="y")

        self.tab_labels[name] = (label, self.btn, tab_frame)
        self.tab_saved[name] = True

    def _set_active_tab(self, name):
        if name == self.active_tab:
            return

        # Save previous tab content
        if self.active_tab:
            content = "" if self.placeholder_active else self.textbox.get("1.0", "end-1c")
            self.tab_contents[self.active_tab] = content
            self.tab_saved[self.active_tab] = False

        # Update previous tab colors
        if self.active_tab and self.active_tab in self.tab_labels:
            label, btn, _ = self.tab_labels[self.active_tab]
            label.configure(fg_color="#303030" if self.mode == 'dark' else "#C4C4C4",font=("Segoe UI",14))
            btn.configure(fg_color="#303030" if self.mode == 'dark' else "#C4C4C4")

        # Update new tab colors
        if name in self.tab_labels:
            label, btn, _ = self.tab_labels[name]
            label.configure(fg_color="#1A1A1A" if self.mode == 'dark' else "#A3A3A3")
            btn.configure(fg_color="#1A1A1A" if self.mode == 'dark' else "#A3A3A3")
            label.configure(font=("Segoe UI Italic",14))

        self.active_tab = name

        # Load content
        self.textbox.delete("1.0", "end")
        content = self.tab_contents.get(name, "")
        if content.strip():
            self.textbox.insert("1.0", content)
            self.placeholder_active = False
        else:
            self._show_placeholder()

        self.tab_saved[name] = True

    def _close_tab(self, name):
        if len(self.tab_order) == 1:
            return  # Cannot close last tab

        # Check unsaved
        if not self.tab_saved.get(name, True):
            result = messagebox.askyesno("Unsaved Content", f"Tab '{name}' has unsaved content. Close anyway?")
            if not result:
                return

        # Destroy tab frame
        if name in self.tab_labels:
            _, _, tab_frame = self.tab_labels[name]
            tab_frame.destroy()
            del self.tab_labels[name]

        # Remove from data
        for d in [self.tab_order, self.tab_contents, self.tab_saved]:
            if name in d:
                d.pop(name, None)

        # Switch active tab
        if self.active_tab == name and self.tab_order:
            self._set_active_tab(self.tab_order[0])

    def _add_new_tab(self):
        if len(self.tab_order) >= 7:
            messagebox.showwarning("Tab Limit Reached", "Cannot open more than 7 tabs.")
            return

        self.tab_count += 1
        name = f"Tab {self.tab_count}"
        self.tab_order.append(name)
        self.tab_contents[name] = ""
        self._add_tab_header(name)
        self._set_active_tab(name)

    def open_file_tab(self, name, content=""):
        if name in self.tab_order:
            self._set_active_tab(name)
            return

        if len(self.tab_order) >= 7:
            messagebox.showwarning("Tab Limit Reached", "Cannot open more than 7 tabs.")
            return

        self.tab_order.append(name)
        self.tab_contents[name] = content
        self._add_tab_header(name)
        self._set_active_tab(name)

    # ------------------- Placeholder -------------------
    def _show_placeholder(self):
        if not self.textbox.get("1.0", "end-1c").strip():
            real_text = self.textbox._textbox
            italic_font = tkFont.Font(family="Consolas", size=14, slant="italic")
            real_text.tag_config("italic", font=italic_font)
            self.textbox.configure(state="normal")
            real_text.delete("1.0", "end")
            real_text.insert("1.0", self.placeholder, "italic")
            real_text.tag_add("placeholder", "1.0", "end")
            real_text.tag_config("placeholder", foreground="gray")
            self.placeholder_active = True

    def _hide_placeholder(self):
        if self.placeholder_active:
            self.textbox.delete("1.0", "end")
            self.textbox.tag_delete("placeholder")
            self.placeholder_active = False

    def _on_focus_in(self, event):
        if self.placeholder_active:
            self._hide_placeholder()

    def _on_focus_out(self, event):
        if not self.textbox.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _on_key_pressed(self, event):
        if self.placeholder_active:
            self._hide_placeholder()


class LayoutsTab(ctk.CTkFrame):
    """
    Flat and optimized tab manager.
    Original textbox is untouched.
    Tabs are created once; switching only updates highlight.
    Overflow tabs scroll; right buttons remain fixed.
    """

    def __init__(self, parent, textbox: ctk.CTkTextbox, max_layouts: int = 10,
                 initial_layouts: int = 1, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.textbox = textbox
        self.max_layouts = max_layouts
        self.layouts: List[Dict[str,str]] = []
        self.active_index: int = 0
        self.tab_widgets: List[Dict[str, ctk.CTkWidget]] = []
        self._button_width = 60
        self._visible_start = 0

        # ---------------- Top tab bar ----------------
        self.tab_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.tab_frame.pack(side="top", fill="x")
        self.tab_frame.pack_propagate(False)

        # Scrollable tabs container (expandable)
        self._tabs_container = ctk.CTkFrame(self.tab_frame, corner_radius=0)
        self._tabs_container.pack(side="left", fill="x", expand=True)

        # Fixed right buttons frame
        self._right_buttons = ctk.CTkFrame(self.tab_frame, corner_radius=0)
        self._right_buttons.pack(side="right")

        # Add layout button
        self.add_button = ctk.CTkButton(self._right_buttons, text="+", width=30,
                                        corner_radius=0, command=self.add_layout)
        self.add_button.pack(side="left", padx=(2,2))

        # ---------------- Initialize tabs ----------------
        for _ in range(initial_layouts):
            self._create_layout_internal()
        self._update_tab_visibility()
        self.switch_layout(0)

        # Bind resizing to update tab visibility
        self.bind("<Configure>", lambda e: self.after_idle(self._update_tab_visibility))

    # ---------------- Public API ----------------
    def add_layout(self):
        if len(self.layouts) >= self.max_layouts:
            self.add_button.configure(state="disabled")
            return
        self._create_layout_internal()
        self._update_tab_visibility()
        self.switch_layout(len(self.layouts)-1)

    def get_all_layouts(self) -> List[Dict[str,str]]:
        return [{"title": l["title"], "text": l["text"]} for l in self.layouts]

    # ---------------- Internal ----------------
    def _create_layout_internal(self):
        idx = len(self.layouts) + 1
        title = f"Untitled {idx}"
        self.layouts.append({"title": title, "text": ""})

        # Tab frame
        tab_frame = ctk.CTkFrame(self._tabs_container, corner_radius=0)
        tab_frame.pack(side="left", padx=2, pady=2)

        # Title button
        layout_btn = ctk.CTkButton(tab_frame, text=title, corner_radius=0,font=("Segoe UI",12),
                                   hover=False, command=lambda idx=idx-1: self.switch_layout(idx))
        layout_btn.pack(side="left", padx=(2,0))

        # Close button
        close_btn = ctk.CTkButton(tab_frame, text="×", width=24, height=24, font=("Segoe UI",15),
                                  corner_radius=0, hover=False,
                                  command=lambda idx=idx-1: self._close_layout(idx))
        close_btn.pack(side="right", padx=(2,2))

        # Right-click rename
        layout_btn.bind("<Button-3>", lambda e, idx=idx-1: self._rename_layout(idx))

        self.tab_widgets.append({"frame": tab_frame, "title_btn": layout_btn, "close_btn": close_btn})

    def _save_current_text(self):
        if self.layouts:
            self.layouts[self.active_index]["text"] = self.textbox.get("1.0","end-1c")

    def switch_layout(self, index:int):
        if index < 0 or index >= len(self.layouts):
            return
        self._save_current_text()
        self.active_index = index
        self.textbox.delete("1.0","end")
        self.textbox.insert("1.0", self.layouts[index]["text"])
        self._highlight_active_tab()

    def _highlight_active_tab(self):
        for i, tab in enumerate(self.tab_widgets):
            if i == self.active_index:
                tab["title_btn"].configure(fg_color="#292929")
            else:
                tab["title_btn"].configure(fg_color=tab["frame"].cget("fg_color"))

    def _close_layout(self, index:int):
        if len(self.layouts) <= 1:
            return
        self._save_current_text()
        self.layouts.pop(index)
        tab_widget = self.tab_widgets.pop(index)
        tab_widget["frame"].destroy()

        if self.active_index >= len(self.layouts):
            self.active_index = len(self.layouts)-1
        elif index < self.active_index:
            self.active_index -=1

        self.switch_layout(self.active_index)
        if len(self.layouts) < self.max_layouts:
            self.add_button.configure(state="normal")

    def _rename_layout(self, index:int):
        popup = ctk.CTkToplevel(self)
        popup.title("Rename layout")
        popup.geometry("300x120")
        popup.grab_set()

        lbl = ctk.CTkLabel(popup, text="New title:")
        lbl.pack(pady=(10,4))
        entry = ctk.CTkEntry(popup)
        entry.insert(0, self.layouts[index]["title"])
        entry.pack(padx=10)
        def apply_and_close():
            new = entry.get().strip()
            if new:
                self.layouts[index]["title"] = new
                self.tab_widgets[index]["title_btn"].configure(text=new)
            popup.destroy()
        btn = ctk.CTkButton(popup, text="Apply", command=apply_and_close)
        btn.pack(pady=8)

    # ---------------- Scroll arrows ----------------
    def _update_tab_visibility(self):
        container_width = max(self._tabs_container.winfo_width(), 200)
        visible_count = max(1, container_width // self._button_width)
        for i, tab in enumerate(self.tab_widgets):
            if i < self._visible_start or i >= self._visible_start + visible_count:
                tab["frame"].pack_forget()
            else:
                tab["frame"].pack(side="left", padx=2, pady=2)


class HorizontalButton(ctk.CTkFrame):
    def __init__(self, parent, image_path=None, text="", command=None, size=(16, 16),
                hover_border="#bebebe", click_border="#808080", font=("Segoe UI", 11), **kwargs):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border
        mode = self._get_appearance_mode()

        # --- Border frame ---
        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,
            border_color=self.hover_border,
            width=100,
            height=25
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)
        self.border_frame.pack_propagate(False)

        # --- Inner content frame (horizontal layout) ---
        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # --- Image ---
        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.pack(side="left", padx=(0, 5))
        else:
            self.icon = None

        # --- Label ---
        self.label = ctk.CTkLabel(self.inner_frame, text=text, font=font,
                                  text_color="#E1E1E1" if mode == "Dark" else "#c8c8c8")
        self.label.pack(side="left")

        # --- Bind hover/click events ---
        for widget in (self, self.border_frame, self.inner_frame, self.icon, self.label):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)


class VerticalButton(ctk.CTkFrame):
    """
    An Image/Label Button (Vertical Approach)
    """
    def __init__(self, parent, image_path=None, text="", command=None, size=(27, 27),
                hover_border="#bebebe", click_border="#808080", **kwargs):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.hover_border = hover_border
        self.click_border = click_border
        mode = self._get_appearance_mode()

        # --- Border frame (acts like an outline) ---
        self.border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=6,
            border_width=0,      # no border initially
            border_color=self.hover_border,
        )
        self.border_frame.pack(padx=2, pady=2, fill="both", expand=True)

        # --- Inner content frame ---
        self.inner_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # --- Image ---
        if image_path:
            self.image = ctk.CTkImage(light_image=Image.open(image_path), size=size)
            self.icon = ctk.CTkLabel(self.inner_frame, image=self.image, text="")
            self.icon.pack(pady=(0, 2))
        else:
            self.icon = None

        # --- Label ---
        self.label = ctk.CTkLabel(self.inner_frame, text=text, font=("Segoe UI", 12),
                                  text_color="#E1E1E1" if mode == "Dark" else "#c8c8c8")
        self.label.pack()

        # --- Bind hover/click ---
        for widget in (self, self.border_frame, self.inner_frame, self.icon, self.label):
            if widget:
                widget.bind("<Enter>", self._on_enter)
                widget.bind("<Leave>", self._on_leave)
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.border_frame.configure(border_width=1)

    def _on_leave(self, event):
        self.border_frame.configure(border_width=0)

    def _on_click(self, event):
        self.border_frame.configure(border_color=self.click_border)
        if self.command:
            self.command()

    def _on_release(self, event):
        self.border_frame.configure(border_color=self.hover_border)

class LinkLabel(ctk.CTkFrame):
    def __init__(self, parent, link_color="#1a73e8", after_link_color="#551a8b",
                 corner_radius=5, font=None, text="", command=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.command = command
        self.link_color = link_color
        self.after_link_color = after_link_color
        self.corner_radius = corner_radius
        self.font = font or ("Segoe UI", 12)

        # --- Hover frame ---
        self.hoverframe = ctk.CTkFrame(
            self,
            fg_color=parent.cget("fg_color"),
            corner_radius=self.corner_radius,
            border_width=0,
            border_color=parent.cget("fg_color")
        )
        self.hoverframe.pack(padx=2, pady=2, fill="both", expand=True)

        # --- Label --- 
        self.label = ctk.CTkLabel(self.hoverframe, text=text, font=self.font,
                                  text_color=self.link_color)
        self.label.pack()

        # --- Bind hover/click ---
        for widget in (self, self.hoverframe, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, event):
        self.label.configure(text_color=self.after_link_color)

    def _on_leave(self, event):
        self.label.configure(text_color=self.link_color)

    def _on_click(self, event):
        if self.command:
            self.command()

class TablePanel(ctk.CTkFrame):
    def __init__(self):
        pass

class ToolTip(ctk.CTkFrame):
        """
        Simple tooltip for Tk / CustomTkinter widgets.
        Usage: ToolTip(widget, "explanation text")
        """
        def __init__(self, widget, text, delay=400, bg="#2b2b2b", fg="white", font=("Segoe UI", 10)):
            self.widget = widget
            self.text = text
            self.delay = delay
            self.bg = bg
            self.fg = fg
            self.font = font

            self.tip_window = None
            self._after_id = None

            widget.bind("<Enter>", self._schedule)
            widget.bind("<Leave>", self._unschedule)
            widget.bind("<Motion>", self._move_tip_position)

        def _schedule(self, event=None):
            self._unschedule()
            self._after_id = self.widget.after(self.delay, self.show_tip)

        def _unschedule(self, event=None):
            if self._after_id is not None:
                try:
                    self.widget.after_cancel(self._after_id)
                except Exception:
                    pass
                self._after_id = None
            self.hide_tip()

        def _move_tip_position(self, event=None):
            if self.tip_window:
                x = event.x_root + 16
                y = event.y_root + 12
                try:
                    self.tip_window.wm_geometry(f"+{x}+{y}")
                except Exception:
                    pass

        def show_tip(self):
            if self.tip_window or not self.text:
                return
            x = self.widget.winfo_rootx() + 40
            y = self.widget.winfo_rooty() + 20

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_attributes("-topmost", True)
            tw.wm_geometry(f"+{x}+{y}")

            label = tk.Label(
                tw,
                text=self.text,
                justify="left",
                bg=self.bg,
                fg=self.fg,
                font=self.font,
                bd=0,
                padx=6,
                pady=3,
            )
            label.pack()

        def hide_tip(self):
            if self.tip_window:
                try:
                    self.tip_window.destroy()
                except Exception:
                    pass
                self.tip_window = None

class ListView(ctk.CTkFrame):
    def __init__(self):
        pass

class ColorDialog(ctk.CTkToplevel):
    def __init__(self, master, initial_color="#FFFFFF"):
        super().__init__(master)
        self.title("RGB Color Picker")
        self.resizable(False, False)
        self.geometry("300x550")

        # Current color state
        self.current_rgb = [255, 255, 255]
        self.current_hex = initial_color
        self.selected_color = None

        # Modal
        self.transient(master)
        self.grab_set()

        # ---------------------------
        # Main container
        # ---------------------------
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Content frame (sliders, palette, save, recent)
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=False)

        # Preview
        self.preview_frame = ctk.CTkFrame(content_frame, width=260, height=50,
                                          corner_radius=5, fg_color=self.current_hex)
        self.preview_frame.pack(pady=(0, 5))

        red_label = ctk.CTkLabel(content_frame, text="Red")
        red_label.pack()

        # Sliders
        self.slider_r = ctk.CTkSlider(content_frame, from_=0, to=255, number_of_steps=255,
                                      command=self._slider_changed)
        self.slider_r.set(self.current_rgb[0])
        self.slider_r.pack(fill="x", pady=2)

        green_label = ctk.CTkLabel(content_frame, text="Green")
        green_label.pack()

        self.slider_g = ctk.CTkSlider(content_frame, from_=0, to=255, number_of_steps=255,
                                      command=self._slider_changed)
        self.slider_g.set(self.current_rgb[1])
        self.slider_g.pack(fill="x", pady=2)

        blue_label = ctk.CTkLabel(content_frame, text="Blue")
        blue_label.pack()

        self.slider_b = ctk.CTkSlider(content_frame, from_=0, to=255, number_of_steps=255,
                                      command=self._slider_changed)
        self.slider_b.set(self.current_rgb[2])
        self.slider_b.pack(fill="x", pady=2)

        # Hex entry
        self.hex_entry = ctk.CTkEntry(content_frame, width=100)
        self.hex_entry.pack(pady=(5,5))
        self.hex_entry.insert(0, self.current_hex)
        self.hex_entry.bind("<Return>", lambda e: self._hex_changed())
        self.hex_entry.bind("<FocusOut>", lambda e: self._hex_changed())

        # Palette
        self.palette_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        self.palette_frame.pack(pady=5)
        self.default_palette = [
            "#FF0000", "#CD0000", "#AB0000", "#740000", "#720000", "#430000",
            "#803A00", "#9B5800", "#AE4E00", "#D55200", "#EB6600", "#FF8800",
            "#FFF700", "#E3BD00", "#DAB51F", "#D1C735", "#B7B100", "#798C00",
            "#397900", "#4E9712", "#5AA728", "#6AC039", "#4CB748", "#46B48A",
            "#20DA9F", "#1ED2D2", "#229CB2", "#187B8B", "#00567E", "#002E84",
            "#080076", "#29006B", "#340057", "#430055", "#520052", "#480022"
        ]
        self._create_palette_buttons()

        # Save button and recent colors
        self.save_button = ctk.CTkButton(content_frame, text="Save Color", command=self._save_current_color)
        self.save_button.pack(pady=(5,5))

        self.recent_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        self.recent_frame.pack(pady=(0,5))
        self.recent_colors = []
        self.max_recent = 6  # <=6 saved colors

        # ---------------------------
        # OK / Cancel buttons
        # ---------------------------
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(5,0))
        ok_button = ctk.CTkButton(button_frame, text="OK", width=60, command=self._on_ok)
        ok_button.pack(side="right", padx=5)
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", width=60, command=self._on_cancel)
        cancel_button.pack(side="right", padx=5)

        # Update preview initially
        self.update_preview()

    # ---------------------------
    # Slider / Hex updates
    # ---------------------------
    def _slider_changed(self, value):
        r = int(self.slider_r.get())
        g = int(self.slider_g.get())
        b = int(self.slider_b.get())
        self.current_rgb = [r, g, b]
        self.update_preview()

    def rgb_to_hex(self, r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"

    def hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip("#")
        if len(hex_code) != 6:
            messagebox.showerror("Wrong Format", "Invalid hex code!")
            raise ValueError("Invalid hex")
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return [r, g, b]

    def update_preview(self):
        hex_color = self.rgb_to_hex(*self.current_rgb)
        self.current_hex = hex_color
        self.preview_frame.configure(fg_color=hex_color)
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, hex_color)

    def update_sliders_from_hex(self):
        try:
            self.current_rgb = self.hex_to_rgb(self.current_hex)
            self.slider_r.set(self.current_rgb[0])
            self.slider_g.set(self.current_rgb[1])
            self.slider_b.set(self.current_rgb[2])
            self.update_preview()
        except:
            pass

    def _hex_changed(self):
        hex_value = self.hex_entry.get()
        if not hex_value.startswith("#"):
            hex_value = "#" + hex_value
        self.current_hex = hex_value
        self.update_sliders_from_hex()

    # ---------------------------
    # Palette buttons
    # ---------------------------
    def _create_palette_buttons(self):
        btn_size = 25
        for index, color in enumerate(self.default_palette):
            btn = ctk.CTkButton(
                self.palette_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c)
            )
            row = index // 6
            col = index % 6
            btn.grid(row=row, column=col, padx=2, pady=2)

    def _palette_color_selected(self, hex_color):
        self.current_hex = hex_color
        self.update_sliders_from_hex()

    # ---------------------------
    # Recent colors
    # ---------------------------
    def _save_current_color(self):
        if self.current_hex in self.recent_colors:
            return
        self.recent_colors.insert(0, self.current_hex)
        if len(self.recent_colors) > self.max_recent:
            self.recent_colors.pop()  # keep max 6
        for widget in self.recent_frame.winfo_children():
            widget.destroy()
        btn_size = 25
        for index, color in enumerate(self.recent_colors):
            btn = ctk.CTkButton(
                self.recent_frame,
                fg_color=color,
                width=btn_size,
                height=btn_size,
                corner_radius=5,
                text="",
                command=lambda c=color: self._palette_color_selected(c)
            )
            btn.grid(row=0, column=index, padx=2)

    # ---------------------------
    # OK / Cancel
    # ---------------------------
    def _on_ok(self):
        self.selected_color = self.current_hex
        self.destroy()

    def _on_cancel(self):
        self.selected_color = None
        self.destroy()

    def get_color(self):
        self.wait_window()
        return self.selected_color


class MediaElement(ctk.CTkFrame):
    def __init__(self):
        pass

class DrawingCanvas(ctk.CTkFrame):
    def __init__(self):
        pass

class DateTimeDialog(ctk.CTkFrame):
    def __init__(self):
        pass

class VisualTimer(ctk.CTkFrame):
    def __init__(self):
        pass

class GraphBox(ctk.CTkFrame):
    def __init__(self):
        pass

class NumericCounter(ctk.CTkFrame):
    def __init__(self):
        pass

class IconListFrame(ctk.CTkFrame):
    def __init__(self):
        pass

class CustomMessageBox(ctk.CTkToplevel):
    def __init__(self, master, message, font, width=200, height=100,
                 further_explanation=None, icon=None, offset_x=20, offset_y=40):
        super().__init__(master)
        self.overrideredirect(True)
        self.geometry(f"{width}x{height}")

        if icon:
            self.iconbitmap(icon)

        self.update_idletasks()                         # ensures screen width/height are accurate
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - offset_x             # offset_x: distance from right edge
        y = screen_height - height - offset_y           # offset_y: distance from bottom edge

        self.geometry(f"{width}x{height}+{x}+{y}")

        text = message if not further_explanation else f"{message}\n{further_explanation}"
        self.message_label = ctk.CTkLabel(
            self,
            text=text,
            font=font,
            fg_color=self.cget("fg_color")
        )
        self.message_label.place(x=40,y=30)

        self.close_btn = ctk.CTkButton(self, text="OK", command=self.destroy, width=80)
        self.close_btn.place(x=60, y=70)

        self.focus()
        self.grab_set()

########################################################################################
# ANIMATIONS AND SHADERS
########################################################################################

class ScreenShakeAnimation():
    def __init__(self, widget, orig_x=None, orig_y=None, intensity_x=5, intensity_y=2, duration=50, cycles=6, anchor=None):
            self.widget = widget
            self.intensity_x = intensity_x
            self.intensity_y = intensity_y
            self.duration = duration
            self.cycles = cycles
            self.anchor = anchor

            # Use provided original position or detect it
            widget.update_idletasks()
            self.orig_x = orig_x if orig_x is not None else widget.winfo_x()
            self.orig_y = orig_y if orig_y is not None else widget.winfo_y()

            # Start animation
            self._animate(0)

    def _animate(self, count):
        if count < self.cycles:
            offset_x = self.intensity_x if count % 2 == 0 else -self.intensity_x
            offset_y = self.intensity_y if count % 2 == 0 else -self.intensity_y

            # Move widget with optional anchor
            self.widget.place(
                x=int(self.orig_x + offset_x),
                y=int(self.orig_y + offset_y),
                anchor=self.anchor
            )

            self.widget.after(self.duration, lambda: self._animate(count + 1))
        else:
            # Restore original place
            self.widget.place(x=int(self.orig_x), y=int(self.orig_y), anchor=self.anchor)

class ClickPressAnimation():
    def __init__(self):
        pass

class MouseHoverAnimation():
    def __init__(self):
        pass

class MouseWaitAnimation():
    def __init__(self):
        pass

class SlidingAnimation():
    def __init__(self):
        pass

class WaitAnimation():
    def __init__(self):
        pass