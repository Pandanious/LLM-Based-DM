from __future__ import annotations
import re
from typing import List, Dict, Any
from src.agent.types import Message
from src.game.dice import roll_dice
from src.llm_client import chat_completion


ROLL_REQUEST_RE = re.compile(
    r"\[ROLL_REQUEST:\s*(.+?)\s*\|\s*(.+?)\s*\]")

# Which action labels we consider "standard" and want to recognize.
ALLOWED_ACTION_TYPES = {
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



def extract_roll_request(text: str):
    match = ROLL_REQUEST_RE.search(text)
    if not match:
        return None, None

    dice_expr = match.group(1).strip()
    reason = match.group(2).strip()
    return dice_expr, reason

def parse_action_type(reason: str) -> str | None:
    #
    #Try to extract an action type label from the reason field.

    # Expected patterns:
    #- "stealth_check: sneaking past the guard"
    #- "attack: strike the goblin"
    #- "lockpick: open the chest"

    # We look at the text before the first ":" or first space and see
    # if it matches one of ALLOWED_ACTION_TYPES.
    #
    
    if not reason:
        return None

    text = reason.strip().lower()

    # Take the part before ":" if present, else first word
    if ":" in text:
        candidate = text.split(":", 1)[0].strip()
    else:
        candidate = text.split(" ", 1)[0].strip()

    if candidate in ALLOWED_ACTION_TYPES:
        return candidate

    return None



def dm_turn_with_dice(messages: List[Message]) -> List[Message]:
    
    # 1) DM replies normally
    dm_reply_text = chat_completion(messages)
    dm_message: Message = {"role": "assistant", "content": dm_reply_text}
    messages.append(dm_message)

    # 2) Scan for a roll request
    dice_expr, reason = extract_roll_request(dm_reply_text)
    if not dice_expr:
        return messages   # No roll needed this turn
    
    # SAFTEY ISSUE - has to be /action to roll
    last_user = next((m for m in reversed(messages) if m.role == "user"), None)
    if not last_user or not last_user.content.strip().startswith("/action"):
    # Ignore the roll request, just treat DM reply as pure narration
        return messages
    action_type = parse_action_type(reason)

    # 3) Perform the dice roll in code
    result = roll_dice(dice_expr, reason=reason)

    # 4) Add a [ROLL_RESULT: ...] line as a system message
    roll_result_line = (
        f"[ROLL_RESULT: {result.expression} = {result.total} "
        f"(rolls={result.rolls}, modifier={result.modifier}) | {result.reason}]"
    )

    roll_message = Message(role="system", content=roll_result_line)
    messages.append(roll_message)

    # 5) Ask DM again to narrate the outcome
    outcome_text = chat_completion(messages)
    outcome_message = Message(role="assistant", content=outcome_text)
    messages.append(outcome_message)



    return messages

