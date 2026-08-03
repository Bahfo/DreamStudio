# File for Agents

|**Project**|DreamStudio IDE|
|---|---|
|**Languages**|`Python`,`D-language`|
|**TextEditor**|`Ironica (Custom DreamStudio) TextEditor`|
|**UI Framework**|`PyQt6` and `QScintilla`|

*Critical*: These guidelines MUST be followed at all times.

## Project Invariants
- Some subdirectories may contain their own AGENTS/.AI instructions; follow them when present.
- `.poly` files, if any found, are the build files for the system. These must NOT be updated unless it is explicitly said to update them. 
- `UPDATES.md` is a file that contains all changes or commits that will be added/committed into the repository. 

## Specific Rules: 
- All other rules are contained inside `.ai/` folder. It contains `styles.md` and `styles.yaml`. 
- `UPDATES.md` must be used after each change made. Whenever a change is completely made (*Example*: a bug fixed, a new addition or feature, a crash or a bug-trace are fixed) then, the file must be populated with the change. This file is a metadata file. You must populate each update in the following format: 

```
---
#### Changes in Fix - (FIX_ID)
- Change-1
- Change-2
- ... etc.
#### Notes: ....

Date of Change: X/X/20XX
---
```
- **Tests**: All tests are `.py` files starting with the word `test`. After each change. Run tests accompanying to the change made.

## Mandatory Rules

### After Code Changes
- Provide a detailed execution of tests after running the tests. If any test fails, you MUST provide the fix immediately. 
- Ignore any failed tests that are pre-failing.

### Code Providing
- Read `.ai/` folder for styling rules.
- Auto-format.
- Normalize (structure or whitespace).
- Add a trailing newline at the end of file.
