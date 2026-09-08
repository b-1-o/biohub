import os
import yaml
from pathlib import Path
from .models import Config, Command, Action

CONFIG_PATH = Path.home() / ".config" / "hub" / "config.yaml"

def ensure_config_dir():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_config() -> dict:
    ensure_config_dir()
    if not CONFIG_PATH.exists():
        return {"commands": {}}
    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
    return data

def save_config(data: dict):
    ensure_config_dir()
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

def get_command(name: str) -> dict | None:
    config = load_config()
    return config.get("commands", {}).get(name)

def add_command(name: str, cmd_dict: dict):
    config = load_config()
    config.setdefault("commands", {})[name] = cmd_dict
    save_config(config)

def delete_command(name: str):
    config = load_config()
    if name in config.get("commands", {}):
        del config["commands"][name]
        save_config(config)
