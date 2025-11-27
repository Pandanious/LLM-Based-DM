import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from src.game.game_state import GameState
from src.game.models import World_State, PlayerCharacter, NPC, Quest


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "game"


def save_world_bundle(game: GameState, dest_dir: Path | str = "saves/bundles") -> Path:
    """
    Save the entire game state (world, PCs, NPCs, quests, initiative) into a single JSON bundle.
    Returns the path to the saved file.
    """
    if game.world is None:
        raise ValueError("Cannot save bundle: world is missing.")

    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    player_names = "-".join(_slug(pc.player_name) for pc in game.player_characters.values()) or "no_players"
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp}_{player_names}.json"
    bundle_path = dest / filename

    data: Dict[str, Any] = {
        "saved_at": timestamp,
        "world": game.world.to_dict() if hasattr(game.world, "to_dict") else {},
        "players": {pc_id: pc.to_dict() for pc_id, pc in (game.player_characters or {}).items()},
        "npcs": {npc_id: npc.to_dict() for npc_id, npc in (game.npcs or {}).items()},
        "quests": {qid: quest.to_dict() for qid, quest in (game.quests or {}).items()},
        "initiative_order": list(game.initiative_order or []),
        "active_turn_index": game.active_turn_index,
    }

    bundle_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return bundle_path


def save_world_seed_bundle(game: GameState, dest_dir: Path | str = "saves/bundles") -> Path:
    """
    Save a deterministic bundle keyed to the world + players so you can reload
    without re-running world generation. Overwrites if the same world/players
    combination is saved again.
    """
    if game.world is None:
        raise ValueError("Cannot save bundle: world is missing.")

    world_slug = _slug(getattr(game.world, "title", "") or game.world.world_id)
    players = list(getattr(game.world, "players", []) or game.player_names or [])
    players_slug = "-".join(_slug(p) for p in players) or "no_players"

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    filename = f"{world_slug}_{players_slug}.json"
    bundle_path = dest / filename

    data: Dict[str, Any] = {
        "saved_at": datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S"),
        "world": game.world.to_dict() if hasattr(game.world, "to_dict") else {},
        "players": {pc_id: pc.to_dict() for pc_id, pc in (game.player_characters or {}).items()},
        "npcs": {npc_id: npc.to_dict() for npc_id, npc in (game.npcs or {}).items()},
        "quests": {qid: quest.to_dict() for qid, quest in (game.quests or {}).items()},
        "initiative_order": list(game.initiative_order or []),
        "active_turn_index": game.active_turn_index,
    }

    bundle_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return bundle_path


def load_world_bundle(path_or_bytes: Path | str | bytes) -> Tuple[World_State, Dict[str, PlayerCharacter], Dict[str, NPC], Dict[str, Quest], list, int]:
    """
    Load a bundle produced by save_world_bundle and return its components.
    """
    if isinstance(path_or_bytes, (str, Path)):
        raw = Path(path_or_bytes).read_text(encoding="utf-8")
    else:
        raw = path_or_bytes.decode("utf-8")

    data = json.loads(raw)

    world = World_State.from_dict(data["world"])
    players = {pc_id: PlayerCharacter.from_dict(pc_data) for pc_id, pc_data in data.get("players", {}).items()}
    npcs = {npc_id: NPC.from_dict(npc_data) for npc_id, npc_data in data.get("npcs", {}).items()}
    quests = {qid: Quest.from_dict(q_data) for qid, q_data in data.get("quests", {}).items()}
    initiative_order = data.get("initiative_order", [])
    active_turn_index = int(data.get("active_turn_index", 0))

    return world, players, npcs, quests, initiative_order, active_turn_index
