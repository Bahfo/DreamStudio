import json

data = json.load(open("editor/texteditor/keywords/python.json"))

for key, value in data.items():
    if key == "all_words":
        for word in data["all_words"]:
            print(word)
