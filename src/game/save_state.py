import json
from pathlib import Path
from typing import Optional
from src.game.models import World_State

SAVE_DIR = Path("saves")
SAVE_DIR.mkdir(exist_ok=True)


def save_world_state(world: World_State):
    path = SAVE_DIR / f"{world.world_id}.json"
    data = world.to_dict()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def load_world_state(world_id: str):
    path = SAVE_DIR / f"{world_id}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return World_State.from_dict(data)
