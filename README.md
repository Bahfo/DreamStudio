<h1 align="left" style="font-size: 40px;">DreamStudio IDE</h1>

![Static Badge](https://img.shields.io/badge/Company-Excellent_TechStacks-006FCD?style=for-the-badge)
![Static Badge](https://img.shields.io/badge/Author-Bahaa_Nofal-CBA317?style=for-the-badge)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

DreamStudio is an open-source Integrated Development Environment developed by *Excellent TechStacks* (known as _EX Techs_). It is the basis for Excellent TechStacks Integrated Platform Development Environment (IPDE).

If you are new to the project and would like to get started quickly, please read the documentaiton provided in either notebook forms (`.ipynb` format) or in plain ddocs format (`.dsman` format).

![DreamStudio in Action](assets/logos/dreamstudio_in_action.png)

## Getting the Source Code
The repository is available from the [GitHub Repository][https://github.com/Bahfo/DreamJetPack-Official_Repository], which can be cloned or downloaded as a zip file. The *main* (default) branch contains the source code of the repository. 

Alternatively, follow the steps shown below in a terminal:

```
git clone https://github.com/Bahfo/DreamJetPack-Official_Repository
cd DreamJetPack-Official_Repository
```

> [!TIP]
> To download only the latest version, add `--depth 1` option after `clone`. 

> [!NOTE]
> The IDE is written in Python and thus expects certain required libraries to build and run successfully. Run the following commands in a terminal to do that:

### Windows Specific:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux/MacOS
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running DreamStudio using Contained Environment and Python
To run DreamStudio directly using Python. One of several files can do the job depending on what is your primary need:
1. To skip the welcome and build window and enter the IDE directly, run `python run.py` on Windows or `python3 run.py` on Linux/MacOS.
2. To show the welcome interface then the IDE directly, run `python welcome.py` on Windows or `python3 welcome.py` on Linux/MacOS.
3. To run all features and start the IDE as it must start, run `python interface.py` on Windows or `python3 interface.py` on Linux/MacOS.

## Documentation
If you want to read the documentaiton, get started, or find the full capabilities of DreamStudio, please head to (/ddocs) directory, which contains all required files to get you started.

## Contributing
Are you a contributor? head to (/contribution) directory and read the terms and conditions to get started.