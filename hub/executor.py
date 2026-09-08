import os
import shlex
import shutil
import subprocess
import webbrowser
from typing import Dict, Any


def get_app_environment() -> dict[str, str]:
    """Return an environment suitable for launching user applications."""
    env = os.environ.copy()

    home = os.path.expanduser("~")
    user_bin = os.path.join(home, ".local", "bin")

    path_entries = env.get("PATH", "").split(os.pathsep)

    if user_bin not in path_entries:
        path_entries.insert(0, user_bin)

    env["PATH"] = os.pathsep.join(path_entries)

    return env


def find_browser(browser_name: str = "brave") -> str | None:
    """Find an installed browser executable."""
    candidates = [
        browser_name,
        f"{browser_name}-browser",
        browser_name.lower(),
    ]

    env = get_app_environment()

    for cmd in candidates:
        if shutil.which(cmd, path=env["PATH"]):
            return cmd

    return None


def open_browser(urls: list[str], browser: str = "brave"):
    """Open a list of URLs in the selected browser."""
    browser_cmd = find_browser(browser)

    if not browser_cmd:
        for url in urls:
            webbrowser.open(url)
        return

    subprocess.Popen(
        [browser_cmd] + urls,
        env=get_app_environment(),
    )


def run_app(command: str):
    """Launch an application without blocking BioHub."""
    env = get_app_environment()

    try:
        args = shlex.split(command)
        if not args:
            return

        subprocess.Popen(args, env=env)

    except FileNotFoundError:
        print(f"Application not found: {command}")
    except OSError as exc:
        print(f"Failed to launch '{command}': {exc}")


def execute_action(action: Dict[str, Any]):
    """Execute one action from the configuration."""
    act_type = action.get("type")

    if act_type == "browser":
        urls = action.get("urls", [])
        browser = action.get("browser", "brave")

        if urls:
            open_browser(urls, browser)

    elif act_type == "app":
        cmd = action.get("command")

        if cmd:
            run_app(cmd)

    else:
        print(f"Unknown action type: {act_type}")
