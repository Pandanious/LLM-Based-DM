

import re
from datetime import datetime
from textwrap import dedent
from typing import Dict, List

from src.llm_client import get_llm
from src.game.models import PlayerCharacter


CHAR_GEN_PROMPT_TEMPLATE = dedent("""
You are helping a player create a tabletop RPG character.

The game is set in this world:
{world_summary}

The human player at the table is named {player_name}.
They have already chosen these fixed details for their character:
- Character name: {char_name}
- Gender: {gender}
- Ancestry: {ancestry}

The player describes the character idea as:
"{character_prompt}"

Your job:
- Keep the name, gender, and ancestry EXACTLY as given. Do not change them.
- Choose an archetype (class/role) that fits the idea and world.
- Refine the concept into 2–4 sentences.
- Use a simple stat system with STR, DEX, CON, INT, WIS, CHA (values between 3 and 18).
- Set the starting level to 1.
- Choose 3–6 appropriate skills from this list of skills in the world:
  {world_skills}
- Give a reasonable MAX HP value for level 1.
- Suggest a small starting inventory (3–6 items).

Write your answer in this format (no extra commentary, no code, no backticks):

NAME: <character name>
GENDER: <gender>
ANCESTRY: <ancestry>
ARCHETYPE: <class or role>
LEVEL: 1

CONCEPT:
<2–4 sentences>

STATS:
STR: <number>
DEX: <number>
CON: <number>
INT: <number>
WIS: <number>
CHA: <number>

MAX HP: <number>

SKILLS:
- <skill 1>
- <skill 2>
- <skill 3>

INVENTORY:
- <item 1>
- <item 2>
- <item 3>
""")


def generate_character_sheet(
    world_summary: str,
    world_skills: List[str],
    player_name: str,
    character_prompt: str,
    pc_id: str,
    char_name: str,
    gender: str,
    ancestry: str,
) -> PlayerCharacter:
    """
    Use the LLM to generate a medium-detailed character sheet,
    keeping name, gender, and ancestry fixed, and picking skills
    from the world's skill list.
    """
    llm = get_llm()

    skills_str = ", ".join(world_skills) if world_skills else "no specific skills listed"

    prompt = CHAR_GEN_PROMPT_TEMPLATE.format(
        world_summary=world_summary,
        player_name=player_name,
        character_prompt=character_prompt,
        char_name=char_name,
        gender=gender,
        ancestry=ancestry,
        world_skills=skills_str,
    )

    result = llm(
        prompt,
        max_tokens=700,
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
        fixed_name=char_name,
        fixed_gender=gender,
        fixed_ancestry=ancestry,
    )


def _parse_stat_block(block: str) -> Dict[str, int]:
    stats: Dict[str, int] = {}
    pattern = re.compile(r"(STR|DEX|CON|INT|WIS|CHA)\s*:\s*(\d+)", re.IGNORECASE)
    for stat, value in pattern.findall(block):
        stats[stat.upper()] = int(value)
    for key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        stats.setdefault(key, 10)
    return stats


def _parse_list_block(block: str) -> List[str]:
    items: List[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if line:
            items.append(line)
    return items


def _parse_character_text(
    raw_text: str,
    pc_id: str,
    player_name: str,
    fixed_name: str,
    fixed_gender: str,
    fixed_ancestry: str,
) -> PlayerCharacter:
    """
    Parse the LLM's character text into a PlayerCharacter.
    Keeps name, gender, ancestry fixed to user choices.
    """
    text = raw_text.strip()

    archetype_match = re.search(
        r"^ARCHETYPE:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE
    )
    level_match = re.search(
        r"^LEVEL:\s*(\d+)", text, re.MULTILINE | re.IGNORECASE
    )

    archetype = archetype_match.group(1).strip() if archetype_match else ""
    level = 1  # always 1 for new characters

    concept_match = re.search(
        r"CONCEPT:\s*(.+?)(?:\n\n|STATS:)", text, re.DOTALL | re.IGNORECASE
    )
    concept = concept_match.group(1).strip() if concept_match else ""

    stats_block_match = re.search(
        r"STATS:\s*(.+?)(?:\n\n|MAX HP:)", text, re.DOTALL | re.IGNORECASE
    )
    stats_block = stats_block_match.group(1) if stats_block_match else ""
    stats = _parse_stat_block(stats_block)

    max_hp_match = re.search(r"MAX HP:\s*(\d+)", text, re.IGNORECASE)
    max_hp = int(max_hp_match.group(1)) if max_hp_match else 10

    skills_match = re.search(
        r"SKILLS:\s*(.+?)(?:\n\n|INVENTORY:)", text, re.DOTALL | re.IGNORECASE
    )
    skills_block = skills_match.group(1) if skills_match else ""
    skills = _parse_list_block(skills_block)

    inv_match = re.search(
        r"INVENTORY:\s*(.+)$", text, re.DOTALL | re.IGNORECASE
    )
    inv_block = inv_match.group(1) if inv_match else ""
    inventory = _parse_list_block(inv_block)

    now = datetime.utcnow()

    pc = PlayerCharacter(
        pc_id=pc_id,
        player_name=player_name,
        name=fixed_name,
        gender=fixed_gender,
        ancestry=fixed_ancestry,
        archetype=archetype,
        level=level,
        concept=concept,
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
