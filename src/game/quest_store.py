# src/game/quest_store.py

from __future__ import annotations

from pathlib import Path
from typing import Dict

import json

from src.game.models import Quest

SAVES_DIR = Path("saves")


def _quests_file_path(world_id: str) -> Path:
    SAVES_DIR.mkdir(exist_ok=True)
    return SAVES_DIR / f"{world_id}_quests.json"


def save_quests(world_id: str, quests: Dict[str, Quest]) -> None:
    """
    Save all quests for a given world_id to disk.
    """
    path = _quests_file_path(world_id)
    data = {qid: q.to_dict() for qid, q in quests.items()}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_quests(world_id: str) -> Dict[str, Quest]:
    """
    Load all quests for a given world_id from disk.
    Returns an empty dict if no quests file exists.
    """
    path = _quests_file_path(world_id)
    if not path.exists():
        return {}

    raw = json.loads(path.read_text(encoding="utf-8"))
    quests: Dict[str, Quest] = {}
    for qid, data in raw.items():
        q = Quest.from_dict(data)
        quests[qid] = q
    return quests
