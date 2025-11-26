from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.game.models import PlayerCharacter


@dataclass
class ActionEntry:
    actor_id: Optional[str]
    actor_name: str
    player_name: str
    content: str
    timestamp: str
    tags: List[str] = field(default_factory=list)


@dataclass
class TurnEntry:
    turn_number: int
    actor_id: Optional[str]
    actor_name: str
    timestamp: str
    description: str
    options: List[str] = field(default_factory=list)
    actions: List[ActionEntry] = field(default_factory=list)


@dataclass
class TurnLog:
    world_id: str
    turn_count: int = 0
    current_actor_id: Optional[str] = None
    entries: List[TurnEntry] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "world_id": self.world_id,
            "turn_count": self.turn_count,
            "current_actor_id": self.current_actor_id,
            "entries": [asdict(e) for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TurnLog":
        entries = [
            TurnEntry(
                turn_number=e.get("turn_number", 0),
                actor_id=e.get("actor_id"),
                actor_name=e.get("actor_name", ""),
                timestamp=e.get("timestamp", ""),
                description=e.get("description", ""),
                options=list(e.get("options", [])),
                actions=[
                    ActionEntry(
                        actor_id=a.get("actor_id"),
                        actor_name=a.get("actor_name", ""),
                        player_name=a.get("player_name", ""),
                        content=a.get("content", ""),
                        timestamp=a.get("timestamp", ""),
                        tags=list(a.get("tags", [])),
                    )
                    for a in e.get("actions", [])
                ],
            )
            for e in data.get("entries", [])
        ]
        return cls(
            world_id=data.get("world_id", ""),
            turn_count=int(data.get("turn_count", 0)),
            current_actor_id=data.get("current_actor_id"),
            entries=entries,
        )


def _turns_path(world_id: str) -> Path:
    Path("saves").mkdir(exist_ok=True)
    Path("saves/turns").mkdir(exist_ok=True)
    return Path("saves/turns") / f"{world_id}_turns.json"


def load_turn_log(world_id: str) -> TurnLog:
    path = _turns_path(world_id)
    if not path.exists():
        return TurnLog(world_id=world_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return TurnLog.from_dict(data)


def save_turn_log(turn_log: TurnLog) -> Path:
    path = _turns_path(turn_log.world_id)
    path.write_text(json.dumps(turn_log.to_dict(), indent=2), encoding="utf-8")
    return path


def begin_turn(turn_log: TurnLog, actor: Optional[PlayerCharacter]) -> TurnLog:
    turn_log.turn_count += 1
    turn_log.current_actor_id = actor.pc_id if actor else None
    entry = TurnEntry(
        turn_number=turn_log.turn_count,
        actor_id=actor.pc_id if actor else None,
        actor_name=actor.name if actor else "Unknown",
        timestamp=datetime.utcnow().isoformat(),
        description="Turn started",
    )
    turn_log.entries.append(entry)
    return turn_log


def add_turn_note(turn_log: TurnLog, note: str, options: Optional[List[str]] = None) -> TurnLog:
    if not turn_log.entries:
        return turn_log
    entry = turn_log.entries[-1]
    entry.description += f" | {note}"
    if options:
        entry.options.extend(options)
    return turn_log


def add_turn_action(
    turn_log: TurnLog,
    *,
    player_name: str,
    actor: Optional[PlayerCharacter],
    content: str,
    tags: Optional[List[str]] = None,
) -> TurnLog:
    """
    Attach a structured action record to the most recent turn.
    """
    if not turn_log.entries:
        return turn_log

    action = ActionEntry(
        actor_id=actor.pc_id if actor else None,
        actor_name=actor.name if actor else "Unknown",
        player_name=player_name,
        content=content,
        timestamp=datetime.utcnow().isoformat(),
        tags=list(tags or []),
    )
    turn_log.entries[-1].actions.append(action)
    return turn_log


def build_action_summary(
    turn_log: TurnLog,
    limit: int = 12,
    encounter_summary: Optional[str] = None,
    encounter_history: Optional[List[str]] = None,
) -> str:
    """
    Produce a compact human-readable summary of the latest actions,
    with optional encounter context.
    """
    lines: List[str] = []
    if encounter_summary:
        lines.append(f"Active encounter: {encounter_summary}")
    if encounter_history:
        lines.append("Recent encounters: " + " | ".join(encounter_history[-3:]))

    collected = []
    for entry in turn_log.entries:
        for action in entry.actions:
            collected.append((entry.turn_number, action))

    if not collected:
        base = "No actions recorded yet."
        return "\n".join(lines + [base]) if lines else base

    tail = collected[-limit:]
    lines.append("Recent actions (oldest of the batch first):")
    for turn_number, action in tail:
        try:
            ts = datetime.fromisoformat(action.timestamp).strftime("%H:%M")
        except Exception:
            ts = action.timestamp
        lines.append(
            f"- Turn {turn_number}: {action.player_name}/{action.actor_name}: "
            f"{action.content} (at {ts}Z)"
        )
    return "\n".join(lines)


def export_turn_log_snapshot(turn_log: TurnLog, summary_text: Optional[str] = None) -> tuple[Path, Path]:
    """
    Persist the turn log plus a text summary into a timestamped snapshot folder.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_root = Path("saves") / "snapshots" / f"{turn_log.world_id}_actions"
    export_root.mkdir(parents=True, exist_ok=True)

    json_path = export_root / f"{turn_log.world_id}_turns_{timestamp}.json"
    summary_path = export_root / f"{turn_log.world_id}_summary_{timestamp}.txt"

    json_path.write_text(json.dumps(turn_log.to_dict(), indent=2), encoding="utf-8")
    summary_text = summary_text if summary_text is not None else build_action_summary(turn_log)
    summary_path.write_text(summary_text, encoding="utf-8")

    return json_path, summary_path
