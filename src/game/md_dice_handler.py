from __future__ import annotations
import re
from typing import List, Dict, Any
from game.dice import roll_dice

Message = Dict[str, Any]

ROLL_REQUEST_RE = re.compile(
    r"\[ROLL_REQUEST:\s*(.+?)\s*\|\s*(.+?)\s*\]")

def extract_roll_request(text: str):
    match = ROLL_REQUEST_RE.search(text)
    if not match:
        return None, None

    dice_expr = match.group(1).strip()
    reason = match.group(2).strip()
    return dice_expr, reason