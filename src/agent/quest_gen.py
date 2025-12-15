from __future__ import annotations

import re
import uuid
from datetime import datetime
from textwrap import dedent
from typing import Dict, List, Optional

from src.llm_client import get_llm
from src.game.models import World_State, NPC, Quest
from src.agent.item_gen import generate_items_for_character

QUEST_GEN_PROMPT_TEMPLATE = dedent("""
You are an expert tabletop RPG quest designer.

The campaign world is described below.

WORLD SUMMARY:
{world_summary}

LORE:
{lore}

MAJOR LOCATIONS:
{major_locations}

MINOR LOCATIONS:
{minor_locations}

NPC ROSTER (name - role - location):
{npc_roster}

Players in this world:
{players}

Your task:
- Propose a small set of story-rich quests suitable as starting and mid-term goals.
- Tie each quest clearly to:
  - one specific quest giver (an NPC from the roster),
  - one primary target location,
  - concrete actions for the players to take.

Quest requirements:
- You MUST output at least {min_quests} quests.
- Try to keep the total under {max_quests_hint}.
- Mix different structures:
  - investigation, combat, social, travel, heists, rescues, deliveries, etc.
- Make sure quests reference the existing NPCs and locations, not invented ones.

Output format:
Write each quest in this exact structure (no extra commentary):

QUEST 1:
Title: <short title>
Giver: <NPC name from the roster>
Location: <one of the listed locations>
Summary: <2-4 sentences describing the core conflict and stakes>
Steps:
- <step 1>
- <step 2>
- <optional further steps>
Rewards:
- <reward 1>
- <reward 2>

QUEST 2:
Title: ...
...

Important style rules:
- Do NOT invent entirely new cities or regions; use the given locations.
- Do NOT invent entirely new NPCs; use the given NPC names as givers.
- Keep steps actionable and concrete.
- Do NOT write code or pseudo-JSON.
- Only use the fields listed above.
""")

QUEST_HEADER_RE = re.compile(r"^QUEST\s+(\d+):\s*$", re.MULTILINE)


def _format_locations(locations: List[dict]):
    if not locations:
        return "- (none listed)"
    lines = []
    for loc in locations:
        name = loc.get("name", "Unnamed location")
        desc = loc.get("description", "").strip()
        if desc:
            lines.append(f"- {name}: {desc}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def _format_npc_roster(npcs: Dict[str, NPC]):
    if not npcs:
        return "- (none listed)"
    lines = []
    for npc in npcs.values():
        lines.append(f"- {npc.name} - {npc.role} - {npc.location}")
    return "\n".join(lines)


def _split_quest_chunks(text: str):
    matches = list(QUEST_HEADER_RE.finditer(text))
    if not matches:
        return []
    chunks: List[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _parse_field(pattern: str, text: str):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip()


def _parse_list_block(label: str, text: str):
    pattern = rf"{label}:\s*(.+?)(?:\n\w+:|\Z)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    items: List[str] = []
    seen = set()
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-") or line.startswith("*"):
            line = line[1:].strip()
        if not line:
            continue
        lower = line.lower()
        if lower in seen:
            continue
        seen.add(lower)
        items.append(line)
    return items


def _resolve_location_name(world: World_State, raw_location: str):
    
    # Try to map a free-text location to one of the world location names
    
    candidates: List[str] = []
    for loc in (world.major_locations or []):
        name = loc.get("name")
        if name:
            candidates.append(name)
    for loc in (world.minor_locations or []):
        name = loc.get("name")
        if name:
            candidates.append(name)

    if not candidates:
        return raw_location or None

    if raw_location:
        rl = raw_location.lower()
        for c in candidates:
            cl = c.lower()
            if rl == cl or rl in cl or cl in rl:
                return c

    return raw_location or candidates[0]


def _find_npc_id_by_name(npcs: Dict[str, NPC], name: str):
    target = name.strip().lower()
    if not target:
        return None
    for npc_id, npc in npcs.items():
        if npc.name.strip().lower() == target:
            return npc_id
    return None


def generate_quests_for_world(
    world: World_State,
    npcs: Dict[str, NPC],
    max_quests: int = 5,):
    
    llm = get_llm()

    major_locations_str = _format_locations(getattr(world, "major_locations", []))
    minor_locations_str = _format_locations(getattr(world, "minor_locations", []))
    npc_roster_str = _format_npc_roster(npcs)
    players_str = ", ".join(world.players) if world.players else "Unknown players"

    min_quests = max_quests  # guarantee at least this many

    prompt = QUEST_GEN_PROMPT_TEMPLATE.format(
        world_summary=world.world_summary,
        lore=world.lore,
        major_locations=major_locations_str,
        minor_locations=minor_locations_str,
        npc_roster=npc_roster_str,
        players=players_str,
        min_quests=min_quests,
        max_quests_hint=max_quests + 3,
    )

    result = llm(
        prompt,
        max_tokens=900,
        temperature=0.8,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw = result["choices"][0]["text"].strip()
    chunks = _split_quest_chunks(raw)

    quests: Dict[str, Quest] = {}

    for i, chunk in enumerate(chunks, start=1):
        title = _parse_field(r"^Title:\s*(.+)$", chunk)
        giver_name = _parse_field(r"^Giver:\s*(.+)$", chunk)
        location_raw = _parse_field(r"^Location:\s*(.+)$", chunk)
        summary = _parse_field(r"^Summary:\s*(.+)$", chunk)

        steps = _parse_list_block("Steps", chunk)
        rewards = _parse_list_block("Rewards", chunk)
        reward_items: List[str] = []

        # Try to generate item rewards 
        try:
            desired = len(rewards) if rewards else 2
            desired = max(1, min(desired, 4))
            items = generate_items_for_character(
                world_summary=world.world_summary,
                archetype="quest_reward",
                count=desired,
            )
            for it in items:
                label_parts = [it.item_name or "Item"]
                cat = it.item_category or ""
                sub = it.item_subcategory or ""
                if cat:
                    cat_text = cat
                    if sub:
                        cat_text += f"/{sub}"
                    label_parts.append(f"({cat_text})")
                dmg = it.item_dice_damage or ""
                if dmg and dmg != "-":
                    dt = it.item_damage_type or ""
                    dmg_text = f"dmg {dmg}"
                    if dt:
                        dmg_text += f" ({dt})"
                    label_parts.append(dmg_text)
                reward_items.append(" ".join(label_parts))
        except Exception:
            reward_items = []

        if not title:
            continue  # skip malformed

        quest_id = f"{world.world_id}_quest_{i}"
        now = datetime.utcnow()

        resolved_location = _resolve_location_name(world, location_raw)
        giver_id = _find_npc_id_by_name(npcs, giver_name)

        quests[quest_id] = Quest(
            quest_id=quest_id,
            world_id=world.world_id,
            title=title,
            summary=summary or "",
            giver_npc_id=giver_id,
            giver_name=giver_name or None,
            target_location=resolved_location,
            steps=steps,
            rewards=rewards,
            reward_items=reward_items,
            status="available",
            created_on=now,
            last_updated=now,
        )

    return quests
