# DreamScript: A Simple Scripting Language for DreamStudio

DreamScript is a simple and command-behavioral scirpting language built for DreamStudio.

## Table of Contents: 
- Introduction.
- Usage.
- Examples.

## Introduction
DreamScript comes by default with DreamStudio, it is a simple scripting language that is used for DreamStudio and automation tasks. 

DreamScript has the extension `.dscript`. Here is a glance of how the language looks like: 
```dscript
$x = 12;
$DIRECTORY = "/home/userOne/Desktop"

if (x == 12) then PRINT "EQUAL"
if (DIRECTORY = CWD) then PRINT "This is the cwd."
```

## Usage

You can use DreamScript from inside of DreamStudio while working with your solution, and write it in scripted files, or use it within the Command Line Interface from DayDream terminal, which supports command-by-command typing of DreamScript.

## Examples

Here are some examples of how DreamScript looks like: 

#### 1. Deleting Files Recursively in Your Machine
```dscript
$CURRENT_DIRECTORY = "/home/userOne/Desktop/TempFolder"
DELETEREC CURRENT_DIRECTORY
```

#### 2. Automated Scanner for Devices in a Network
```dscript
SWEEPSNET  # Returns all active devices in the network
```

#### 3. Network Scanner to Get Advanced Info About Users in Network
```dscript
SWEEPSNET --s
```