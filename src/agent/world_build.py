import re
from datetime import datetime
from textwrap import dedent
from typing import List, Tuple

from src.llm_client import get_llm
from src.game.models import World_State


WORLD_GEN_PROMPT_TEMPLATE = dedent("""
You are a creative tabletop RPG worldbuilder.

The user describes an idea for a campaign world. Based on this idea, write:

1. A world summary (3–6 sentences).
2. Lore (2–5 short paragraphs).
3. A list of important character skills used in this world.

Write normal prose. At the END of your reply, add a SKILLS section like:

SKILLS:
- Skill name 1
- Skill name 2
- Skill name 3

Do not write code. Do not repeat these instructions.

WORLD IDEA:
{setting}
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

    title, world_summary, lore, skills = _parse_world_output(
        raw_text, fallback_setting=setting_prompt
    )

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
    )

    return world


def _sanitize_world_text(text: str) -> str:
    """
    Light cleanup: remove obvious code tags and trim.
    """
    cleaned = text.replace("<code>", "").replace("</code>", "")
    cleaned = cleaned.strip()
    return cleaned


def _parse_skills_section(skills_text: str) -> List[str]:
    """
    Extract skills from a 'SKILLS:' section with lines like '- Skill'.
    """
    skills: List[str] = []
    lines = skills_text.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Stop if some new big header starts (rare here)
        if re.match(r"^[A-Z ]+:$", stripped):
            break

        if stripped.startswith("-"):
            skill = stripped.lstrip("-").strip()
            if skill:
                skills.append(skill)
        else:
            # Also allow plain lines as skill names
            skills.append(stripped)

    # de-duplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for s in skills:
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        deduped.append(s)
    return deduped


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


def _parse_world_output(text: str, fallback_setting: str) -> Tuple[str, str, str, List[str]]:
    """
    Parse model output into (title, world_summary, lore, skills).
    Simple, forgiving:
    - Split off SKILLS: section
    - First paragraph = world summary
    - Remaining paragraphs = lore
    - Title inferred from summary
    """
    cleaned = _sanitize_world_text(text)
    if not cleaned:
        return "Untitled Campaign", fallback_setting, "", []

    # Split off SKILLS section if present
    parts = re.split(r"\bSKILLS\s*:\s*", cleaned, maxsplit=1, flags=re.IGNORECASE)
    main_text = parts[0].strip()
    skills_text = parts[1].strip() if len(parts) > 1 else ""

    skills = _parse_skills_section(skills_text) if skills_text else []

    paragraphs = [p.strip() for p in main_text.split("\n\n") if p.strip()]

    if not paragraphs:
        return "Untitled Campaign", fallback_setting, main_text, skills

    world_summary = paragraphs[0]
    lore = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""

    title = _infer_title_from_summary(world_summary, fallback_setting)

    return title, world_summary, lore, skills
