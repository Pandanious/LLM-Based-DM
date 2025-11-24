from __future__ import annotations
import random
import re
from dataclasses import dataclass
from typing import List

DICE_PATTERN = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$")

@dataclass
class DiceRollResult:
    expression: str    # like 2d4 + 3 # standard rpg types
    rolls: List[str]   # like [3,5] etc.
    modifier: int       
    total: int 
    reason: str | None = None

def roll_dice(expression: str, reason: str | None = None):

    match = DICE_PATTERN.match(expression)
    if not match:
        raise ValueError(f"Invalid dice expression: {expression!r}")

    count_str, sides_str, mod_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = 0
    if mod_str:
        modifier = int(mod_str.replace(" ", ""))  # "+ 3" -> "+3"

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    return DiceRollResult(
        expression=expression,
        rolls=rolls,
        modifier=modifier,
        total=total,
        reason=reason,
    )
