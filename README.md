# BioHub

**A lightweight personal command center for Linux.**

BioHub brings your everyday applications, websites, and workflows into one customizable command center — available through the **terminal**, **web dashboard**, and **desktop GUI**.

<p align="center">

**One command. One click. One workflow.**

</p>

---

##  Features

*  **Desktop GUI** for launching workflows
*  **Web dashboard** with interactive controls
*  **Terminal CLI** for fast workflow execution
*  Launch multiple applications with one action
*  Open multiple websites in your preferred browser
*  Combine different actions into a single workflow
*  Custom icons, colors, and descriptions
*  Upload custom PNG icons
*  YAML-based configuration
*  Built specifically for Linux
*  Lightweight and customizable
*  Simple one-command installation

---

##  Quick Install

BioHub can be installed without cloning the repository or manually creating a Python environment.

### Install

```bash
curl -fsSL https://raw.githubusercontent.com/b-1-o/biohub/main/install.sh | bash
```

After installation, update desktop database and run:

```bash
update-desktop-database ~/.local/share/applications
```

The installer creates:

* an isolated Python virtual environment
* the `biohub` command
* the `hub` CLI command
* the `hub-desktop` command
* a desktop application entry

### Requirements

* Linux
* Python **3.10+**
* `curl`

No Git installation is required for the quick installer.

---

##  Uninstall

To remove BioHub:

```bash
curl -fsSL https://raw.githubusercontent.com/b-1-o/biohub/main/uninstall.sh | bash
```

The uninstaller removes the BioHub installation, launchers, and desktop entry.

---

##  Interfaces

BioHub provides three ways to interact with your workflows.

### Terminal

Use the CLI directly:

```bash
hub init
hub list
hub run coding
hub edit
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

The dashboard allows you to create, edit, launch, and manage workflows from your browser.

### Desktop

Launch the desktop application:

```bash
hub-desktop
```

You can also launch **BioHub** directly from your desktop application's menu after installation.

---

## ⚡ Workflows

The main idea behind BioHub is simple:

> **Turn repetitive computer workflows into one-click actions.**

A workflow can contain multiple actions.

For example, a single `coding` workflow could:

1. Launch your code editor
2. Open GitHub
3. Open ChatGPT
4. Open your documentation
5. Start another application

Instead of repeating these actions manually every day, BioHub lets you define them once and launch them together.

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

Then run:

```bash
hub run coding
```

---

##  Browser Actions

BioHub can open multiple URLs as part of one workflow.

```yaml
- type: browser
  urls:
    - https://github.com
    - https://chatgpt.com
    - https://example.com
  browser: brave
```

This makes it possible to create workflows for development, school, work, gaming, research, or any other repetitive setup.

---

##  Application Actions

Launch desktop applications directly from a workflow:

```yaml
- type: app
  command: zed
```

You can combine application actions with browser actions and other supported actions.

---

##  Customization

Each workflow can have its own:

* Name
* Description
* Icon
* Icon type
* Color
* Actions

BioHub also supports custom PNG icons through the web dashboard.

This allows you to build a command center around the applications and workflows you actually use.

---

##  Configuration

BioHub uses YAML for configuration.

The default configuration is stored in:

```text
~/.config/hub/config.yaml
```

Initialize it with:

```bash
hub init
```

Edit it with:

```bash
hub edit
```

---

##  Manual Installation

If you prefer installing BioHub directly from source:

```bash
git clone https://github.com/b-1-o/biohub.git
cd biohub

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

Then initialize BioHub:

```bash
hub init
```

---

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
│   ├── static/
│   └── templates/
│       └── dashboard.html
│
├── install.sh
├── uninstall.sh
├── pyproject.toml
├── README.md
└── .gitignore
```

---

##  Tech Stack

| Technology | Purpose            |
| ---------- | ------------------ |
| Python     | Core application   |
| Typer      | Terminal CLI       |
| FastAPI    | Web backend        |
| Uvicorn    | ASGI server        |
| Jinja2     | Web templates      |
| PyYAML     | Configuration      |
| Pydantic   | Data validation    |
| Rich       | Terminal interface |
| PySide6    | Desktop GUI        |

---

## 🐧 Linux First

BioHub is designed primarily for Linux desktops.

The project focuses on integrating with the Linux desktop environment while keeping the application lightweight and easy to customize.

---

##  Roadmap

* [x] Terminal CLI
* [x] Web dashboard
* [x] Desktop GUI
* [x] YAML configuration
* [x] Workflow execution
* [x] Browser actions
* [x] Application actions
* [x] Custom icons
* [x] Linux installer
* [x] Linux uninstaller
* [ ] Custom BioHub application icon
* [ ] Drag-and-drop dashboard customization
* [ ] Command categories and folders
* [ ] Keyboard shortcuts
* [ ] System tray integration
* [ ] More action types
* [ ] Workflow import/export
* [ ] Theme customization
* [ ] Plugin system
* [ ] Cross-platform support

---

##  Contributing

Contributions, ideas, bug reports, and improvements are welcome.

If you find a problem or have an idea for BioHub, feel free to open an issue or submit a pull request.

---

##  License

BioHub is released under the **MIT License**.

---

##  Philosophy

BioHub is not designed to replace your terminal or desktop environment.

It sits on top of them and gives you a convenient visual layer for the commands, applications, websites, and workflows you use most often.

**Your commands. Your workflow. Your command center.**
