import json
from pathlib import Path
from typing import Dict

from src.game.models import PlayerCharacter

SAVE_DIR = Path("saves")
SAVE_DIR.mkdir(exist_ok=True)


def _world_players_path(world_id: str) -> Path:
    return SAVE_DIR / f"{world_id}_players.json"


def load_player_characters(world_id: str) -> Dict[str, PlayerCharacter]:
    """
    Load all PCs for a given world as a dict {pc_id: PlayerCharacter}.
    """
    path = _world_players_path(world_id)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    pcs = {}
    for pc_id, payload in data.items():
        pcs[pc_id] = PlayerCharacter.from_dict(payload)
    return pcs


def save_player_characters(world_id: str, pcs: Dict[str, PlayerCharacter]) -> None:
    """
    Save all PCs for a given world from a dict {pc_id: PlayerCharacter}.
    """
    path = _world_players_path(world_id)
    data = {pc_id: pc.to_dict() for pc_id, pc in pcs.items()}

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
