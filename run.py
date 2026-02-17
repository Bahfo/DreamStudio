from dreamstudio.ui_build import App
from startup import *

# CODE REFACTOR FOR MAINTAINING ALL STEPS
if __name__ == '__main__':
    # app = App(None)
    welcome_window = Initialize()
    welcome_window.start_loading_screen()
    # app.run()