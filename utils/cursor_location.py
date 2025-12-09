import pyautogui
import time

while True:
    x, y = pyautogui.position()
    print(f"Mouse is at ({x}, {y})", end="\r")
    time.sleep(0.1)
