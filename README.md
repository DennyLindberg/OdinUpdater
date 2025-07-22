# Odin Updater

A Sublime Text plugin for automatically installing and updating Odin and Odin Language Server (OLS) from source. Includes additional commands for adding Odin build systems and source folders to a project.

This plugin was created for personal use while learning Odin and Sublime Text. Feel free to use and modify it as needed.

> **Disclaimer:** Parts of the code were AI-generated and manually rewritten to ensure proper functionality. The README was revised based on generated suggestions for grammar, clarity, and readability.

## Intended Use
- Add Odin Updater plugin to Sublime Text 4 User Folder
- Create a new sublime project for your Odin project
- Enable LSP globally and for your project if you are going to use OLS
- Use Odin Updater to:
    - Install or update Odin and OLS whenever you need the latest version
    - Add Odin build system to your project
    - Add Odin source folders for easy access

## Installation

1. Copy files or clone the repository to **Packages/OdinUpdater**
    - Use Preferences > Browse Packages... in Sublime to navigate there
2. Access commands under **Tools > Packages > Odin Updater**
    - Commands are listed in the next section
3. Configure settings and keybinds under **Preferences > Package Settings > Odin Updater**
    - The file is auto-generated when running OdinUpdater for the first time

## Commands

**Tools > Packages > Odin Updater > Update Odin Compiler and OLS**

- Creates `OdinUpdater.sublime-settings` on first run
    - Update these paths to match your system setup. Installing OLS is optional
- Clones git repositories for Odin and OLS
- Pulls latest changes and selects latest dev tag for Odin
- Builds executables in release mode
- Displays latest commit info on success

**Tools > Packages > Odin Updater > Add Odin build system to project**

- Adds build system with variants (executable name uses project name):
  - `Build and Run (temporary exe)` (odin run .)
  - `Build and Run` (odin build . && start exe)
  - `Build Only` (odin build)
- Includes build output `file_regex` based on Karl Zylinski's tutorials

**Tools > Packages > Odin Updater > Add Odin source folders to project [base, core, examples, vendor]**

- Adds Odin source folders for reference (enables easy search, LSP support, etc.)

## Recommended Sublime Packages

- [Odin](https://packagecontrol.io/packages/Odin) for Syntax highlighting
- [LSP](https://packagecontrol.io/packages/LSP) for Odin Language Server to work in Sublime Text
- [Visual Studio Dark (color scheme)](https://packagecontrol.io/packages/Visual%20Studio%20Dark) because I like it

## Requirements

- Sublime Text 3 or 4
- Git (for cloning and updating repositories)
- MSVC Build tools for compiling Odin and OLS (pick one option)
    - [Visual Studio (recommended)](https://visualstudio.microsoft.com/)
    - [MSVC PortableBuildTools](https://github.com/Data-Oriented-House/)
    - [MSVC Python installation script by mmozeiko](https://gist.github.com/mmozeiko/7f3162ec2988e81e56d5c4e22cde9977)
