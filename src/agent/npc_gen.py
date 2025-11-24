
import re
from datetime import datetime
from textwrap import dedent
from typing import Dict, List

from src.llm_client import get_llm
from src.game.models import World_State, NPC

NPC_GEN_PROMPT_TEMPLATE = dedent("""
You are an experienced tabletop RPG designer.

The following is a campaign world. Create a cast of NPCs who belong in it.

WORLD SUMMARY:
{world_summary}

LORE (excerpt):
{lore_excerpt}

MAJOR LOCATIONS:
{major_locations_text}

MINOR LOCATIONS:
{minor_locations_text}

TASK:
- Create 6–10 distinct NPCs.
- Spread them across the locations above (major and minor).
- Mix roles: quest-givers, merchants, local leaders, villains, informants, weirdos.
- Include at least 2 NPCs with obvious quest hooks and secrets.
- All NPCs should fit the tone and themes of the world.

OUTPUT FORMAT (no extra commentary, no backticks, no code):

NPC 1
NAME: <name>
ROLE: <short role or archetype>
LOCATION: <one of the locations above>
ATTITUDE: <friendly/hostile/cautious/etc.>
TAGS: <comma-separated tags>

DESCRIPTION:
<2–4 sentences about personality, mannerisms, goals>

HOOKS:
- <plot hook 1>
- <plot hook 2>

NPC 2
NAME: ...
...

Do NOT explain what you are doing.
Do NOT include system-level commentary.
Just output the NPC blocks in the format above.
""")

def generate_npcs_for_world(world: World_State, max_npcs: int = 10) -> Dict[str,NPC]:
    # generates NPCs based on world_state data. Returns a dict npc_id.

    llm = get_llm()

    major_locations_text = "\n".join(
        f"- {loc.get('name','Unnamed')}: {loc.get('description','')}"
        for loc in world.major_locations
    ) or "(none listed)"

    minor_locations_text = "\n".join(
        f"- {loc.get('name','Unnamed')}: {loc.get('description','')}"
        for loc in world.minor_locations
    ) or "(none listed)"

    lore_excerpt = world.lore[:1200]

    prompt = NPC_GEN_PROMPT_TEMPLATE.format(
        world_summary=world.world_summary,
        lore_excerpt=lore_excerpt,
        major_locations_text=major_locations_text,
        minor_locations_text=minor_locations_text,
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
    return _parse_npc_blocks(raw, world, max_npcs=max_npcs)

def _parse_npc_blocks(text: str, world: World_State, max_npcs: int = 10) -> Dict[str, NPC]:
    """
    Parse NPC blocks from output.
    """
    lines = text.splitlines()

    npcs: Dict[str, NPC] = {}
    current_block: List[str] = []

    for line in lines:
        if re.match(r"^NPC\s+\d+", line.strip(), flags=re.IGNORECASE):
            # Start of new NPC block
            if current_block:
                npc = _parse_single_npc("\n".join(current_block), world)
                if npc:
                    npcs[npc.npc_id] = npc
                    if len(npcs) >= max_npcs:
                        return npcs
                current_block = []
            current_block.append(line)
        else:
            current_block.append(line)

    # flush last one
    if current_block and len(npcs) < max_npcs:
        npc = _parse_single_npc("\n".join(current_block), world)
        if npc:
            npcs[npc.npc_id] = npc

    return npcs


def _parse_single_npc(block: str, world: World_State) -> NPC | None:
    name_match = re.search(r"NAME:\s*(.+)", block, flags=re.IGNORECASE)
    if not name_match:
        return None

    role_match = re.search(r"ROLE:\s*(.+)", block, flags=re.IGNORECASE)
    loc_match = re.search(r"LOCATION:\s*(.+)", block, flags=re.IGNORECASE)
    att_match = re.search(r"ATTITUDE:\s*(.+)", block, flags=re.IGNORECASE)
    tags_match = re.search(r"TAGS:\s*(.+)", block, flags=re.IGNORECASE)

    desc_match = re.search(
        r"DESCRIPTION:\s*(.+?)(?:\nHOOKS:|\Z)",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    hooks_match = re.search(
        r"HOOKS:\s*(.+)",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )

    name = name_match.group(1).strip()
    role = role_match.group(1).strip() if role_match else ""
    location = loc_match.group(1).strip() if loc_match else ""
    attitude = att_match.group(1).strip() if att_match else "neutral"

    tags_raw = tags_match.group(1).strip() if tags_match else ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    desc = desc_match.group(1).strip() if desc_match else ""
    hooks_block = hooks_match.group(1) if hooks_match else ""

    hooks = []
    for line in hooks_block.splitlines():
        l = line.strip()
        if l.startswith("-"):
            l = l[1:].strip()
        if l:
            hooks.append(l)

    npc_id = f"{world.world_id}_npc_{name.lower().replace(' ', '_')}"
    now = datetime.utcnow()

    return NPC(
        npc_id=npc_id,
        world_id=world.world_id,
        name=name,
        role=role,
        location=location,
        desc=desc,
        hooks=hooks,
        attitude=attitude,
        tags=tags,
        created_on=now,
        last_updated=now,
    )