import os
import yaml
import jinja2
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Union
import subprocess
import webbrowser
import shutil
import tempfile

from .config import load_config, save_config
from .executor import execute_action

app = FastAPI()
templates = Jinja2Templates(directory="hub/templates")
app.mount("/static", StaticFiles(directory="hub/static"), name="static")

# Модель для API
class ActionModel(BaseModel):
    type: str
    urls: Optional[List[str]] = None
    command: Optional[str] = None
    browser: Optional[str] = "brave"

class CommandModel(BaseModel):
    name: str
    description: Optional[str] = ""
    actions: List[ActionModel]
    icon_type: Optional[str] = "emoji"
    icon_value: Optional[str] = "📌"
    color: Optional[str] = "#3b82f6"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    commands = config.get("commands", {})

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"commands": commands},
    )

@app.get("/api/commands")
async def get_commands():
    config = load_config()
    return config.get("commands", {})

@app.post("/api/commands/{name}/run")
async def run_command(name: str):
    config = load_config()
    cmd = config.get("commands", {}).get(name)
    if not cmd:
        raise HTTPException(404, "Command not found")
    for action in cmd.get("actions", []):
        execute_action(action)
    return {"status": "ok", "name": name}

@app.post("/api/commands")
async def add_command(cmd: CommandModel):
    config = load_config()
    commands = config.setdefault("commands", {})
    commands[cmd.name] = {
        "description": cmd.description or "",
        "actions": [a.dict(exclude_none=True) for a in cmd.actions],
        "icon_type": cmd.icon_type or "emoji",
        "icon_value": cmd.icon_value or "📌",
        "color": cmd.color or "#3b82f6"
    }
    save_config(config)
    return {"status": "ok"}

@app.put("/api/commands/{name}")
async def update_command(name: str, cmd: CommandModel):
    config = load_config()
    if name not in config.get("commands", {}):
        raise HTTPException(404, "Command not found")
    # удаляем старую и создаём новую
    del config["commands"][name]
    config["commands"][cmd.name] = {
        "description": cmd.description or "",
        "actions": [a.dict(exclude_none=True) for a in cmd.actions],
        "icon_type": cmd.icon_type or "emoji",
        "icon_value": cmd.icon_value or "📌",
        "color": cmd.color or "#3b82f6"
    }
    save_config(config)
    return {"status": "ok"}

@app.delete("/api/commands/{name}")
async def delete_command(name: str):
    config = load_config()
    if name not in config.get("commands", {}):
        raise HTTPException(404, "Command not found")
    del config["commands"][name]
    save_config(config)
    return {"status": "ok"}

@app.post("/api/commands/{name}/icon")
async def upload_icon(name: str, file: UploadFile = File(...)):
    if not file.filename.endswith('.png'):
        raise HTTPException(400, "Только PNG-файлы разрешены")
    config = load_config()
    if name not in config.get("commands", {}):
        raise HTTPException(404, "Command not found")
    
    icon_dir = Path(__file__).parent / "static" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    file_path = icon_dir / f"{name}.png"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    config["commands"][name]["icon_type"] = "image"
    config["commands"][name]["icon_value"] = f"{name}.png"
    save_config(config)
    return {"status": "ok", "icon": f"{name}.png"}

@app.delete("/api/commands/{name}/icon")
async def delete_icon(name: str):
    config = load_config()
    if name not in config.get("commands", {}):
        raise HTTPException(404, "Command not found")
    icon_path = Path(__file__).parent / "static" / "icons" / f"{name}.png"
    if icon_path.exists():
        icon_path.unlink()
    config["commands"][name]["icon_type"] = "emoji"
    config["commands"][name]["icon_value"] = "📌"
    save_config(config)
    return {"status": "ok"}
