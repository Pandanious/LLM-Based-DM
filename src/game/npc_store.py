from pathlib import Path
import json
from typing import Dict

from src.game.models import NPC

BASE_DIR = Path(__file__).resolve().parents[2]
NPC_SAVE_DIR = BASE_DIR / "saves" / "npcs"


def _world_npc_path(world_id: str) -> Path:
    return NPC_SAVE_DIR / f"{world_id}_npcs.json"

def save_npcs(world_id: str, npcs: Dict[str, NPC]) -> None:
    NPC_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    path = _world_npc_path(world_id)
    data = {npc_id: npc.to_dict() for npc_id, npc in npcs.items()}
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_npcs(world_id: str) -> Dict[str, NPC]:
    path = _world_npc_path(world_id)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    npcs: Dict[str, NPC] = {}
    for npc_id, npc_data in raw.items():
        npcs[npc_id] = NPC.from_dict(npc_data)
    return npcs