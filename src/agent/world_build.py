# src/agent/world_build.py

from datetime import datetime
from textwrap import dedent
from typing import List

from src.llm_client import get_llm
from src.game.models import World_State  # make sure this matches your dataclass name

import re

HEADER_LINES = [
    r"^---\s*$",
    r"^CAMPAIGN TITLE:.*",
    r"^WORLD SUMMARY:.*",
    r"^LORE:.*",
    r"^TITLE:.*",
]

BOT_SNIPPETS = [
    "I am a bot and this action was performed automatically",
]


def _clean_paragraph(text: str) -> str:
    """Remove headers, bot footers, trivial junk from a block of text."""
    lines = []
    seen_lines = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # drop header-ish lines
        if any(re.match(pat, line, re.IGNORECASE) for pat in HEADER_LINES):
            continue

        # drop obvious bot footer lines
        if any(snippet in line for snippet in BOT_SNIPPETS):
            continue

        # avoid exact duplicate lines
        if line in seen_lines:
            continue
        seen_lines.add(line)

        lines.append(line)

    return "\n".join(lines).strip()


def _sanitize_world_text(raw: str) -> str:
    """
    Clean raw LLM output:
    - strip code tags / </code> etc.
    - drop headers, footers, duplicates
    - normalize paragraphs
    """
    text = raw.replace("<code>", "").replace("</code>", "")
    text = text.strip()

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    cleaned_paras = []
    seen_paras = set()
    for p in paras:
        cleaned = _clean_paragraph(p)
        if not cleaned:
            continue
        if cleaned in seen_paras:
            continue
        seen_paras.add(cleaned)
        cleaned_paras.append(cleaned)

    return "\n\n".join(cleaned_paras).strip()


def _clean_title(title: str, world_summary: str, fallback_setting: str) -> str:
    """
    Clean obvious template/markdown junk from the title.
    If it still looks wrong, try to infer a title from the summary.
    """
    t = title.strip()

    # strip markdown headings and templates
    t = re.sub(r"^#+\s*", "", t)  # remove leading #, ##, etc.
    t = re.sub(r"^YOUR ANSWER\s*:?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^TITLE\s*:?\s*", "", t, flags=re.IGNORECASE)

    # if it still looks like instructions, derive from summary
    lower = t.lower()
    if (not t) or "short, punchy" in lower or "your answer" in lower or t == "#Title":
        # try pattern: "<Something> is ..." at start of summary
        m = re.match(r'^"?([^".]+?)"?\s+is\b', world_summary)
        if m:
            t = m.group(1).strip()
        else:
            # fallback: first sentence of summary
            m2 = re.match(r"^(.+?)\.", world_summary)
            if m2:
                t = m2.group(1).strip()

    if not t:
        t = "Untitled Campaign"

    return t


def _strip_section_headers(text: str) -> str:
    """Remove 'Summary:', '#Lore', etc. from inside summary/lore."""
    out_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#+\s*(summary|lore|campaign title)[:\s]*$", stripped, flags=re.I):
            continue
        if re.match(r"^(summary|lore|title)[:\s]*$", stripped, flags=re.I):
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()

def _infer_title_from_summary(world_summary: str, fallback_setting: str) -> str:
    """
    Derive a campaign title from the summary text.
    Ignores junk like 'Sample answer', 'YOUR ANSWER', etc.
    """
    s = world_summary.strip()

    # Strip obvious headers like 'Summary:', '# Title', etc.
    s = re.sub(r"^#+\s*(summary|title)[:\s]*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"^(summary|title)[:\s]*", "", s, flags=re.IGNORECASE).strip()

    # If line still looks like template junk, ignore it
    bad_phrases = ["sample answer", "your answer", "short, punchy", "write a title"]
    if any(p in s.lower() for p in bad_phrases):
        s = ""

    # Pattern: "<Something> is ..." at the start of the summary
    #   e.g. "The City of Broken Dreams is a cyberpunk world..."
    m = re.match(r'^"?([^".]+?)"?\s+is\b', s)
    if m:
        title = m.group(1).strip()
    else:
        # Fallback: take the first sentence or up to ~60 chars
        m2 = re.match(r"^(.+?)[\.\n]", s)
        if m2:
            title = m2.group(1).strip()
        else:
            title = s[:60].strip()

    # If after all that it's still empty or generic, use the setting prompt as a base
    if not title:
        title = fallback_setting[:60].strip() or "Untitled Campaign"

    return title

def _parse_world_sections(text: str, fallback_setting: str) -> tuple[str, str, str]:
    """
    Very forgiving parsing:
    - sanitize the text
    - treat the first paragraph as summary
    - treat remaining paragraphs as lore
    - derive the title from the summary only
    """
    cleaned = _sanitize_world_text(text)

    if not cleaned:
        return "Untitled Campaign", fallback_setting, ""

    paras = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

    if not paras:
        return "Untitled Campaign", fallback_setting, cleaned

    # First paragraph: world summary
    world_summary = paras[0]
    # Rest: lore
    lore = "\n\n".join(paras[1:]) if len(paras) > 1 else ""

    # Clean obvious section headers out of summary/lore
    world_summary = _strip_section_headers(world_summary)
    lore = _strip_section_headers(lore)

    # Now derive a good title purely from the summary
    title = _infer_title_from_summary(world_summary, fallback_setting)

    return title, world_summary, lore

WORLD_GEN_PROMPT_TEMPLATE = dedent("""
You are a creative tabletop RPG worldbuilder.

Using the user's idea, write the following:

1. A campaign title (one short line).
2. A world summary (3–6 sentences).
3. Lore (3–5 paragraphs of rich detail: regions, factions, conflicts, mysteries, tone).

Do NOT explain what you're doing.  
Do NOT repeat these instructions.
Do NOT reveal infomration hidden to the players.  
Just write the title, summary, and lore as normal prose.
You must answer only the latest message from the player.
You must provide **one single answer and then stop**.

USER IDEA:
{setting}
                                   
""")


def generate_world_state(setting_prompt: str, players: List[str], world_id: str = "default") -> World_State:
    """
    Ask the LLM to invent a world for the given setting + players.
    Returns a World_State object.
    """
    llm = get_llm()

    player_list = players or ["Player"]
    #players_str = ", ".join(player_list) if player_list else "Unnamed adventurers"

    prompt = WORLD_GEN_PROMPT_TEMPLATE.format(
        setting=setting_prompt)

    result = llm(
        prompt,
        max_tokens=1200,       # plenty of room for multi-paragraph lore
        temperature=0.8,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw_text = result["choices"][0]["text"].strip()

    title, world_summary, lore = _parse_world_sections(raw_text, fallback_setting=setting_prompt)

    now = datetime.utcnow()

    world = World_State(
        world_id=world_id,
        title=title,
        setting_prompt=setting_prompt,
        world_summary=world_summary,
        lore=lore,
        players=player_list,
        created_on=now,      # make sure these match your dataclass fields
        last_played=now,
        notes=[],
    )

    return world
