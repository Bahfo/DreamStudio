import sys
import time
import socket
from blessed import Terminal

terminal = Terminal()

WINDOW_BG = terminal.on_white
TEXT_MAIN_BLUE = terminal.blue           
TEXT_DESC_BLACK = terminal.black         
KEY_HIGHLIGHT_RED = terminal.red         

SELECT_BG = terminal.on_cyan
SELECT_TEXT = terminal.white

def get_ip():
    """Retrieves the primary active LAN IP address of the device."""
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    is_online = False
    try:
        test_socket.connect(("8.8.8.8", 80))
        lan_ip = test_socket.getsockname()[0]
        is_online = True if lan_ip else False
    except Exception:
        lan_ip = "127.0.0.1"
        is_online = False
    finally:
        test_socket.close()
    return [lan_ip, is_online]

def draw_background():
    """Fills terminal display with a rock-solid blue canvas."""
    for y in range(terminal.height):
        print(terminal.move_xy(0, y) + terminal.on_blue + " " * terminal.width, end="")

def draw_top_bars(active_tab):
    """Renders a fixed header and horizontal navigation bar at the top of the screen."""
    title_text = " DSInstaller v1.0.0 - DreamStudio Setup "
    print(terminal.move_xy(0, 0) + terminal.on_black + terminal.white 
        + title_text.center(terminal.width), end="")
    
    tab_1 = "  1. Options  "
    tab_2 = "  2. Information  "

    if active_tab == 0:
        str_1 = terminal.on_blue + terminal.white + terminal.bold(tab_1)
        str_2 = terminal.on_black + terminal.white + tab_2  
    else:
        str_1 = terminal.on_black + terminal.white + tab_1  
        str_2 = terminal.on_blue + terminal.white + terminal.bold(tab_2)
        
    combined_tabs = str_1 + str_2
    remainder_length = terminal.width - (len(tab_1) + len(tab_2))
    print(terminal.move_xy(0, 1) + combined_tabs + terminal.on_black 
        + " " * remainder_length, end="")
    sys.stdout.flush()

def draw_status_bar():
    """Renders a full-width status bar using the window background with red highlighted keys."""
    segments = [
        ("E:", " Exit      "),
        ("1-2-...:", " Tabs Navigation      "),
        ("F1:", " Documentation      "),
        ("F2:", " Instant Studio Installation")
    ]
    plain_text = " " + "".join(key + desc for key, desc in segments)
    padding_length = max(0, terminal.width - len(plain_text))
    status_bar_line = WINDOW_BG + " "
    
    for key, desc in segments:
        status_bar_line += WINDOW_BG + KEY_HIGHLIGHT_RED + key + WINDOW_BG + terminal.black + desc
    status_bar_line += WINDOW_BG + (" " * padding_length)
    print(terminal.move_xy(0, terminal.height - 1) + status_bar_line, end="", flush=True)

def draw_progress_modal(title, message, current, total, width=80):
    """Renders a clean progress bar modal overlay."""
    height = 9
    start_x = (terminal.width - width) // 2
    start_y = max(3, (terminal.height - height) // 2)

    percent = min(100, int((current / total) * 100))
    bar_width = width - 16
    filled_units = int((percent / 100) * bar_width)
    empty_units = bar_width - filled_units

    progress_bar = (terminal.cyan + "█" * filled_units + 
                    terminal.white + "░" * empty_units)

    for i in range(height):
        print(terminal.move_xy(start_x + 2, start_y + i + 1) 
            + terminal.on_black + " " * width, end="")
    
    for i in range(height):
        print(terminal.move_xy(start_x, start_y + i) + WINDOW_BG + " " * width, end="")

    print(terminal.move_xy(start_x + 3, start_y + 1) + WINDOW_BG + 
        terminal.black + terminal.bold(title), end="")
    print(terminal.move_xy(start_x + 4, start_y + 3) + WINDOW_BG + 
        terminal.black + f"{message:<{width-8}}", end="")
    print(terminal.move_xy(start_x + 4, start_y + 5) + WINDOW_BG + 
        terminal.black + f"[ {progress_bar}{terminal.black} ] {percent:3}%", end="")

    sys.stdout.flush()

def draw_window_frame(title, num_lines, width=100):
    """Draws static main window frame components."""
    inner_height = num_lines
    height = inner_height + 9
    
    start_x = (terminal.width - width) // 2
    start_y = max(3, (terminal.height - height) // 2)

    for i in range(height):
        print(terminal.move_xy(start_x + 2, start_y + i + 1) 
            + terminal.on_black + " " * width, end="")

    for i in range(height):
        print(terminal.move_xy(start_x, start_y + i) + WINDOW_BG + " " * width, end="")

    print(terminal.move_xy(start_x + 3, start_y + 1) + WINDOW_BG 
        + terminal.black + terminal.bold(title), end="")
    print(terminal.move_xy(start_x + 3, start_y + 2) + WINDOW_BG 
        + terminal.black, "Welcome to DS Installer - DreamStudio IDE Interactive Installation")
    print(terminal.move_xy(start_x + 3, start_y + 3) + WINDOW_BG 
        + terminal.black, "Please choose one of the following options")

    inner_x = start_x + 3
    inner_y = start_y + 4
    inner_w = width - 6

    print(terminal.move_xy(inner_x, inner_y) + WINDOW_BG + terminal.black 
        + "┌" + "─" * (inner_w - 2) + "┐", end="")
    for i in range(1, inner_height + 1):
        print(terminal.move_xy(inner_x, inner_y + i) + WINDOW_BG 
            + terminal.black + "│" + " " * (inner_w - 2) + "│", end="")
    print(terminal.move_xy(inner_x, inner_y + inner_height + 1) + WINDOW_BG 
        + terminal.black + "└" + "─" * (inner_w - 2) + "┘", end="")

    print(terminal.move_xy(start_x + 2, start_y + height - 3) + WINDOW_BG 
        + terminal.black + "─" * (width - 4), end="")

    ok_btn = "  < OK >  "
    cancel_btn = " <Cancel> "
    print(terminal.move_xy(start_x + (width // 2) - 13, start_y + height - 2) 
        + terminal.on_blue + terminal.yellow + ok_btn, end="")
    print(terminal.move_xy(start_x + (width // 2) + 2, start_y + height - 2) 
        + WINDOW_BG + terminal.black + cancel_btn, end="")

    return inner_x + 2, inner_y + 1, inner_w - 4

def draw_options_only(options, selected_idx, start_x, start_y, content_width):
    """Draws individual selectable list options."""
    for idx, (name, desc) in enumerate(options):
        y_pos = start_y + idx

        if idx == selected_idx:
            full_line = f" {name:<20} {desc}"
            padded_line = f"{full_line:<{content_width}}"
            print(terminal.move_xy(start_x, y_pos) + SELECT_BG + SELECT_TEXT + padded_line, end="")
        else:
            print(terminal.move_xy(start_x, y_pos) + WINDOW_BG + " " * content_width, end="")

            first_char = name[0]
            rest_of_name = name[1:]

            print(terminal.move_xy(start_x, y_pos) + WINDOW_BG 
                + KEY_HIGHLIGHT_RED + " " + first_char, end="")
            print(terminal.move_xy(start_x + 2, y_pos) 
                + WINDOW_BG + TEXT_MAIN_BLUE + f"{rest_of_name:<18}", end="")
            print(terminal.move_xy(start_x + 22, y_pos) 
                + WINDOW_BG + TEXT_DESC_BLACK + desc, end="")
    sys.stdout.flush()

def draw_static_info_pane(title, lines, width=86):
    """Renders a non-interactive aggregated static text container panel."""
    inner_height = len(lines)
    height = inner_height + 6

    start_x = (terminal.width - width) // 2
    start_y = max(3, (terminal.height - height) // 2)

    for i in range(height):
        print(terminal.move_xy(start_x + 2, start_y + i + 1) 
            + terminal.on_black + " " * width, end="")
    for i in range(height):
        print(terminal.move_xy(start_x, start_y + i) 
            + WINDOW_BG + " " * width, end="")

    print(terminal.move_xy(start_x + 3, start_y + 1) 
        + WINDOW_BG + terminal.black + terminal.bold(title), end="")

    inner_x = start_x + 3
    inner_y = start_y + 3
    inner_w = width - 6

    print(terminal.move_xy(inner_x, inner_y) + WINDOW_BG + terminal.black
        + "┌" + "─" * (inner_w - 2) + "┐", end="")
    for i in range(1, inner_height + 1):
        print(terminal.move_xy(inner_x, inner_y + i) + WINDOW_BG 
            + terminal.black + "│" + " " * (inner_w - 2) + "│", end="")
    print(terminal.move_xy(inner_x, inner_y + inner_height + 1) 
        + WINDOW_BG + terminal.black + "└" + "─" * (inner_w - 2) + "┘", end="")

    for idx, line in enumerate(lines):
        print(terminal.move_xy(inner_x + 2, inner_y + 1 + idx) 
            + WINDOW_BG + TEXT_DESC_BLACK + f"{line:<{inner_w-4}}", end="")
    sys.stdout.flush()

def show_interactive_less_menu(title, lines, width=80):
    """Renders data maps inside an overlay utility view window."""
    inner_height = len(lines)
    height = inner_height + 6

    start_x = (terminal.width - width) // 2
    start_y = max(3, (terminal.height - height) // 2)

    print(terminal.clear, end="")
    draw_background()

    for i in range(height):
        print(terminal.move_xy(start_x + 2, start_y + i + 1) 
            + terminal.on_black + " " * width, end="")
    for i in range(height):
        print(terminal.move_xy(start_x, start_y + i) + WINDOW_BG 
            + " " * width, end="")

    print(terminal.move_xy(start_x + 3, start_y + 1) + WINDOW_BG 
        + terminal.black + terminal.bold(title), end="")
    for idx, line in enumerate(lines):
        print(terminal.move_xy(start_x + 4, start_y + 3 + idx) 
            + WINDOW_BG + terminal.black + line, end="")

    print(terminal.move_xy(start_x + 2, start_y + height - 3) 
        + WINDOW_BG + terminal.black + "─" * (width - 4), end="")
    
    ok_btn = "  < OK >  "
    print(terminal.move_xy(start_x + (width // 2) - 5, start_y + height - 2) 
        + terminal.on_blue + terminal.yellow + ok_btn, end="")
    sys.stdout.flush()

    while True:
        key = terminal.inkey()
        if key.name in ("KEY_ENTER", "KEY_ESCAPE") or key == "\n":
            break

def fallback(active_tab):
    """Redraws main background framework and structural canvas blocks."""
    print(terminal.clear, end="")
    draw_background()
    draw_top_bars(active_tab)
    if active_tab == 0:
        return draw_window_frame("DSInstaller Options Manager", len(options))
    return None, None, None


options = [
    ("Upgrade",             "Upgrade the installer if updates available"),
    ("Test",                "Check internet connection"),
    ("Restore",             "Restore default settings"),
    ("Download",            "Download and Install latest version of DreamStudio IDE"),
    ("Marketplace",         "View and Install latest applications from EXcellent TechStacks"),
    ("Downgrade",           "Install an older version of DreamStudio IDE and delete current one"),
    ("Aquire Requirements", "Install all requirements for DreamStudio (Manual Installations)"),
    ("Settings",            "Open DSInstaller Settings"),
    ("Documentation",       "Open Documentations"),
    ("Exit",                "Exit DSInstaller")
]

test_connection = [
    "Testing Connection to the network",
    f"Is connected to Internet:                 {get_ip()[1]}",
    f"Connection IP Address (Local LAN IP):     {get_ip()[0]}",
]

aggregated_information = [
    "  DreamStudio Installer - Version 1.0.0 BETA",
    "  Studio Latest Supported Version:       Quiet Vally - Release 1.0.1",
    "  Studio Release Version:                Quiet Vally - Release 1.0.1",
    "  Estimated Long-Term-Support Time:      Until August 31st - 2026",
    f"  Active Local Device Host IP:           {get_ip()[0]}",
    "  Installer ID Code                      12B513X-E12",
    "",
    "",
    "",
    " (C) COPYRIGHT - 2026 EXcellent TechStacks - All Rights Reserved.",
    " This Installer is licensed under the GPLv3 Software License agreement, which is provided",
    " within Studio's public repositories.",
    " Please inspect distant source code trees to view full license terms."
]

with terminal.fullscreen(), terminal.cbreak(), terminal.hidden_cursor():
    active_tab = 0  
    selected_option = 0
    
    print(terminal.clear, end="")
    draw_background()
    draw_top_bars(active_tab)
    start_x, start_y, content_width = draw_window_frame("DSInstaller Options Manager", len(options))
    title_text = " DSInstaller v1.0.0 - DreamStudio Setup "
    draw_status_bar()

    while True:
        if active_tab == 0:
            draw_options_only(options, selected_option, start_x, start_y, content_width)
        else:
            draw_static_info_pane("System Information & Licensing Overview", aggregated_information,
                width=100)
            
        key = terminal.inkey()
        
        if key.name == "KEY_LEFT":
            if active_tab != 0:
                active_tab = 0
                start_x, start_y, content_width = fallback(active_tab)
                draw_status_bar()
        elif key.name == "KEY_RIGHT":
            if active_tab != 1:
                active_tab = 1
                fallback(active_tab)
                draw_status_bar()
                
        elif key.name == "KEY_UP" and active_tab == 0:
            selected_option = (selected_option - 1) % len(options)
        elif key.name == "KEY_DOWN" and active_tab == 0:
            selected_option = (selected_option + 1) % len(options)

        elif key.name in ("KEY_ENTER", "\n") and active_tab == 0:
            if selected_option == 0:  
                print(terminal.clear, end="")
                draw_background()
                draw_top_bars(active_tab)
                for i in range(101):
                    draw_progress_modal("Upgrade Status", 
                        "Searching and fetching updates...", current=i, total=100)
                    time.sleep(0.03)
                start_x, start_y, content_width = fallback(active_tab)
                draw_status_bar()

            elif selected_option == 1:  
                show_interactive_less_menu("Test Connection", test_connection)
                start_x, start_y, content_width = fallback(active_tab)
                draw_status_bar()

            elif selected_option == 9:  
                break