import ctypes
import os

###################################################
# FUNCTIONS TO CALL SEARCH FILE DYNAMIC LIBRARY
###################################################

class FilesList(ctypes.Structure):
    _fields_ = [
        ("names", ctypes.POINTER(ctypes.c_char_p)),
        ("count", ctypes.c_size_t)
    ]

script_directory = os.path.dirname(os.path.abspath(__file__))
searchFile_path  = os.path.join(script_directory, "searchFile.dll")

c_functions = ctypes.CDLL(searchFile_path)
c_functions.lscwd.argtypes = [ctypes.c_char_p]
c_functions.lscwd.restype  = FilesList

def TouchCWDFiles(variable_to_save : list, file_path):
    files = c_functions.lscwd(file_path.encode('utf-8'))
    for i in range(files.count):
        variable_to_save.append(files.names[i].decode('utf-8'))
