# Agent Source Settings & Execution Protocol

This document establishes the systemic boundaries, repository ingestion rules, and operational execution commands for any AI Agent working within this project workspace.

## 1. Repository Ingestion & File Reading Priority
When initialized or given an orchestration task, you must scan and understand the repository layout according to this explicit hierarchy:

1. **Tier 1 (Critical Context - Read First):**
   - `.ai/agent_needed_info.md` (System context, technical stack, architecture mapping)
   - `.ai/agent_instructions.md` (Behavioral, structural, and framework rules)
2. **Tier 2 (Entry Points & Entry Hooks):**
   - `run.py` (Application initialization and core execution thread)
   - `interface.py` (To run the application but with a welcome screen at first)
   - `welcome.py` (To run at how a user is expected to see the app (with projects choosing layout)).
   - Custom entry modules or core layout initializers.
3. **Tier 3 (Core Core Components):**
   - Custom widgets, threaded worker modules, syntax engines, and editor logic.
4. **Tier 4 (Supporting Files):**
   - Stylesheets (`.qss`), assets, configurations, setup files, and test suites.

## 2. File Handling & Modification Rules
- **Verify Existence:** Always cross-reference imports across the filesystem before generating modifications. Never assume an internal module exists without verifying its declaration in the file tree.
- **Deep Scan Requirement:** For complex tasks, read the entirety of target implementation files. Do not guess behavior based on method headers or truncated signatures.
- **Excluded Paths:** Do NOT ingest or parse `__pycache__/`, `.git/`, Virtual Environments (`.venv/`, `env/`, `conda-env/`), or binary build distributions unless explicitly requested.

## 3. Core System Commands
When responding to the developer, align your underlying action plan to these core execution paths:
- `/audit`: Perform a strict review of a file or directory focusing heavily on threading safety and performance.
- `/refactor`: Restructure a module completely following the non-placeholder and zero-bug rules in `agent_instructions.md`.
- `/feature`: Map out and build a complete end-to-end integration matching the current IDE core architecture.
- `/test`: Analyze test coverage and write deep mock assertions using the guidelines in `additional_instructions.md`.