<h1 align="left" style="font-size: 40px;">DreamStudio IDE</h1>

![Static Badge](https://img.shields.io/badge/Company-Excellent_TechStacks-006FCD?style=for-the-badge)
![Static Badge](https://img.shields.io/badge/Author-Bahaa_Nofal-CBA317?style=for-the-badge)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

DreamStudio is an open-source Integrated Development Environment developed by *Excellent TechStacks* (known as _EX Techs_). It is the basis for Excellent TechStacks Integrated Platform Development Environment (IPDE).

If you are new to the project and would like to get started quickly, please read the documentaiton provided in notebook forms (`.ipynb` format).

You can see in the following picture **DreamStudio** in action.

![DreamStudio in Action](assets/logos/dreamstudio_in_action.png)

---

## Getting the Source Code
The repository is available from at https://github.com/Bahfo/DreamJetPack-Official_Repository, which can be cloned or downloaded as a zip file. The *main* (default) branch contains the source code of the repository. 

Alternatively, follow the steps shown below in a terminal:

```bash
git clone https://github.com/Bahfo/DreamJetPack-Official_Repository
cd DreamJetPack-Official_Repository
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

To run building, type the following command:

```bash
./build.sh  # If you are on UNIX Systems
build.bat   # For Windows
```

> [!TIP]
> You can also run with specific configurations for building. For example, you can build explicitly without a specific feature you do not want the IDE to have. The notebook's documentation provides a full article about it.

--- 

## Additional Information

### Marketplace

The marketplace offers extensions that you can add into DreamStudio. Basically, all marketplace extensions are available in one repository available on GitHub. The installation uses `clone` and then a building utility handles building the extension's source code. 

The marketplace is completely safe and is 100% secure to be trusted. All the addons and extensions that a developer might add are reviewed carefully inside the marketplace. 

You can if you want customize the IDE as you want or make a new addon or extension by using the free API that DreamStudio offers, read the notebook's documentation for more details on that.

### Ether AI

Ether AI is an additional **Large Language Model (LLM)** that DreamStudio offers. Ether AI window can be in two modes: chatting and agentic. Chatting simply can be helpful around general usage and defining goals or setting up plans. While agentic model is all about building, reading files, modifying files, etc. Ether AI in DreamStudio does not come natively built inside the studio.

--- 

## Additional Information

This `README` file is an introduction and quick setup guide for installing and building DreamStudio, for better info with more explanations, additional informations, keybinding settings, and others, read the provided notebook documentation.