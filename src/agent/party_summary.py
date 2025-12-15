from typing import Dict
from src.game.models import PlayerCharacter


def build_party_summary(pcs: Dict[str, PlayerCharacter]):
    
    if not pcs:
        return ""

    lines = [
        "PARTY SUMMARY (DM reference only):",
        "These are the current player characters in the campaign.",
        "Do not invent different characters. Use these as canonical.",
        "",
    ]

    for pc in pcs.values():
        init_value = getattr(pc, "initiative", 0)
        line = (
            f"- Player: {pc.player_name} | "
            f"Character: {pc.name}, Level {pc.level} {pc.ancestry} {pc.archetype}. "
            f"Concept: {pc.concept.strip()}"
            f"(Initiative {init_value})."
        )
        lines.append(line)

    return "\n".join(lines)
