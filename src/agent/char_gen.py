import re
from datetime import datetime
from textwrap import dedent
from typing import Dict, List

from src.llm_client import get_llm
from src.game.models import PlayerCharacter
from src.game.dice import roll_dice
from src.agent.item_gen import generate_items_for_character


END_MARKER = "<<CHARACTER_SHEET_COMPLETE>>"
STOP_MARKERS = [
    END_MARKER.lower(),
    "character sheet complete",
    "character sheet completed",
    "end:",
    "end of character sheet",
]


CHAR_GEN_PROMPT_TEMPLATE = dedent(f"""
You are helping a player create a tabletop RPG character.

The game is set in this world:
{{world_summary}}

The human player at the table is named {{player_name}}.
They have already chosen these fixed details for their character:
- Character name: {{char_name}}
- Gender: {{gender}}
- Ancestry: {{ancestry}}

The player describes the character idea as:
"{{character_prompt}}"

Your job:
- Keep the NAME, GENDER and ANCESTRY exactly as given. Do not change them.
- Do NOT sanitize, correct, replace, or reinterpret player-provided values, even if they seem absurd or contradictory; honor them verbatim and work them into the world context as best you can.
- Choose an archetype (class/role) that fits the idea and world.
- Refine the concept into 2-4 sentences. Do NOT repeat the same sentence or idea twice.
- Use a simple stat system with STR, DEX, CON, INT, WIS, CHA (values between 3 and 18).
- Set LEVEL = 1.
- Choose 3-6 appropriate skills from this list of skills in the world:
  {{world_skills}}
- Give a reasonable MAX HP value for a level 1 character.

Important style rules:
- Do NOT repeat yourself. Avoid saying the same thing in different words.
- Do NOT restate the character idea verbatim; summarize and refine it.
- Keep each section short and focused.
- Do NOT add extra sections or commentary.
- Do NOT use backticks or code fences.
- Generate **exactly ONE** character sheet.
- Do NOT repeat fields you have already created.
- After producing the sheet, end your answer with the EXACT line:
  END: {END_MARKER}

Write your answer in this format exactly (no extra commentary):

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

END: {END_MARKER}
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
    
    # Use the LLM to generate a medium-detailed character sheet, keeping name, gender,
    # and ancestry fixed, and picking skills from the world's skill list.
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

    raw = ""
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        result = llm(
            prompt,
            max_tokens=600,
            temperature=0.65,   # a bit lower for more discipline
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.2,  # slightly stronger to reduce rambling
        )
        raw = _clean_raw_text(result["choices"][0]["text"])
        if _looks_like_sheet(raw):
            break
        if attempt == max_attempts:
            raise ValueError("Character generation did not return a usable sheet after retries.")

    return _parse_character_text(
        raw_text=raw,
        pc_id=pc_id,
        player_name=player_name,
        fixed_name=char_name,
        fixed_gender=gender,
        fixed_ancestry=ancestry,
        world_summary=world_summary,
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
    seen = set()
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-") or line.startswith("•"):
            line = line[1:].strip()
        if not line:
            continue
        lower_line = line.lower()
        # Skip obvious header/marker pollution and model self-talk
        if lower_line.startswith(
            (
                "name:",
                "gender:",
                "ancestry:",
                "archetype:",
                "level:",
                "concept:",
                "stats:",
                "skills:",
                "inventory:",
                "end:",
            )
        ):
            continue
        if "character sheet" in lower_line or "complete" in lower_line:
            continue
        # de-duplicate list entries
        if lower_line in seen:
            continue
        seen.add(lower_line)
        items.append(line)
        # Hard cap to avoid runaway lists
        if len(items) >= 6:
            break
    return items


def _dedupe_sentences(text: str, max_sentences: int = 4) -> str:
    
    # crude sentence split on . ! and remove same text. ?
    parts = re.split(r"([\.!?])", text)
    sentences = []
    current = ""

    for chunk in parts:
        if chunk in [".", "!", "?"]:
            current += chunk
            if current.strip():
                sentences.append(current.strip())
            current = ""
        else:
            current += chunk

    if current.strip():
        sentences.append(current.strip())

    seen = set()
    cleaned = []
    for s in sentences:
        normalized = re.sub(r"\s+", " ", s.strip().lower())
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(s.strip())
        if len(cleaned) >= max_sentences:
            break

    return " ".join(cleaned).strip()


def _clean_raw_text(raw: str) -> str:
    text = raw.strip()
    # Remove fenced code blocks or backtick wrappers the model might emit
    text = re.sub(r"^```(?:\w+)?\\n?", "", text)
    text = re.sub(r"```$", "", text)
    # Truncate at the first stop marker we see
    lower_text = text.lower()
    for marker in STOP_MARKERS:
        idx = lower_text.find(marker)
        if idx != -1:
            text = text[:idx]
            lower_text = text.lower()
            break
    # Drop any END markers in various forms
    text = text.replace(f"END: {END_MARKER}", "")
    text = text.replace(END_MARKER, "")
    text = text.replace("END:", "")
    # Remove a leading “Character Sheet” label if present
    text = re.sub(r"^Character Sheet:?\\s*", "", text, flags=re.IGNORECASE)
    return text.strip()

def _parse_character_text(
    raw_text: str,
    pc_id: str,
    player_name: str,
    fixed_name: str,
    fixed_gender: str,
    fixed_ancestry: str,
    world_summary: str,
) -> PlayerCharacter:
    
    #Parse the LLM's character text into a PlayerCharacter. Keeps name, gender etc user choices.
    
    text = raw_text.strip()

    # Archetype and level
    archetype_match = re.search(
        r"^ARCHETYPE:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE
    )

    archetype = archetype_match.group(1).strip() if archetype_match else ""
    level = 1  # always 1 for new characters; ignore model level if present

    # Concept block
    concept_match = re.search(
        r"CONCEPT:\s*(.+?)(?:\n\n|STATS:)", text, re.DOTALL | re.IGNORECASE
    )
    raw_concept = concept_match.group(1).strip() if concept_match else ""
    concept = _dedupe_sentences(raw_concept, max_sentences=4)

    # Stats
    stats_block_match = re.search(
        r"STATS:\s*(.+?)(?:\n\n|MAX HP:)", text, re.DOTALL | re.IGNORECASE
    )
    stats_block = stats_block_match.group(1) if stats_block_match else ""
    stats = _parse_stat_block(stats_block)

    # Max HP
    max_hp_match = re.search(r"MAX HP:\s*(\d+)", text, re.IGNORECASE)
    max_hp = int(max_hp_match.group(1)) if max_hp_match else 10

    # Skills
    skills_match = re.search(
        r"SKILLS:\s*(.+)$", text, re.DOTALL | re.IGNORECASE
    )
    skills_block = skills_match.group(1) if skills_match else ""
    skills = _parse_list_block(skills_block)

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
        notes=[],
        created_on=now,
        last_updated=now,    )

    try:
        # roll_dice only expects an expression; use a simple d20 for initiative
        init_result = roll_dice("1d20")
        pc.initiative = init_result.total
    except Exception:
        # Fallback so we never crash character generation
        pc.initiative = 0

    # Generate starter gear separately and attach simple labels to inventory
    try:
        items = generate_items_for_character(world_summary=world_summary, archetype=archetype, count=4)
        inv_labels: List[str] = []
        for it in items:
            cat = it.item_category or "gear"
            sub = f"/{it.item_subcategory}" if it.item_subcategory else ""
            dmg = ""
            if it.item_dice_damage and it.item_dice_damage != "-":
                dmg = f" | dmg {it.item_dice_damage}"
                if it.item_damage_type:
                    dmg += f" ({it.item_damage_type})"
            label = f"{it.item_name} ({cat}{sub}){dmg}"
            inv_labels.append(label)
        if inv_labels:
            pc.inventory = inv_labels
    except Exception:
        # Keep inventory empty on failure
        pass

    return pc


def _looks_like_sheet(text: str) -> bool:
    """
    Cheap validation to see if the LLM returned something structured enough to parse.
    """
    if not text.strip():
        return False
    markers = ["ARCHETYPE:", "STATS:", "SKILLS:"]
    return any(m in text for m in markers)
