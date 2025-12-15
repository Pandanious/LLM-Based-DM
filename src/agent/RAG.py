from __future__ import annotations
import json
import re
from pathlib import Path
from collections import Counter
from typing import Iterable, List, Tuple, Dict

SAVES_DIR = Path("saves")


def _tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _load_json_files(root: Path):
    docs = []
    for path in root.glob("**/*.json"):
        try:
            docs.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return docs


def _flatten_snippets(doc: dict):
    # Yield (id, text) snippets from a game bundle-like dict.
    # World
    world = doc.get("world") or {}
    if world:
        yield ("world_summary", world.get("world_summary", ""))
        yield ("world_lore", world.get("lore", ""))
    # NPCs
    for npc_id, npc in (doc.get("npcs") or {}).items():
        name = npc.get("name", npc_id)
        desc = npc.get("description", "")
        loc = npc.get("location", "")
        yield (f"npc:{name}", f"{name}. {loc}. {desc}")
    # Quests
    for qid, q in (doc.get("quests") or {}).items():
        title = q.get("title", qid)
        status = q.get("status", "unknown")
        giver = q.get("giver_name", "")
        desc = q.get("description", "")
        yield (f"quest:{title}", f"{title} [{status}] {giver}. {desc}")
    # Notes / turns
    for entry in (doc.get("turn_log", {}).get("entries", []) or []):
        text = entry.get("content") or entry.get("note") or ""
        if text:
            yield ("turn_note", text)


def build_corpus(root: Path = SAVES_DIR):
    # Collect small text snippets from all save files
    snippets = []
    for doc in _load_json_files(root):
        for sid, text in _flatten_snippets(doc):
            t = (text or "").strip()
            if t:
                snippets.append((sid, t))
    return snippets


def search_snippets(query: str, snippets: List[Tuple[str, str]], top_k: int = 5):
    # simple keyword scorer
    q_tokens = _tokenize(query)
    q_counts = Counter(q_tokens)
    results = []
    for sid, text in snippets:
        t_tokens = _tokenize(text)
        t_counts = Counter(t_tokens)
        score = sum(min(q_counts[w], t_counts[w]) for w in q_counts)
        if score > 0:
            results.append((sid, text, float(score)))
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]


def format_context_blocks(hits):
    """Turn hits into labeled blocks to prepend to the prompt."""
    lines = []
    for i, (_, text, _) in enumerate(hits, 1):
        lines.append(f"[CONTEXT {i}]\n{text}\n")
    return "\n".join(lines)
