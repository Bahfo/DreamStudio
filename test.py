import os
import time
import random
import shutil

# CHANGE THIS to a folder your IDE is currently watching
TEST_DIR = "./test_project" 

def run_stress_test():
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
        
    print(f"Starting Stress Test on {TEST_DIR}...")
    
    try:
        for i in range(1, 11):
            # 1. Simulate "New Folder" creation
            folder_name = f"folder_{i}"
            folder_path = os.path.join(TEST_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            print(f"Created {folder_name}")
            time.sleep(0.1) # Small delay to see if Watchdog handles it
            
            # 2. Simulate "Ghost" files (OS Hover noise)
            for j in range(3):
                tmp_file = os.path.join(folder_path, f".tmp_hover_{j}.tmp")
                with open(tmp_file, "w") as f: f.write("noise")
                time.sleep(0.05)
                os.remove(tmp_file) # Delete immediately
            
            # 3. Simulate File Creation inside
            file_path = os.path.join(folder_path, f"data_{i}.txt")
            with open(file_path, "w") as f: f.write("content")
            
            # 4. Rapid Rename (Common trigger for hierarchy breaks)
            new_file_path = os.path.join(folder_path, f"final_file_{i}.txt")
            os.rename(file_path, new_file_path)
            
            time.sleep(0.5)
            
        print("Stress test complete. Check if the IDE tree is duplicated or flat.")
        
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    run_stress_test()