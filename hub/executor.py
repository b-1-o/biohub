import subprocess
import shutil
import webbrowser
from typing import Dict, Any

def find_browser(browser_name: str = "brave") -> str | None:
    """Ищет исполняемый файл браузера в системе."""
    candidates = [browser_name, f"{browser_name}-browser", browser_name.lower()]
    for cmd in candidates:
        if shutil.which(cmd):
            return cmd
    return None

def open_browser(urls: list[str], browser: str = "brave"):
    """Открывает список URL в указанном браузере."""
    browser_cmd = find_browser(browser)
    if not browser_cmd:
        # fallback на xdg-open или системный браузер по умолчанию
        for url in urls:
            webbrowser.open(url)
        return
    # Запускаем браузер с несколькими вкладками
    subprocess.Popen([browser_cmd] + urls)

def run_app(command: str):
    """Запускает приложение (блокирующий вызов)."""
    subprocess.Popen(command.split())

def execute_action(action: Dict[str, Any]):
    """Выполняет одно действие из конфига."""
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
        print(f" Неизвестный тип действия: {act_type}")
