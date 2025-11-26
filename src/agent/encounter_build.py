from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Encounter:
    encounter_type: str
    trigger: str
    summary: str
    status: str = "active"  # "active", "resolved"


_COMBAT_CUES = ("attack", "fight", "draws a weapon", "initiative", "hostile", "ambush")
_SOCIAL_CUES = ("parley", "negotiate", "talks down", "intimidate", "diplomacy")
_HAZARD_CUES = ("trap", "environmental hazard", "collapsing", "fire spreads", "poison gas")


def _match_keywords(text: str, keywords: Tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def detect_encounter(user_text: str) -> Optional[Encounter]:
    """
    Light-weight detector for simple encounter types.
    Returns an Encounter if the text suggests combat, social, or hazard.
    """
    if _match_keywords(user_text, _COMBAT_CUES):
        return Encounter(
            encounter_type="combat",
            trigger=user_text,
            summary="Combat encounter detected",
        )
    if _match_keywords(user_text, _SOCIAL_CUES):
        return Encounter(
            encounter_type="social",
            trigger=user_text,
            summary="Social encounter detected",
        )
    if _match_keywords(user_text, _HAZARD_CUES):
        return Encounter(
            encounter_type="hazard",
            trigger=user_text,
            summary="Hazard encounter detected",
        )
    return None


def encounter_prompt(encounter: Encounter, player_name: str, character_name: str) -> str:
    """
    Build a short system prompt to alert the DM about the encounter state.
    """
    return (
        f"[ENCOUNTER] {encounter.summary}. "
        f"Initiated by {player_name} as {character_name}. "
        "Address this encounter now and keep turns moving."
    )
