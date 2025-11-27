import re
import uuid
from textwrap import dedent
from typing import List

from src.llm_client import get_llm
from src.game.models import Item


ITEM_GEN_PROMPT_TEMPLATE = dedent("""
You are an RPG gear quartermaster. Generate starter items for a player character.

World summary:
{world_summary}

Character archetype: {archetype}

Output exactly {count} items covering at least one weapon, one armor/shield, one consumable, and one utility/gear item. Follow this format (one after another, no extra commentary):

ITEM 1:
Name: <short name>
Category: <weapon|armor|gear|consumable|trinket>
Subcategory: <e.g., sword, bow, potion, kit>
Damage: <dice expression or "-" if not a weapon>
Damage Type: <slashing|piercing|bludgeoning|fire|cold|poison|psychic|force|radiant|necrotic|acid|thunder|lightning|healing|none>
Properties: <comma-separated tags like finesse, light, two_handed, ranged, thrown, shield, heavy, ammo, consumable, utility>

ITEM 2:
...
""")

ITEM_HEADER_RE = re.compile(r"^ITEM\s+(\d+):\s*$", re.MULTILINE)


def _split_item_chunks(text: str) -> List[str]:
    matches = list(ITEM_HEADER_RE.finditer(text))
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


def _parse_field(label: str, text: str) -> str:
    m = re.search(rf"^{label}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_properties(raw: str) -> List[str]:
    if not raw:
        return []
    parts = []
    for part in raw.replace(";", ",").split(","):
        token = part.strip()
        if token:
            parts.append(token)
    return parts


def generate_items_for_character(
    world_summary: str,
    archetype: str,
    count: int = 4,
) -> List[Item]:
    """
    Ask the LLM for a small set of starter items and parse them into Item objects.
    """
    llm = get_llm()

    prompt = ITEM_GEN_PROMPT_TEMPLATE.format(
        world_summary=world_summary or "No summary provided.",
        archetype=archetype or "unspecified",
        count=count,
    )

    result = llm(
        prompt,
        max_tokens=400,
        temperature=0.75,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )

    raw = result["choices"][0]["text"].strip()
    chunks = _split_item_chunks(raw)

    items: List[Item] = []
    for i, chunk in enumerate(chunks, start=1):
        name = _parse_field("Name", chunk)
        category = _parse_field("Category", chunk) or "gear"
        subcategory = _parse_field("Subcategory", chunk)
        damage = _parse_field("Damage", chunk)
        damage_type = _parse_field("Damage Type", chunk)
        properties = _parse_properties(_parse_field("Properties", chunk))

        if not name:
            continue

        items.append(
            Item(
                item_id=f"item_{uuid.uuid4().hex[:8]}_{i}",
                item_name=name,
                item_category=category,
                item_subcategory=subcategory,
                item_dice_damage=damage,
                item_damage_type=damage_type,
                item_properties=properties,
            )
        )

        if len(items) >= count:
            break

    return items
