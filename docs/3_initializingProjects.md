# Initializing a Project

To initialize a project, you must open DreamStudio first.

Once you open DreamStudio, it greets you with the **Start Window**, a
project manager landing page with two tabs on the left sidebar.

## Create a New Solution

1. On the **Create a New Solution** tab, pick a project type from the
   templates list (each entry is read from `manifests/projects/*.yaml` —
   adding a YAML file there registers a new template).
2. Click `Next`, name the solution and choose the folder where it should
   live.
3. Click `Create and Open`. The IDE starts with the newly created solution
   folder, and a blocking progress dialog scaffolds the project structure
   (virtual environment, template files and dependency installation).
   You can press `Cancel` at any time; the created structure is kept as-is.

## Open an Existing Solution

On the **Open an Existing Solution** tab you can:

- Reopen a recently used solution (highlighted list entry, newest first).
- Browse for a folder with `Browse for folder...`.

Any folder can be opened as a solution even without a marker; DreamStudio
remembers it in the recent list.

> A solution is simply a folder containing a `.ds/solution.yaml` marker that
> records its name and project type.

## Within the IDE

- `File > New Project` reopens the Start Window on the Create tab.
- `File > Open Recent Project` reopens the Start Window on the Open tab.
- The Quick Start home screen offers a clickable `New Project` shortcut.