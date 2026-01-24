import ctypes

lib = ctypes.CDLL(r"C:\Users\Bahaa\Desktop\ExoSystem\DreamStudio\searchfile\src\search_engine.dll")
lib.list_directory.argtypes = [ctypes.c_char_p]
lib.list_directory.restype = ctypes.c_char_p

lib.search_files.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
lib.search_files.restype = ctypes.c_char_p

print(lib.list_directory(b"C:\\Users\\Bahaa\\Desktop"))

# Search by name
print(lib.search_files(b"C:\\Users\\Bahaa\\Desktop", b"report", 1).decode())

# Search by extension
print(lib.search_files(b"C:\\Users\\Bahaa\\Desktop", b".txt", 2).decode())

# Search by path
print(lib.search_files(b"C:\\Users\\Bahaa\\Desktop", b"Documents", 3).decode())
