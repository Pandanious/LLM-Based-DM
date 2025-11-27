from __future__ import annotations

import re
import uuid
import random
from datetime import datetime
from textwrap import dedent
from typing import Dict, List, Optional

from src.llm_client import get_llm
from src.game.models import World_State, NPC
from src.agent.item_gen import generate_items_for_character


NPC_GEN_PROMPT_TEMPLATE = dedent("""
You are an experienced tabletop RPG worldbuilder and NPC designer.

The campaign world is described below.

WORLD SUMMARY:
{world_summary}

LORE:
{lore}

MAJOR LOCATIONS:
{major_locations}

MINOR LOCATIONS:
{minor_locations}

Players in this world:
{players}

Your task:
- Create a roster of important NPCs for this world.
- Focus on interesting personalities, clear roles, and strong hooks that invite interaction.
- Prefer to place NPCs in **minor locations** first, then major locations if needed.

NPC requirements:
- You MUST output **at least {min_npcs} distinct NPCs**.
- Try to keep the total under {max_npcs_hint} unless the location coverage rules require more.
- For EACH minor location, there must be at least:
  - one merchant-type NPC (trader, vendor, shopkeeper, fixer)
  - one leader-type NPC (mayor, boss, captain, elder, manager)
  - one quest-giver NPC (someone who offers tasks, jobs, missions, contracts)

Output format:
- Write one NPC after another in this exact structure:

NPC 1:
Name: <short unique name>
Role: <short role label, e.g. "merchant", "gang leader", "quest giver", "bartender">
Location: <one of the locations listed above (major or minor)>
Description: <2-4 sentences of flavor>
Hooks:
- <one hook sentence>
- <optional second hook>
Attitude: <one word or short phrase, e.g. "friendly", "hostile", "greedy">
Tags:
- <tag 1>
- <tag 2>

NPC 2:
Name: ...
...

Important style rules:
- Do NOT add extra sections or commentary.
- Do NOT write code.
- Do NOT repeat the world summary or lore.
- Only use the fields shown above for each NPC.
- Ensure that merchants / leaders / quest givers are clearly labeled in the Role or Tags.
""")

NPC_HEADER_RE = re.compile(r"^NPC\s+(\d+):\s*$", re.MULTILINE)


def _format_locations(locations: List[Dict[str, str]]) -> str:
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


def _split_npc_chunks(text: str) -> List[str]:
    """
    Split the LLM output into chunks, one per NPC, based on 'NPC X:' headers.
    """
    matches = list(NPC_HEADER_RE.finditer(text))
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


def _parse_field(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip()


def _parse_list_block(label: str, text: str) -> List[str]:
    """
    Extract a bullet list under a label like 'Hooks:' or 'Tags:' with minimal normalization.
    """
    pattern = rf"{label}:\s*(.+?)(?:\n\w+:|\Z)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    items: List[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if line:
            items.append(line)
    return items


def _pick_location_name(world: World_State, preferred: Optional[str]) -> str:
    """
    Try to map a free-text location name back to one of the world's major/minor
    location names. If we can't, just return the preferred text or a fallback.
    """
    all_names: List[str] = []
    for loc in (world.major_locations or []):
        name = loc.get("name")
        if name:
            all_names.append(name)
    for loc in (world.minor_locations or []):
        name = loc.get("name")
        if name:
            all_names.append(name)

    if not all_names and preferred:
        return preferred

    if preferred:
        # simple fuzzy-ish match by lowercase containment
        p = preferred.lower()
        for name in all_names:
            if p == name.lower() or p in name.lower() or name.lower() in p:
                return name

    if all_names:
        return random.choice(all_names)

    return preferred or "Unknown location"


def _label_item(item) -> str:
    """
    Build a readable label for an Item without depending on full Item type here.
    """
    name = getattr(item, "item_name", "Item")
    category = getattr(item, "item_category", "") or "gear"
    sub = getattr(item, "item_subcategory", "")
    damage = getattr(item, "item_dice_damage", "")
    damage_type = getattr(item, "item_damage_type", "")
    parts = [name, f"({category}"]
    if sub:
        parts[-1] += f"/{sub}"
    parts[-1] += ")"
    if damage and damage != "-":
        dmg_part = f" dmg {damage}"
        if damage_type:
            dmg_part += f" ({damage_type})"
        parts.append(dmg_part)
    return " ".join(parts)


def _ensure_minimum_npcs(
    world: World_State,
    npcs: Dict[str, NPC],
    min_npcs: int,
) -> None:
    """
    If the LLM produced fewer than min_npcs, pad with generic filler NPCs.
    """
    if len(npcs) >= min_npcs:
        return

    all_locations = (world.minor_locations or []) + (world.major_locations or [])
    if not all_locations:
        base_locations = ["Unknown location"]
    else:
        base_locations = [loc.get("name", "Unknown location") for loc in all_locations]

    while len(npcs) < min_npcs:
        npc_id = f"auto_{uuid.uuid4().hex[:8]}"
        loc = random.choice(base_locations)
        now = datetime.utcnow()
        npcs[npc_id] = NPC(
            npc_id=npc_id,
            world_id=world.world_id,
            name=f"Extra NPC {len(npcs) + 1}",
            role="Villager",
            location=loc,
            description="A filler NPC created automatically to reach the minimum count.",
            hooks=[],
            attitude="neutral",
            tags=["filler"],
            created_on=now,
            last_updated=now,
        )


def _ensure_roles_per_minor_location(world: World_State, npcs: Dict[str, NPC]) -> None:
    """
    Ensure that each minor location has at least one merchant / leader / quest giver.
    If missing, create simple NPCs with those roles.
    """
    role_keywords = {
        "merchant": ["merchant", "trader", "vendor", "shopkeeper", "fixer"],
        "leader": ["leader", "mayor", "boss", "captain", "elder", "manager"],
        "quest": ["quest", "mission", "job giver", "contract broker", "dispatcher"],
    }

    # Pre-build an index of NPCs by location
    by_location: Dict[str, List[NPC]] = {}
    for npc in npcs.values():
        by_location.setdefault(npc.location, []).append(npc)

    for loc in (world.minor_locations or []):
        loc_name = loc.get("name", "Unknown location")
        npcs_here = by_location.get(loc_name, [])

        lower_roles = []
        for npc in npcs_here:
            text = f"{npc.role} {' '.join(npc.tags)}".lower()
            lower_roles.append(text)

        def has_role(kind: str) -> bool:
            keywords = role_keywords[kind]
            for text in lower_roles:
                for kw in keywords:
                    if kw in text:
                        return True
            return False

        needed = []
        if not has_role("merchant"):
            needed.append("merchant")
        if not has_role("leader"):
            needed.append("leader")
        if not has_role("quest"):
            needed.append("quest giver")

        for kind in needed:
            npc_id = f"auto_{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow()
            role_label = kind
            tags = [kind.replace(" ", "_"), "auto_generated"]
            desc = (
                f"A local {kind} for {loc_name}, created automatically to ensure "
                f"every minor location has key NPC roles."
            )
            npcs[npc_id] = NPC(
                npc_id=npc_id,
                world_id=world.world_id,
                name=f"{loc_name} {kind.title()}",
                role=role_label,
                location=loc_name,
                description=desc,
                hooks=[],
                attitude="neutral",
                tags=tags,
                created_on=now,
                last_updated=now,
            )


def generate_npcs_for_world(world: World_State, max_npcs: int = 10) -> Dict[str, NPC]:
    """
    Ask the LLM to suggest a roster of NPCs for the given world, then enforce
    minimum counts and per-location role coverage.

    Returns a dict npc_id -> NPC.
    """
    llm = get_llm()

    major_locations_str = _format_locations(world.major_locations)
    minor_locations_str = _format_locations(world.minor_locations)
    players_str = ", ".join(world.players) if world.players else "Unknown players"

    # Ask the LLM for up to max_npcs. We won't pad with generic extras.
    min_npcs_base = 0  # disable filler NPC padding

    prompt = NPC_GEN_PROMPT_TEMPLATE.format(
        world_summary=world.world_summary,
        lore=world.lore,
        major_locations=major_locations_str,
        minor_locations=minor_locations_str,
        players=players_str,
        min_npcs=min_npcs_base,
        max_npcs_hint=max_npcs + 5,
    )

    result = llm(
        prompt,
        max_tokens=900,
        temperature=0.85,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw = result["choices"][0]["text"].strip()

    chunks = _split_npc_chunks(raw)
    npcs: Dict[str, NPC] = {}

    for i, chunk in enumerate(chunks, start=1):
        name = _parse_field(r"^Name:\s*(.+)$", chunk)
        role = _parse_field(r"^Role:\s*(.+)$", chunk)
        loc_raw = _parse_field(r"^Location:\s*(.+)$", chunk)
        desc = _parse_field(r"^Description:\s*(.+)$", chunk)

        hooks = _parse_list_block("Hooks", chunk)
        tags = _parse_list_block("Tags", chunk)
        attitude = _parse_field(r"^Attitude:\s*(.+)$", chunk) or "neutral"

        location = _pick_location_name(world, loc_raw or "")

        if not name:
            # Skip obviously malformed entries
            continue

        npc_id = f"{world.world_id}_npc_{i}"
        now = datetime.utcnow()

        npc_obj = NPC(
            npc_id=npc_id,
            world_id=world.world_id,
            name=name,
            role=role or "NPC",
            location=location,
            description=desc or "",
            hooks=hooks,
            attitude=attitude,
            tags=tags,
            created_on=now,
            last_updated=now,
        )
        # If this looks like a merchant, generate a small inventory
        role_text = f"{role} {' '.join(tags)}".lower()
        if any(word in role_text for word in ["merchant", "trader", "vendor", "shopkeeper"]):
            try:
                items = generate_items_for_character(
                    world_summary=world.world_summary,
                    archetype="merchant_stock",
                    count=4,
                )
                npc_obj.inventory = [_label_item(it) for it in items]
            except Exception:
                npc_obj.inventory = []

        npcs[npc_id] = npc_obj

    # Enforce per-minor-location role coverage
    _ensure_roles_per_minor_location(world, npcs)

    return npcs
