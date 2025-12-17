import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.game.game_state import GameState
from src.game.models import World_State, PlayerCharacter, NPC, Quest


def _slug(text: str):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "game"


def _conf_game_dir(game_id: str, root: Path | str = "saves/games") -> Path:
    base = Path(root) / _slug(game_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _write_json(path: Path, data: Dict[str, Any]):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_game(game: GameState, game_id: str, root: Path | str = "saves/games") -> Path:
    """Persist the game into split JSON files under saves/games/<game_id>."""
    if game.world is None:
        raise ValueError("Cannot save: World is empty")

    base = _conf_game_dir(game_id, root)
    timestamp = datetime.utcnow().isoformat()

    _write_json(
        base / "meta.json",
        {
            "game_id": game_id,
            "world_id": getattr(game.world, "world_id", None),
            "saved_at": timestamp,
            "version": "1.0",
            "players": list(game.player_characters.keys()),
            "npcs": list(game.npcs.keys()),
            "quests": list(game.quests.keys()),
        },
    )
    _write_json(base / "world.json", game.world.to_dict())
    _write_json(
        base / "players.json",
        {pc_id: pc.to_dict() for pc_id, pc in (game.player_characters or {}).items()},
    )
    _write_json(
        base / "npcs.json",
        {npc_id: npc.to_dict() for npc_id, npc in (game.npcs or {}).items()},
    )
    _write_json(
        base / "quests.json",
        {qid: quest.to_dict() for qid, quest in (game.quests or {}).items()},
    )
    _write_json(
        base / "initiative.json",
        {
            "order": list(game.initiative_order or []),
            "active_turn_index": int(game.active_turn_index or 0),
        },
    )
    return base


def load_game(game_id: str, root: Path | str = "saves/games"):
    """Load a split save for the given game_id."""
    base = Path(root) / _slug(game_id)
    if not base.exists():
        raise FileNotFoundError(f"No save folder for game id '{game_id}' at {base}")

    def _read(name: str, default=None):
        path = base / name
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    world_data = _read("world.json")
    world = World_State.from_dict(world_data) if world_data else None
    players_data = _read("players.json", {}) or {}
    npcs_data = _read("npcs.json", {}) or {}
    quests_data = _read("quests.json", {}) or {}
    initiative_data = _read("initiative.json", {}) or {}

    players = {pc_id: PlayerCharacter.from_dict(pc) for pc_id, pc in players_data.items()}
    npcs = {npc_id: NPC.from_dict(npc) for npc_id, npc in npcs_data.items()}
    quests = {qid: Quest.from_dict(q) for qid, q in quests_data.items()}

    return (
        world,
        players,
        npcs,
        quests,
        initiative_data.get("order", []),
        int(initiative_data.get("active_turn_index", 0)),
    )
