import re
from textwrap import dedent
from typing import Dict

from src.llm_client import get_llm
from src.game.models import PlayerCharacter
from datetime import datetime


CHAR_GEN_PROMPT_TEMPLATE = dedent("""
You are creating a player character for a tabletop RPG set in this world:

{world_summary}

The player is named {player_name}.
Their character idea is:
"{character_prompt}"

Generate a medium-detail character sheet based on this idea.
Follow the format in the EXAMPLE below.
Do not invent rules. Keep everything narrative friendly.

EXAMPLE FORMAT (copy structure, not content):

NAME: Arlen Vex
ANCESTRY: Human
ARCHETYPE: Street Samurai
LEVEL: 3

CONCEPT:
A grizzled ex-soldier turned mercenary. He wanders the neon underworld looking for redemption.

STATS:
STR: 14
DEX: 12
CON: 13
INT: 10
WIS: 11
CHA: 9

MAX HP: 18

SKILLS:
- Close Combat
- Intimidation
- Tracking

INVENTORY:
- Katana
- Combat jacket
- Old military dog tags

END OF EXAMPLE

Now generate the character following the same structure.
Begin your answer with "NAME:".
""")


def generate_character_sheet(
    world_summary: str,
    player_name: str,
    character_prompt: str,
    pc_id: str,
) -> PlayerCharacter:
    
    # Use the LLM to generate a medium-detailed character sheet and parse it into a PlayerCharacter.
    
    llm = get_llm()

    prompt = CHAR_GEN_PROMPT_TEMPLATE.format(
        world_summary=world_summary,
        player_name=player_name,
        character_prompt=character_prompt,
    )

    result = llm(
        prompt,
        max_tokens=600,
        temperature=0.8,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw = result["choices"][0]["text"].strip()

    return _parse_character_text(
        raw_text=raw,
        pc_id=pc_id,
        player_name=player_name,
    )


def _parse_stat_block(block: str) -> Dict[str, int]:
    stats = {}
    pattern = re.compile(r"(STR|DEX|CON|INT|WIS|CHA)\s*:\s*(\d+)", re.IGNORECASE)
    for stat, value in pattern.findall(block):
        stats[stat.upper()] = int(value)
    # ensure all keys exist with some default
    for key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        stats.setdefault(key, 10)
    return stats


def _parse_list_block(block: str) -> list:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if line:
            items.append(line)
    return items


def _parse_character_text(raw_text: str, pc_id: str, player_name: str) -> PlayerCharacter:
    
    #Parse the LLM's character text into a PlayerCharacter.
    #Assumes the format from CHAR_GEN_PROMPT_TEMPLATE, but is forgiving.
    
    text = raw_text.strip()

    # Basic sections using simple regex / splits
    # NAME, ANCESTRY, ARCHETYPE, LEVEL
    name_match = re.search(r"^NAME:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    ancestry_match = re.search(r"^ANCESTRY:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    archetype_match = re.search(r"^ARCHETYPE:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    level_match = re.search(r"^LEVEL:\s*(\d+)", text, re.MULTILINE | re.IGNORECASE)

    name = name_match.group(1).strip() if name_match else f"{player_name}'s character"
    ancestry = ancestry_match.group(1).strip() if ancestry_match else ""
    archetype = archetype_match.group(1).strip() if archetype_match else ""
    level = int(level_match.group(1)) if level_match else 1

    # CONCEPT block
    concept_match = re.search(
        r"CONCEPT:\s*(.+?)(?:\n\n|STATS:)", text, re.DOTALL | re.IGNORECASE
    )
    concept = concept_match.group(1).strip() if concept_match else ""

    # STATS block
    stats_block_match = re.search(
        r"STATS:\s*(.+?)(?:\n\n|MAX HP:)", text, re.DOTALL | re.IGNORECASE
    )
    stats_block = stats_block_match.group(1) if stats_block_match else ""
    stats = _parse_stat_block(stats_block)

    # MAX HP
    max_hp_match = re.search(r"MAX HP:\s*(\d+)", text, re.IGNORECASE)
    max_hp = int(max_hp_match.group(1)) if max_hp_match else 10

    # SKILLS block
    skills_match = re.search(
        r"SKILLS:\s*(.+?)(?:\n\n|INVENTORY:)", text, re.DOTALL | re.IGNORECASE
    )
    skills_block = skills_match.group(1) if skills_match else ""
    skills = _parse_list_block(skills_block)

    # INVENTORY block
    inv_match = re.search(
        r"INVENTORY:\s*(.+)$", text, re.DOTALL | re.IGNORECASE
    )
    inv_block = inv_match.group(1) if inv_match else ""
    inventory = _parse_list_block(inv_block)

    now = datetime.utcnow()

    pc = PlayerCharacter(
        pc_id=pc_id,
        player_name=player_name,
        name=name,
        concept=concept,
        ancestry=ancestry,
        archetype=archetype,
        level=level,
        stats=stats,
        max_hp=max_hp,
        current_hp=max_hp,
        skills=skills,
        inventory=inventory,
        notes=[],
        created_on=now,
        last_updated=now,
    )

    return pc