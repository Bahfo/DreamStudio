###### Current Version: 1.1.0 (Quiet Vally Release)

<h1 align="left" style="font-size: 40px;">DreamStudio IDE</h1>

![Static Badge](https://img.shields.io/badge/Company-Excellent_TechStacks-006FCD?style=for-the-badge)
![Static Badge](https://img.shields.io/badge/Author-Bahaa_Nofal-CBA317?style=for-the-badge)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![](https://img.shields.io/badge/C%2B%2B-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)

DreamStudio is an open-source Integrated Development Environment developed by *Excellent TechStacks* (known as _EX Techs_). It is the basis for Excellent TechStacks Integrated Platform Development Environment (IPDE).

If you are new to the project and would like to get started quickly, please read the documentaiton provided in notebook forms (`.ipynb` format).

You can see in the following picture **DreamStudio** in action.

---

## Getting the Source Code
The repository is available from at https://github.com/Bahfo/DreamJetPack-Official_Repository, which can be cloned or downloaded as a zip file. The *main* (default) branch contains the source code of the repository. 

Alternatively, follow the steps shown below in a terminal:

```bash
git clone https://github.com/Bahfo/DreamStudio
cd DreamStudio
```

> [!TIP]
> If the complete repository history is not required, or you want a faster download, you can access the latest-only repository changes by adding to your command `--depth 1` after the `clone` command.

### Installing Required Dependencies
DreamStudio requires additional configuration to run successfully separate from the main repository. 

Firstly you should build a virtual environment and install required libraries and frameworks inside. To do that, run the following commands one after another: 

```bash
# Specific Commands for UNIX Systems
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
```powershell
# For Windows, see the following
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

DreamStudio also relies on backend services that should be available such as the D-Language Compiler. Make sure you have it downloaded. You can type the following on a terminal to check: 

```bash
dmd --version # Explicitly the DMD Compiler is Required
```

>[!IMPORTANT]
> Explicitly, we prefer you have the `dmd` compiler downloaded for D-Language. Other compilers are accepted but are not supported. 

The final tool you should have is the C-Language Compiler (`GCC`). You can check if it is available on your machine or not by running the following command: 

```bash
gcc --version # Explicitly the GCC Compiler is Required
```

Just like with D-Lang, you are free to use any C-Language Compiler, but we support `GCC` for this operation.

--- 

## Building DreamStudio

DreamStudio has a build tool in a script format available too inside the repository, you do not need to type-in commands to build the repository by hand. Just make sure you have the prerequisties from previous steps ready, and that the Python's Virtual Environment (venv) is available and activated.

> [!TIP]
> You can also run with specific configurations for building. For example, you can build explicitly without a specific feature you do not want the IDE to have. The notebook's documentation provides a full article about it.

--- 

## A Word to Users

Thank you for choosing DreamStudio to build your applications! your support means the world to us. We will continue to ship more features and make the studio a better system for developers of all kinds. Thank you!