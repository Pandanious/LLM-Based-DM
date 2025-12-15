from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Optional


ROLL_RE = re.compile(
    r"^\s*(?P<num>\d*)d(?P<sides>\d+)(?P<mod>[+-]\d+)?\s*$",
    re.IGNORECASE,
)


@dataclass
class RollResult:
    expression: str
    total: int
    rolls: List[int]
    modifier: int
    reason: Optional[str] = None


def roll_dice(expr: str, reason: Optional[str] = None):
    # Parse dice expression like "1d20+3" or "2d6-1" and roll it.
    
    m = ROLL_RE.match(expr)
    if not m:
        raise ValueError(f"Invalid dice expression: {expr!r}")

    num = int(m.group("num") or "1")
    sides = int(m.group("sides"))
    mod = int(m.group("mod") or "0")

    rolls = [random.randint(1, sides) for _ in range(num)]
    total = sum(rolls) + mod

    return RollResult(
        expression=expr.strip(),
        total=total,
        rolls=rolls,
        modifier=mod,
        reason=reason,
    )
