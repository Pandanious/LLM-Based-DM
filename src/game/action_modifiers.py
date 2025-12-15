# src/game/action_modifiers.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.game.models import PlayerCharacter


# Which ability is primary for which action_type
PRIMARY_STAT: Dict[str, str] = {
    "attack": "STR",          # fallback if we still see "attack"
    "stealth_check": "DEX",
    "perception_check": "WIS",
    "lockpick": "DEX",
    "persuasion": "CHA",
    "athletics": "STR",
    "acrobatics": "DEX",
    "damage_light": "DEX",    # or STR; tweak to taste
    "damage_heavy": "STR",
}


# If any of these substrings appear in a PC skill, they count as proficiency for that action_type
SKILL_KEYWORDS: Dict[str, List[str]] = {
    "stealth_check": ["stealth", "sneak", "hiding"],
    "perception_check": ["perception", "awareness", "spot", "notice"],
    "lockpick": ["lockpick", "thievery", "burglary"],
    "persuasion": ["persuasion", "diplomacy", "negotiation", "charm"],
    "athletics": ["athletics", "climbing", "swimming", "lifting"],
    "acrobatics": ["acrobatics", "tumbling", "balancing", "dodging"],
    "attack": ["weapon", "combat", "fighting"],
    "damage_light": ["weapon", "combat", "finesse"],
    "damage_heavy": ["weapon", "combat", "heavy"],
}

# Simple static proficiency bonus for "has the right skill"
DEFAULT_PROF_BONUS = 2


def ability_mod(stat_value: int):
    """
    Convert a 3-18 stat score to a D&D-ish modifier, including negatives.
    Example: 8 -> -1, 10 -> 0, 14 -> +2, 18 -> +4.
    """
    return (stat_value - 10) // 2


def _get_primary_ability_mod(pc: PlayerCharacter, action_type: str):
    stats = pc.stats or {}
    # Default to 10 if missing
    str_mod = ability_mod(stats.get("STR", 10))
    dex_mod = ability_mod(stats.get("DEX", 10))
    int_mod = ability_mod(stats.get("INT", 10))
    wis_mod = ability_mod(stats.get("WIS", 10))
    cha_mod = ability_mod(stats.get("CHA", 10))

    key = PRIMARY_STAT.get(action_type)

    if key == "STR":
        return str_mod
    if key == "DEX":
        return dex_mod
    if key == "INT":
        return int_mod
    if key == "WIS":
        return wis_mod
    if key == "CHA":
        return cha_mod

    # Fallback for unknown types: use best mental or physical stat
    return max(str_mod, dex_mod, int_mod, wis_mod, cha_mod)


def _skill_bonus(pc: PlayerCharacter, action_type: str):

    # +DEFAULT_PROF_BONUS PC's skills match SKILL_KEYWORDS[action_type].
    
    keywords = SKILL_KEYWORDS.get(action_type)
    if not keywords:
        return 0

    skills = pc.skills or []
    lower_skills = [s.lower() for s in skills]

    for kw in keywords:
        for s in lower_skills:
            if kw in s:
                return DEFAULT_PROF_BONUS
    return 0


def _difficulty_adjustment(reason: str):
    """
    Very simple difficulty parser:
    - "very hard" / "extremely" -> -4
    - "hard" / "difficult"      -> -2
    - "easy" / "simple"         -> +2
    """
    r = reason.lower()
    if "very hard" in r or "extremely" in r or "impossible" in r:
        return -4
    if "hard" in r or "difficult" in r or "risky" in r:
        return -2
    if "easy" in r or "simple" in r:
        return +2
    return 0


def compute_action_modifier(
    pc: Optional[PlayerCharacter],
    action_type: str,
    reason: str,):
    
    #Compute the total modifier for a given action
    
    if pc is None:
        return 0

    base = _get_primary_ability_mod(pc, action_type)
    skill = _skill_bonus(pc, action_type)
    diff = _difficulty_adjustment(reason)

    return base + skill + diff


def evaluate_check(
    total: int,
    action_type: str,
    reason: str,):
   
    if action_type in {"damage_light", "damage_heavy"}:
        return None, None

    r = reason.lower()

    if "very hard" in r or "extremely" in r or "impossible" in r:
        dc = 20
    elif "hard" in r or "difficult" in r or "risky" in r:
        dc = 17
    elif "easy" in r or "simple" in r:
        dc = 10
    else:
        # "Normal" difficulty
        dc = 13

    outcome = "success" if total >= dc else "failure"
    return dc, outcome
