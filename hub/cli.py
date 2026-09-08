import typer
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .config import load_config, save_config, CONFIG_PATH
from .executor import execute_action

app = typer.Typer()
console = Console()

@app.command()
def init():
    """Создаёт пример конфига ~/.config/hub/config.yaml"""
    config_path = CONFIG_PATH
    if config_path.exists():
        overwrite = typer.confirm("Конфиг уже существует. Перезаписать?")
        if not overwrite:
            return
    example = {
        "commands": {
            "school": {
                "description": "Zoom + Schoology",
                "actions": [
                    {"type": "browser", "urls": ["https://zoom.us/j/123", "https://lms.lausd.net/"], "browser": "brave"}
                ],
                "icon_type": "emoji",
                "icon_value": "🏫",
                "color": "#3b82f6"
            },
            "code": {
                "description": "Zed + GitHub",
                "actions": [
                    {"type": "app", "command": "zed"},
                    {"type": "browser", "urls": ["https://github.com"], "browser": "brave"}
                ],
                "icon_type": "emoji",
                "icon_value": "💻",
                "color": "#10b981"
            },
            "chill": {
                "description": "YouTube",
                "actions": [
                    {"type": "browser", "urls": ["https://youtube.com"], "browser": "brave"}
                ],
                "icon_type": "emoji",
                "icon_value": "😎",
                "color": "#f59e0b"
            },
            "hwork": {
                "description": "Schoology + Grok + ChatGPT + DeepSeek",
                "actions": [
                    {"type": "browser", "urls": [
                        "https://lms.lausd.net/",
                        "https://grok.x.ai",
                        "https://chatgpt.com",
                        "https://chat.deepseek.com"
                    ], "browser": "brave"}
                ],
                "icon_type": "emoji",
                "icon_value": "📚",
                "color": "#8b5cf6"
            }
        }
    }
    save_config(example)
    console.print(f"[green]✅ Конфиг создан: {config_path}[/green]")
    console.print("[yellow]Отредактируй его под себя (например, замени ссылку на Zoom)[/yellow]")

@app.command()
def list():
    """Показывает все доступные команды"""
    config = load_config()
    commands = config.get("commands", {})
    if not commands:
        console.print("[red]Нет команд. Создай их через `hub init` или веб-панель.[/red]")
        return
    table = Table(title="Доступные команды")
    table.add_column("Имя", style="cyan")
    table.add_column("Описание", style="green")
    table.add_column("Иконка", style="magenta")
    for name, cmd in commands.items():
        table.add_row(name, cmd.get("description", ""), cmd.get("icon_value", "📌"))
    console.print(table)

@app.command()
def edit():
    """Открывает конфиг в редакторе по умолчанию"""
    if not CONFIG_PATH.exists():
        console.print("[red]Конфиг не найден. Запусти `hub init`[/red]")
        return
    editor = Path("/usr/bin/nano")  # можно заменить на $EDITOR
    subprocess.call([editor, str(CONFIG_PATH)])

@app.command()
def run(command: str):
    """Выполняет команду по имени"""
    config = load_config()
    cmd_data = config.get("commands", {}).get(command)
    if not cmd_data:
        console.print(f"[red]Команда '{command}' не найдена.[/red]")
        console.print("Используй `hub list` для просмотра всех команд.")
        return
    for action in cmd_data.get("actions", []):
        execute_action(action)
    console.print(f"[green]✅ Команда '{command}' выполнена.[/green]")

@app.command()
def ui(port: int = 8765):
    """Запускает веб-панель с кнопками (GUI)"""
    try:
        import uvicorn
        from .web import app as web_app
        console.print(f"[cyan]🚀 Запуск веб-панели на http://127.0.0.1:{port}[/cyan]")
        uvicorn.run(web_app, host="127.0.0.1", port=port)
    except ImportError:
        console.print("[red]❌ Не установлены зависимости для GUI. Выполни: pip install fastapi uvicorn jinja2[/red]")
        raise

if __name__ == "__main__":
    app()
