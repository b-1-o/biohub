from pydantic import BaseModel, Field
from typing import List, Optional, Union

class Action(BaseModel):
    type: str  # "browser" или "app"
    urls: Optional[List[str]] = None
    command: Optional[str] = None
    browser: Optional[str] = "brave"

class Command(BaseModel):
    description: Optional[str] = ""
    actions: List[Action]
    icon: Optional[str] = "📌"
    color: Optional[str] = "#3b82f6"

class Config(BaseModel):
    commands: dict[str, Command]
