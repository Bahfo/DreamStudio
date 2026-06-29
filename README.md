###### Current Version: 1.0.2 (Quiet Vally Release)

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

## Using DreamStudio

### For Python Users

You have several options of using DreamStudio. The IDE comes configured for Python mainly. 

When you open DreamStudio, you are guided towards choosing an already made project or creating a new project. Suppose you are creating a new project. 

There are several options. Including: 

1. Python Server with Flask: Create a Python server, powered by *Flask* framework. DreamStudio does the heavy lifting for you, and manages your environment fully.

2. Python Machine Learning Project: Run your machine learning projects easily with Python, with options to use **TensorFlow** or **PyTorch**. The studio has all time-consuming tasks already built, so scientists and programmers can jump right-away into coding.

3. Python User Acitivty Applications for Desktop: You can use PyQt's latest technologies to build your applications for desktop configured for your operating system's environment. Note that the application built is configured by default to be for your native operating system.

4. Python Android Activity Project: Use BeeWare, the native Python builder for Android, with Android SDK, inside DreamStudio, to build your applications for android mobile, we have you set up with emulators needed, required SDKs, and all tools to build your apps on mobile. 

You can also create empty projects and set things up yourself. 

### For C-Plus-Plus: 

C++ Is currently not implemented, but under development. In the future, DreamStudio will also support C++ natively inside it.

### Initializing a New Project: 

This is straight-forward: Initializing a new project is done easily via the setup wizard: 

- Open DreamStudio. 
- Select `New Project`.
- Choose the project you want from templates. 
- Give it a new name (duplicated names inside same directory aren't allowed). Then give it a path. 
- Click `Create` to create the project.

## Marketplace

DreamStudio is also heavily-customized. You can customize the studio and install additional packages, addons, and themes from the marketplace (*the forth option in the leftmost sidebar*). Addons are installed directly from GitHub repository (`Addons-for-DreamStudio`). 

Addons are heavily monitored and checked. If you want to make a new addon, head towards *DreamStudio Documentations* where you can find all needed info.

## Android Apps and Emulation

DreamStudio supports Android activity creation! You can build your app using `BeeWare` framework to create applications natively supported on Android. Thanks to Android's SDK we are able to bring this inside DreamStudio so you have all the tools you need in one place, ready to go.

> [!NOTE]
> Android SDK tools does come by default configured within the studio. If you want a verison of DreamStudio where these tools aren't what you want, or you want custom setup, then install what you want from DSInstaller by navigating to `Install` -> `Advanced Installtion` and choose what you want.

## A Word to Users

Thank you for choosing DreamStudio to build your applications! your support means the world to us. We will continue to ship more features and make the studio a better system for developers of all kinds. Thank you!