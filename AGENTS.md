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

## Specific Rules: 
- All other rules are contained inside `.ai/` folder. It contains `styles.md` and `styles.yaml`. 

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
