from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.agent.types import Message
from src.game.dice import roll_dice
from src.game.models import PlayerCharacter
from src.game.action_modifiers import compute_action_modifier, evaluate_check
from src.llm_client import chat_completion

# ---------------------------------------------------------------------------
# Action labels we expect the DM to use in the [ROLL_REQUEST] reason field.
# These must match the list in your persona prompt.
# ---------------------------------------------------------------------------

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

# [ROLL_REQUEST: 1d20+3 | stealth_check: sneak past the guard]
ROLL_REQUEST_RE = re.compile(
    r"\[ROLL_REQUEST:\s*(?P<expr>.+?)\s*\|\s*(?P<reason>.+?)\s*\]"
)


def parse_roll_request(text: str) -> Optional[tuple[str, str]]:
    # Extract (dice_expr, reason) from a DM reply, if present

    m = ROLL_REQUEST_RE.search(text)
    if not m:
        return None
    expr = m.group("expr").strip()
    reason = m.group("reason").strip()
    return expr, reason


def parse_action_type(reason: str) -> Optional[str]:
    
    m = re.match(r"^\s*([a-zA-Z_]+)\s*:", reason)
    if not m:
        return None
    label = m.group(1).strip().lower()
    if label in ALLOWED_ACTION_TYPES:
        return label
    return None


def ensure_action_label_in_reason(reason: str, fallback_action: str) -> str:
    
    if parse_action_type(reason) is not None:
        return reason
    fallback = fallback_action if fallback_action in ALLOWED_ACTION_TYPES else "attack"
    return f"{fallback}: {reason}"


def _find_pc_for_speaker(
    speaker: Optional[str],
    player_characters: Dict[str, PlayerCharacter],):
    
    if not speaker:
        return None
    s = speaker.lower()
    for pc in player_characters.values():
        if pc.player_name.lower() == s:
            return pc
    return None


def dm_turn_with_dice(
    messages: List[Message],
    player_characters: Dict[str, PlayerCharacter],):
    
    # Ask the DM to respond to the current messages
    
    dm_reply = chat_completion(messages, temperature=0.6)
    dm_message = Message(role="assistant", content=dm_reply, speaker="Dungeon Master")
    messages.append(dm_message)

    # Look for a [ROLL_REQUEST: ...] line in the DM reply
    
    rr = parse_roll_request(dm_reply)
    if not rr:
        # No dice requested; just return with the DM's response added.
        return messages

    dice_expr, reason = rr

    # Determine which player character is acting
    
    last_user = next(
        (m for m in reversed(messages) if m.role == "user"),
        None,
    )
    actor_pc = _find_pc_for_speaker(
        getattr(last_user, "speaker", None) if last_user else None,
        player_characters,
    )

    # Determine action_type and normalize the reason label
    
    action_type = parse_action_type(reason)
    if action_type is None:
        # If DM forgot, fall back based on context; for now just assume "attack"
        action_type = "attack"
    reason = ensure_action_label_in_reason(reason, action_type)

    
    # Build a final dice expression using stats/skills instead of DM's modifier
    
    # For non-damage actions, always treat as a d20 check.
    if action_type in {"damage_light", "damage_heavy"}:
        # Simple defaults; tweak to taste
        if action_type == "damage_light":
            base_expr = "1d6"
        else:
            base_expr = "1d10"
    else:
        base_expr = "1d20"

    # Stat + skill + difficulty-based modifier (may be negative)
    modifier = compute_action_modifier(actor_pc, action_type, reason)

    if modifier == 0:
        final_expr = base_expr
    elif modifier > 0:
        final_expr = f"{base_expr}+{modifier}"
    else:
        final_expr = f"{base_expr}{modifier}"  # modifier already includes "-"

    # Roll the dice and evaluate success/failure (for checks)
    
    result = roll_dice(final_expr, reason=reason)

    dc, outcome = evaluate_check(
        total=result.total,
        action_type=action_type,
        reason=reason,
    )

    # Add a [ROLL_RESULT: ...] line as a system message
    
    extra_parts = [
        f"rolls={result.rolls}",
        f"modifier={modifier}",
        f"action_type={action_type}",
    ]
    if dc is not None:
        extra_parts.append(f"dc={dc}")
    if outcome is not None:
        extra_parts.append(f"outcome={outcome}")
    if actor_pc is not None:
        extra_parts.append(f"actor={actor_pc.name}")

    extra_str = ", ".join(extra_parts)

    roll_result_line = (
        f"[ROLL_RESULT: {result.expression} = {result.total} "
        f"({extra_str}) | {result.reason}]"
    )

    roll_message = Message(role="system", content=roll_result_line, speaker=None)
    messages.append(roll_message)

    # Ask DM again to narrate the outcome based on the roll result
    
    outcome_text = chat_completion(messages, temperature=0.6)
    outcome_message = Message(
        role="assistant",
        content=outcome_text,
        speaker="Dungeon Master",
    )
    messages.append(outcome_message)

    return messages
