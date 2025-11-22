import re
from datetime import datetime
from textwrap import dedent
from typing import List, Tuple, Dict

from src.llm_client import get_llm
from src.game.models import World_State


WORLD_GEN_PROMPT_TEMPLATE = dedent("""
You are an expert tabletop RPG worldbuilder. Expand the user's idea into a fully-realized campaign world.

Write your answer in plain text with the following sections, in this exact order:

========================================
WORLD SUMMARY:
========================================
Write 3–8 sentences describing the core identity of the world.
Include:
- genre
- tone
- major conflict(s)
- important themes
- what makes this world unique

========================================
LORE:
========================================
Write 3–5 paragraphs of deeper worldbuilding.
Include:
- major cultures or civilizations
- important regions and landmarks
- historical conflicts or myths
- political or supernatural forces
- current tensions that adventurers might encounter

========================================
MAJOR LOCATIONS (3):
========================================
List exactly THREE major exploration hubs.
For each:
- NAME (1–3 words)
- 2–4 sentences describing purpose, atmosphere, and important features.

Format example:
1. NAME — description...

========================================
MINOR LOCATIONS (5):
========================================
List exactly FIVE smaller adventuring or quest-oriented locations.
For each:
- NAME
- 1–3 sentences describing its danger, mystery, or purpose.

Use the same numbering format.

========================================
WORLD SKILLS:
========================================
List 10–20 skills used by characters in this world.
One skill per line.
No descriptions.

========================================
THEMES & TONE:
========================================
Write 3–6 bullet points about the overall mood, narrative direction, and recurring motifs.

========================================
PLAYER START :
========================================
Start the player in one of the locations, based upon the character they create.                                   

{setting}

Do NOT:
- write code
- use backticks
- add extra sections
- repeat these instructions
- invent new headers not listed above
- ask questions

Write all text in a consistent, friendly, descriptive TTRPG tone.
""")


def generate_world_state(setting_prompt: str, players: List[str], world_id: str = "default") -> World_State:
    """
    Ask the LLM to invent a world (summary, lore, skills) for the given setting + players.
    Returns a World_State object.
    """
    llm = get_llm()

    prompt = WORLD_GEN_PROMPT_TEMPLATE.format(
        setting=setting_prompt,
    )

    result = llm(
        prompt,
        max_tokens=900,
        temperature=0.8,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw_text = result["choices"][0]["text"].strip()

    (
        title,
        world_summary,
        lore,
        skills,
        major_locations,
        minor_locations,
        themes,
    ) = _parse_world_output(raw_text, fallback_setting=setting_prompt)

    now = datetime.utcnow()

    world = World_State(
        world_id=world_id,
        title=title,
        setting_prompt=setting_prompt,
        world_summary=world_summary,
        lore=lore,
        players=players,
        created_on=now,
        last_played=now,
        notes=[],
        skills=skills,
        major_locations=major_locations,
        minor_locations=minor_locations,
        themes=themes,
    )

    return world


def _sanitize_world_text(text: str) -> str:
    """
    Light cleanup: remove obvious code tags and trim.
    """
    cleaned = text.replace("<code>", "").replace("</code>", "")
    cleaned = cleaned.strip()
    return cleaned


def _infer_title_from_summary(world_summary: str, fallback_setting: str) -> str:
    """
    Derive a campaign title from the summary text.
    Gemma sometimes echoes templates; we ignore obvious junk.
    """
    s = world_summary.strip()

    # Strip simple headers
    s = re.sub(r"^#+\s*(summary|title)[:\s]*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"^(summary|title)[:\s]*", "", s, flags=re.IGNORECASE).strip()

    bad_bits = ["sample answer", "your answer", "short, punchy", "write a title"]
    if any(b in s.lower() for b in bad_bits):
        s = ""

    # Pattern: "<Something> is ..." at the start of the summary
    m = re.match(r'^"?([^".]+?)"?\s+is\b', s)
    if m:
        title = m.group(1).strip()
    else:
        # Fallback: first sentence or first ~60 chars
        m2 = re.match(r"^(.+?)[\.\n]", s)
        if m2:
            title = m2.group(1).strip()
        else:
            title = s[:60].strip()

    if not title:
        # fallback to setting prompt truncated
        fallback = fallback_setting.strip()
        if not fallback:
            return "Untitled Campaign"
        # maybe pattern "<Something> is" in setting
        m3 = re.match(r'^"?([^".]+?)"?\s+is\b', fallback)
        if m3:
            return m3.group(1).strip()
        return fallback[:60].strip()

    return title


def _sanitize_world_text(text: str) -> str:
    """
    Light cleanup: remove obvious code tags and trim.
    """
    cleaned = text.replace("<code>", "").replace("</code>", "")
    return cleaned.strip()


def _split_sections(text: str) -> Dict[str, str]:
    """
    Split the model output into sections based on our headers:

    WORLD SUMMARY:
    LORE:
    MAJOR LOCATIONS (3):
    MINOR LOCATIONS (5):
    WORLD SKILLS:
    THEMES & TONE:
    """
    sections: Dict[str, List[str]] = {}
    current_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # skip empty separator lines like "====="
        if set(line) == {"="}:
            continue

        # detect headers (we use startswith so the model can be a bit fuzzy)
        if line.upper().startswith("WORLD SUMMARY:"):
            current_key = "WORLD SUMMARY"
            sections[current_key] = []
            continue
        elif line.upper().startswith("LORE:"):
            current_key = "LORE"
            sections[current_key] = []
            continue
        elif line.upper().startswith("MAJOR LOCATIONS"):
            current_key = "MAJOR LOCATIONS"
            sections[current_key] = []
            continue
        elif line.upper().startswith("MINOR LOCATIONS"):
            current_key = "MINOR LOCATIONS"
            sections[current_key] = []
            continue
        elif line.upper().startswith("WORLD SKILLS"):
            current_key = "WORLD SKILLS"
            sections[current_key] = []
            continue
        elif line.upper().startswith("THEMES & TONE"):
            current_key = "THEMES & TONE"
            sections[current_key] = []
            continue

        if current_key is not None:
            sections[current_key].append(raw_line)

    # join lines back into strings
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _parse_locations_section(block: str) -> List[Dict[str, str]]:
    """
    Parse a numbered locations section into a list of {name, description} dicts.

    Expected formats, roughly:
    1. NAME — description...
    2. NAME - description...
    """
    locations: List[Dict[str, str]] = []

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Must start with a number and a dot to be considered a location entry
        m = re.match(r"^\d+\.\s*(.+)$", line)
        if not m:
            continue

        rest = m.group(1).strip()

        # Try to split name / description on "—" or "-"
        name = rest
        desc = ""
        if "—" in rest:
            name_part, desc_part = rest.split("—", 1)
            name = name_part.strip()
            desc = desc_part.strip()
        elif " - " in rest:
            name_part, desc_part = rest.split(" - ", 1)
            name = name_part.strip()
            desc = desc_part.strip()
        else:
            # no clear separator, treat entire rest as description
            name = rest
            desc = ""

        locations.append(
            {
                "name": name,
                "description": desc,
            }
        )

    return locations


def _parse_bullet_list(block: str) -> List[str]:
    """
    Parse a simple bullet list ("- item" or "• item") into a list of strings.
    Used for world skills and themes.
    """
    items: List[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # strip bullet prefixes
        if line.startswith("-") or line.startswith("•"):
            line = line[1:].strip()
        if line:
            items.append(line)
    return items


def _parse_world_output(text: str, fallback_setting: str) -> Tuple[
    str, str, str, List[str], List[Dict[str, str]], List[Dict[str, str]], List[str]
]:
    """
    Parse model output into:
      (title, world_summary, lore, skills, major_locations, minor_locations, themes)

    Matches the template sections:
    - WORLD SUMMARY
    - LORE
    - MAJOR LOCATIONS (3)
    - MINOR LOCATIONS (5)
    - WORLD SKILLS
    - THEMES & TONE
    """
    cleaned = _sanitize_world_text(text)
    if not cleaned:
        return "Untitled Campaign", fallback_setting, "", [], [], [], []

    sections = _split_sections(cleaned)

    world_summary = sections.get("WORLD SUMMARY", "").strip()
    if not world_summary:
        world_summary = fallback_setting.strip()

    lore = sections.get("LORE", "").strip()

    major_block = sections.get("MAJOR LOCATIONS", "")
    minor_block = sections.get("MINOR LOCATIONS", "")
    skills_block = sections.get("WORLD SKILLS", "")
    themes_block = sections.get("THEMES & TONE", "")

    major_locations = _parse_locations_section(major_block) if major_block else []
    minor_locations = _parse_locations_section(minor_block) if minor_block else []

    skills = _parse_bullet_list(skills_block)
    themes = _parse_bullet_list(themes_block)

    # Use your existing title inference helper
    title = _infer_title_from_summary(world_summary, fallback_setting)

    return title, world_summary, lore, skills, major_locations, minor_locations, themes
