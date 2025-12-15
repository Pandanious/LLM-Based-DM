from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class CommandKind(str, Enum):
    """High-level category of a parsed command."""
    MECHANICAL = "mechanical"  # <-  game mechanics
    META = "meta"              # <-  out-of-character or system commands
    

@dataclass
class ParsedCommand:
   
    raw: str
    base: str
    action_type: Optional[str] # what is the action type
    description: str
    needs_dice: bool      # if it needs dice throw or not.
    kind: CommandKind

ACTION_TYPES = {
    "attack",
    "stealth_check",
    "perception_check",
    "lockpick",
    "persuasion",
    "athletics",
    "acrobatics",
    "damage_light",
    "damage_heavy",
}

# mapping lowercase words to the action type. can be added on by the llm as well, later.


ACTION_SYNONYMS: Dict[str, str] = {

   # LIGHT ATTACKS (damage_light)
    "stab": "damage_light",
    "slash": "damage_light",   # small/light slash
    "cut": "damage_light",
    "slice": "damage_light",
    "dagger": "damage_light",
    "jab": "damage_light",
    "punch": "damage_light",
    "kick": "damage_light",
    "strike": "damage_light",  # ambiguous, treat as light if unsure
    "thrust": "damage_light",

    # HEAVY ATTACKS (damage_heavy)
    "smash": "damage_heavy",
    "cleave": "damage_heavy",
    "swing": "damage_heavy",   # often implies force
    "hammer": "damage_heavy",
    "axe": "damage_heavy",
    "maul": "damage_heavy",
    "power": "damage_heavy",   # as in "power attack"
    "heavy": "damage_heavy",
    
    # GENERIC ATTACK use damage_light

    "attack": "damage_light",

    # STEALTH
    "sneak": "stealth_check",
    "hide": "stealth_check",
    "stealth": "stealth_check",
    "creep": "stealth_check",
    "slip": "stealth_check",

    # PERCEPTION
    "perception": "perception_check",
    "look": "perception_check",
    "scan": "perception_check",
    "observe": "perception_check",
    "listen": "perception_check",
    "search": "perception_check",
    "notice": "perception_check",

    # LOCKPICK
    "lockpick": "lockpick",
    "picklock": "lockpick",
    "pick": "lockpick",
    "unlock": "lockpick",
    "openlock": "lockpick",

    # PERSUASION
    "persuade": "persuasion",
    "charm": "persuasion",
    "convince": "persuasion",
    "negotiate": "persuasion",
    "talk": "persuasion",
    "appeal": "persuasion",

    # ATHLETICS
    "athletics": "athletics",
    "climb": "athletics",
    "jump": "athletics",
    "run": "athletics",
    "lift": "athletics",
    "push": "athletics",
    "pull": "athletics",
    "break": "athletics",
    "force": "athletics",

    # ACROBATICS
    "acrobatics": "acrobatics",
    "dodge": "acrobatics",
    "tumble": "acrobatics",
    "roll": "acrobatics",
    "leap": "acrobatics",
    "balance": "acrobatics",
    "flip": "acrobatics",
}

# Meta / system commands.
META_COMMANDS = {
    "help",
    "ooc",        
    "note",
    "system",
    "gm",
    "dm",
}


def register_action_synonym(trigger: str, action_type: str):
    
    trigger = trigger.strip().lower()
    action_type = action_type.strip().lower()
    if not trigger:
        return
    if action_type not in ACTION_TYPES:
        # flag if messes up later.
        return
    ACTION_SYNONYMS[trigger] = action_type


def _normalize_action_from_rest(rest: str):
    
    rest = rest.strip()
    if not rest:
        return None

    first_word = rest.split(" ", 1)[0].lower()
    return ACTION_SYNONYMS.get(first_word)


def parse_command(text: str):
    
    if not text:
        return None

    raw = text.strip()
    if not raw.startswith("/"):
        # Not a command - treat as normal in-character speech.
        return None

    # Strip leading "/" and split.
    body = raw[1:].strip()
    
    parts = body.split(" ", 1)
    cmd_word = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    base = f"/{cmd_word}"

    
    if cmd_word in META_COMMANDS:
        return ParsedCommand(
            raw=raw,
            base=base,
            action_type=None,
            description=rest.strip(),
            needs_dice=False,
            kind=CommandKind.META,
        )

    # DICE throw case
    if cmd_word == "action":
        action_type = _normalize_action_from_rest(rest)
        
        return ParsedCommand(
            raw=raw,
            base=base,
            action_type=action_type,
            description=rest.strip(),
            needs_dice=True,
            kind=CommandKind.MECHANICAL,
        )

    # Other verbs still try map : like /attack, /sneak, /perception, /lockpick, etc.
    
    action_type = ACTION_SYNONYMS.get(cmd_word)

    if action_type:
        return ParsedCommand(
            raw=raw,
            base=base,
            action_type=action_type,
            description=rest.strip(),
            needs_dice=True,
            kind=CommandKind.MECHANICAL,
        )

    
