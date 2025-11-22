import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

def agreement_registeration():
    ctk.set_appearance_mode('dark')
    window = ctk.CTk()
    window.title("Softdream Licesnse Agreement")
    window.iconbitmap()
    window.resizable(False,False)
    window_width = 580
    window_height = 480

    window.update_idletasks()

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    frame_1 = ctk.CTkFrame(window, bg_color="#1e1e1e",width=550,height=440,
                           fg_color="#303030")
    frame_1.pack(padx=15,pady=15,side='top',anchor='w',expand=True,fill='both')
    frame_1.pack_propagate(False)

    frame_2 = ctk.CTkFrame(window, bg_color="#1e1e1e",width=550,height=440,
                           fg_color="#303030")
    frame_2.pack(padx=15,pady=15,side='top',anchor='w',expand=True,fill='both')
    frame_2.pack_propagate(False)

    frame_3 = ctk.CTkFrame(window, bg_color="#1e1e1e",width=550,height=440,
                           fg_color="#303030")
    frame_3.pack(padx=15,pady=15,side='top',anchor='w',expand=True,fill='both')
    frame_3.pack_propagate(False)

    frame_4 = ctk.CTkFrame(window, bg_color="#1e1e1e",width=550,height=440,
                           fg_color="#303030")
    frame_4.pack(padx=15,pady=15,side='top',anchor='w',expand=True,fill='both')
    frame_4.pack_propagate(False)

    for frame in (frame_1, frame_2, frame_3, frame_4):
        frame.place(relwidth=1, relheight=1)

    notice_label = ctk.CTkLabel(frame_1,text="Welcome to Softdream Beta Program",
                                font=("Segoe UI",18))
    notice_label.pack(padx=10,pady=10,side='top',anchor='w')

    explanation_text = """Please read the following text carefully, if you do not agree to the terms of service, freely shut down the program without continuation. Should you proceed, you click (I agree to the terms of service and BETA program policies)"""

    explanation_label = ctk.CTkLabel(
        frame_1,
        text=explanation_text,
        font=("Segoe UI", 12),
        justify='left',
        anchor='w',
        wraplength=528
    )
    explanation_label.pack(padx=10, pady=10, side='top', anchor='w')

    license_agreement = ctk.CTkTextbox(frame_1,font=("Segoe UI",12),
                                       width=530,height=190)
    license_agreement.insert("1.0","License")
    license_agreement.pack(padx=10,pady=10,side='top',anchor='w')
    license_agreement.configure(state=ctk.DISABLED)

    agree_var = ctk.IntVar(value=0)

    def on_radio_button_click():
        if agree_var.get() == 1:
            continue_button.configure(state=ctk.NORMAL)
        else:
            continue_button.configure(state=ctk.DISABLED)

    check_button = ctk.CTkRadioButton(
        frame_1,
        text="I agree to the terms of service",
        font=("Segoe UI", 12),
        variable=agree_var,
        value=1,
        radiobutton_height=15,
        radiobutton_width=15,
        command=on_radio_button_click
    )
    check_button.pack(padx=10, pady=10, side='top', anchor='w')

    discheck_button = ctk.CTkRadioButton(
        frame_1,
        text="I do not agree to the terms of service",
        font=("Segoe UI", 12),
        variable=agree_var,
        value=2,
        radiobutton_width=15,
        radiobutton_height=15,
        command=on_radio_button_click
    )
    discheck_button.pack(padx=10, pady=5, side='top', anchor='w')

    continue_button = ctk.CTkButton(frame_1,text="Proceed with Configuration",
                                    font=("Segoe UI",14),fg_color="#0063af",
                                    bg_color="#303030",width=45,height=25,
                                    corner_radius=5,state=ctk.DISABLED,command=lambda: frame_2.tkraise())
    continue_button.pack(padx=10, pady=10, side='bottom', anchor='e')

    setting_up = ctk.CTkLabel(frame_2,text="Let's Set You Up",
                                font=("Segoe UI",18))
    setting_up.pack(padx=10,pady=10,side='top',anchor='w')

    explanation_text_1 = """Let's start setting you up to the BETA program, enter the following information and proceed, please make sure you have an internet connection to save you information to the cloud"""

    explanation_label_1 = ctk.CTkLabel(
        frame_2,
        text=explanation_text_1,
        font=("Segoe UI", 12),
        justify='left',
        anchor='w',
        wraplength=528
    )
    explanation_label_1.pack(padx=10, pady=(0,5), side='top', anchor='w')

    name_label = ctk.CTkLabel(
        frame_2,
        text="Name",
        font=("Segoe UI",14),
        justify='left',
        anchor='w'
    )
    name_label.pack(padx=10, pady=(10,0), side='top', anchor='w')

    name_label_tip = ctk.CTkLabel(
        frame_2,
        text="Set up a name for your account, your BETA program will use this name, you cannot change it later",
        font=("Segoe UI",12),
        justify='left',
        anchor='w'
    )
    name_label_tip.pack(padx=10, pady=(0,5), side='top', anchor='w')

    name_box = ctk.CTkEntry(
        frame_2,
        placeholder_text="example_name: mechangeleon",
        font=("Segoe UI",12),
        justify='left',
        width=400,
        height=40
    )
    name_box.pack(padx=10,pady=(0,0),side='top',anchor='w')

    account_label = ctk.CTkLabel(
        frame_2,
        text="Account",
        font=("Segoe UI",14),
        justify='left',
        anchor='w'
    )
    account_label.pack(padx=10, pady=(10,0), side='top', anchor='w')

    account_label_tip = ctk.CTkLabel(
        frame_2,
        text="Enter a valid account to proceed, we will send you a confirmation email once validation completes",
        font=("Segoe UI",12),
        justify='left',
        anchor='w'
    )
    account_label_tip.pack(padx=10, pady=(0,5), side='top', anchor='w')

    account_box = ctk.CTkEntry(
        frame_2,
        placeholder_text="example_email: example123@gmail.com",
        font=("Segoe UI",12),
        justify='left',
        width=400,
        height=40
    )
    account_box.pack(padx=10,pady=(0,0),side='top',anchor='w')

    description_label = ctk.CTkLabel(
        frame_2,
        text="Description",
        font=("Segoe UI",14),
        justify='left',
        anchor='w'
    )
    description_label.pack(padx=10, pady=(10,0), side='top', anchor='w')

    description_label_tip = ctk.CTkLabel(
        frame_2,
        text="Please choose what describes you best in terms of experience",
        font=("Segoe UI",12),
        justify='left',
        anchor='w'
    )
    description_label_tip.pack(padx=10, pady=(0,5), side='top', anchor='w')

    options = ['Student','Full time Programmer','Professor','Senior Dev','Junior Dev','Other']

    description_box = ctk.CTkComboBox(
        frame_2,
        values=options,
        font=("Segoe UI",12),
        justify='left',
        width=400,
        height=40
    )
    description_box.pack(padx=10,pady=(0,0),side='top',anchor='w')
    description_box.configure(state="readonly")

    loading_image = Image.open(r"icons\animated_widgets\Circle Loader.gif")
    new_size = (300, 300)
    frames_loading = [ImageTk.PhotoImage(frame.copy().resize(new_size)) for frame in ImageSequence.Iterator(loading_image)]

    label = ctk.CTkLabel(frame_3,text="")
    label.pack(pady=20)

    def loading_to_configure():
        frame_3.tkraise()
        def animate(counter=0):
            frame = frames_loading[counter % len(frames_loading)]
            label.configure(image=frame)
            frame_3.after(30, lambda: animate(counter + 1))

        animate()
        label_2 = ctk.CTkLabel(frame_3,text="Loading Configuration",font=("Segoe UI",16))
        label_2.pack(pady=(10,0))

        label_2 = ctk.CTkLabel(frame_3,text="Rest assured, we got this",font=("Segoe UI",12))
        label_2.pack(pady=(5,0))
        frame_3.after(10000, lambda: frame_4.tkraise())

    button_next_1 = ctk.CTkButton(frame_2,text="\u279C",
                                  font=("Segoe UI",14,"bold"),fg_color="#0063af",
                                  bg_color="#303030",width=35,height=35,
                                  corner_radius=5,command=loading_to_configure)
    button_next_1.pack(padx=15,pady=(10,0),side='top',anchor='e')

    all_set_image = Image.open(r"icons\animated_widgets\Successfully Done.gif")
    new_size = (300, 300)
    frames_set = [ImageTk.PhotoImage(frame.copy().resize(new_size)) for frame in ImageSequence.Iterator(all_set_image)]

    label_3 = ctk.CTkLabel(frame_4, text="")
    label_3.pack(pady=20)

    def animate_once(counter=0):
        if counter < len(frames_set):
            label_3.configure(image=frames_set[counter])
            label_3.after(70, lambda: animate_once(counter + 1))

    animate_once() 

    def loading_main_program():
        window.destroy()
        app = main.App()
        app.run()

    button_next_2 = ctk.CTkButton(
        frame_4,
        text="Continue with Registration \nThis won't take long",
        font=("Segoe UI",14),
        fg_color="#0063af",
        bg_color="#303030",
        width=45,
        height=25,
        corner_radius=5,
        command=loading_main_program)
    button_next_2.pack(padx=10, pady=(0,50), side='bottom')


    label_2 = ctk.CTkLabel(frame_4,text="All Set to Go!",font=("Segoe UI",16))
    label_2.pack(pady=(10,0))

    frame_1.tkraise()
    window.mainloop()

agreement_registeration()