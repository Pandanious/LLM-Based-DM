from __future__ import annotations

from typing import List

from src.agent.types import Message
from src.game.game_state import GameState


def _current_actor_label(game: GameState):
    if not game.initiative_order or not game.player_characters:
        return "none set"
    idx = getattr(game, "active_turn_index", 0)
    if idx >= len(game.initiative_order):
        idx = 0
    pc_id = game.initiative_order[idx]
    pc = game.player_characters.get(pc_id)
    if not pc:
        return "none set"
    return f"{pc.player_name} as {pc.name}"


def _initiative_order_label(game: GameState):
    if not game.initiative_order or not game.player_characters:
        return "unset"
    names = [
        game.player_characters.get(pid).name
        for pid in game.initiative_order
        if game.player_characters.get(pid)
    ]
    return " > ".join(names) if names else "unset"


def _quest_labels(game: GameState, limit: int = 3):
    quests = getattr(game, "quests", {}) or {}
    if not quests:
        return []
    labels = []
    for quest in quests.values():
        title = getattr(quest, "title", "") or "Unnamed quest"
        status = getattr(quest, "status", "available")
        labels.append(f"{title} [{status}]")
    return labels[:limit]


def build_mechanics_prompt(game: GameState):
    
    #Build a concise mechanics/state reminder for the DM to keep dice, turn order, quests, and encounters consistent.
    
    parts: List[str] = []
    parts.append("[MECHANICS] Table rules and current state:")
    parts.append(
        "- Use /action <verb>: <details>. Always request rolls with [ROLL_REQUEST: 1d20+mod | action_type: reason]."
    )
    parts.append("- Resolve rolls server-side; respect [ROLL_RESULT ...] messages.")
    parts.append(f"- Initiative order: { _initiative_order_label(game) }.")
    parts.append(f"- Current actor: { _current_actor_label(game) }.")

    if getattr(game, "active_encounter_summary", None):
        parts.append(f"- Active encounter: {game.active_encounter_summary}")
    if getattr(game, "encounter_history", None):
        recent = game.encounter_history[-3:]
        if recent:
            parts.append(f"- Recent encounters: " + " | ".join(recent))

    quests = _quest_labels(game)
    if quests:
        parts.append("- Quests: " + " | ".join(quests))

    return "\n".join(parts)


def refresh_mechanics_prompt(game: GameState):
    #Remove old mechanics prompts and append the latest one.
    
    if not game or not game.messages:
        return
    game.messages = [
        m for m in game.messages
        if not (m.role == "system" and "[MECHANICS]" in m.content)
    ]
    game.messages.append(
        Message(role="system", content=build_mechanics_prompt(game))
    )
