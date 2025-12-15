from __future__ import annotations

from datetime import datetime
from typing import Any

from src.agent.types import Message
from src.game.quest_store import save_quests


def handle_quest_command(raw: str, game: Any):
    
    # Handle quest-related slash commands.
    
    if not raw.strip().lower().startswith("/quest"):
        return False

    parts = raw.strip().split(maxsplit=2)  # ["/quest", subcmd, rest]
    if len(parts) == 1:
        return False  # let DM see it

    sub = parts[1].lower()
    arg = parts[2].strip() if len(parts) > 2 else ""

    world = game.world
    if world is None:
        return False

    quests = getattr(game, "quests", {}) or {}

    def add_system_message(text: str):
        game.messages.append(
            Message(
                role="system",
                content=text,
                speaker=None,
            )
        )

    
    if sub == "list":
        if not quests:
            add_system_message("[QUEST LIST] No quests available for this world.")
        else:
            lines = ["[QUEST LIST]"]
            for q in quests.values():
                loc = q.target_location or "Unknown location"
                lines.append(f"- {q.title} [{q.status}] at {loc}")
            add_system_message("\n".join(lines))
        return True

    # start/complete/fail
    if sub in {"start", "complete", "fail"}:
        if not arg:
            add_system_message(
                "Quest command needs a title fragment. Example:\n"
                "/quest complete stolen cargo"
            )
            return True

        target = arg.lower()
        found = None
        for qid, q in quests.items():
            if target in q.title.lower():
                found = (qid, q)
                break

        if not found:
            add_system_message(
                f"No quest title matched '{arg}'. Use /quest list to see all quests."
            )
            return True

        qid, quest = found

        if sub == "start":
            quest.status = "in_progress"
        elif sub == "complete":
            quest.status = "completed"
        elif sub == "fail":
            quest.status = "failed"

        quest.last_updated = datetime.utcnow()
        quests[qid] = quest
        game.quests = quests
        save_quests(world.world_id, quests)

        add_system_message(f"Quest '{quest.title}' marked as {quest.status.upper()}.")
        return True

    return False
