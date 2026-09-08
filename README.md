# BioHub – Personal Command Center

**BioHub** is a lightweight personal command center for Linux designed to launch your everyday workflows from one place.

It combines a **terminal CLI**, a **web dashboard**, and a **desktop GUI** into a customizable workspace inspired by the simplicity of a Stream Deck.

##  Features

*  **Launch workflows from the terminal**
*  **Web dashboard** with interactive command buttons
*  **Desktop GUI** for launching workflows
*  **Create and edit commands** directly from the web interface
*  **Open multiple URLs** in your preferred browser
*  **Launch desktop applications**
*  **Custom icons and colors** for commands
*  **Upload custom PNG icons**
*  **YAML-based configuration**
*  **Combine multiple actions into a single workflow**
*  **Linux-focused and lightweight**
*  **Designed to be easily customizable and extensible**

##  How It Works

A BioHub command is a collection of actions.

For example, one button can:

1. Launch Zed
2. Open GitHub
3. Open your school website
4. Open ChatGPT
5. Start another application

Instead of running each command manually, you can create a single workflow and launch everything with one click.

### Example

```yaml
commands:
  coding:
    description: "Open my coding environment"
    actions:
      - type: app
        command: zed

      - type: browser
        urls:
          - https://github.com
          - https://chatgpt.com
        browser: brave

    icon_type: emoji
    icon_value: "💻"
    color: "#10b981"
```

##  Interfaces

### Terminal

Use BioHub directly from the command line:

```bash
hub list
hub run coding
hub edit
hub init
```

### Web Dashboard

Start the local web interface:

```bash
hub ui
```

Then open:

```text
http://127.0.0.1:8765
```

The dashboard provides an interactive interface for launching, creating, editing, and deleting workflows.

### Desktop GUI

BioHub also provides a desktop entry point:

```bash
hub-desktop
```

##  Installation

### Requirements

* Linux
* Python 3.10+
* pip
* Git

### Install from source

```bash
git clone https://github.com/b-1-o/biohub.git
cd biohub

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

Initialize the default configuration:

```bash
hub init
```

Your configuration will be created at:

```text
~/.config/hub/config.yaml
```

##  Quick Start

After installation:

```bash
hub init
```

View your available workflows:

```bash
hub list
```

Run a workflow:

```bash
hub run coding
```

Edit your configuration:

```bash
hub edit
```

Start the web dashboard:

```bash
hub ui
```

Or launch the desktop application:

```bash
hub-desktop
```

##  Actions

BioHub workflows can combine different types of actions.

### Open applications

```yaml
- type: app
  command: zed
```

### Open websites

```yaml
- type: browser
  urls:
    - https://github.com
    - https://chatgpt.com
  browser: brave
```

Multiple actions can be combined into a single workflow.

##  Customization

Each command can have its own:

* Name
* Description
* Icon
* Icon type
* Color
* Actions

BioHub also supports uploading custom PNG icons through the web interface.

This makes it possible to build a personalized dashboard around your own workflow.

##  Project Structure

```text
biohub/
├── hub/
│   ├── cli.py
│   ├── config.py
│   ├── desktop.py
│   ├── executor.py
│   ├── models.py
│   ├── web.py
│   └── templates/
│       └── dashboard.html
│
├── pyproject.toml
├── README.md
└── .gitignore
```

##  Tech Stack

* **Python**
* **Typer** – CLI
* **FastAPI** – Web API
* **Uvicorn** – ASGI server
* **Jinja2** – Web templates
* **PyYAML** – Configuration
* **Pydantic** – Data validation
* **Rich** – Terminal UI
* **PySide6** – Desktop GUI

##  Philosophy

BioHub is built around a simple idea:

> **Turn repetitive computer workflows into one-click actions.**

Instead of remembering commands, opening applications one by one, and navigating through the same websites every day, BioHub lets you define a workflow once and launch it whenever you need it.

##  Roadmap

Planned improvements may include:

* [ ] Drag-and-drop dashboard customization
* [ ] Command categories and folders
* [ ] Keyboard shortcuts
* [ ] System tray integration
* [ ] More action types
* [ ] Workflow import/export
* [ ] Theme customization
* [ ] Better desktop integration
* [ ] Plugin system
* [ ] Cross-platform support

##  License

BioHub is released under the **MIT License**.

---

###  Why BioHub?

BioHub is not intended to replace your terminal or desktop environment.

It sits on top of them and provides a convenient visual layer for the commands and workflows you use most often.

**Your commands. Your workflow. Your command center.**
