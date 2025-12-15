from __future__ import annotations
import json
import re
from pathlib import Path
from collections import Counter
from math import log1p
from typing import Iterable, List, Tuple, Dict

SAVES_DIR = Path("saves")

# tokenize querry
def _lower_case(text: str):
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
    # Yield (id, text) snippets from a game bundle.

    # World
    world = doc.get("world") or {}
    if world:
        yield ("world_summary", world.get("world_summary", ""))
        yield ("world_lore", world.get("lore", ""))
    # Player Char (if exist)
    for pc_id, pc in (doc.get("pcs") or {}).items():
        name = pc.get("name",pc_id)
        player = pc.get("player_name","")
        cls = pc.get("archetype","")
        stats = pc.get("stats",{})
        inv = pc.get("inventory",[])
        summary = f"{name} - {cls} by {player}. Stats: {stats}. Inventory: {inv}"
        yield (f"pc:{name}",summary)
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

    # Current State
    state =  doc.get("state") or {}
    if state:
        loc = state.get("location","")
        action = state.get("current_action","")
        notes = state.get("notes","")
        yield ("state",f"Location: {loc}. Action: {action}. Notes: {notes}")
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
    # TF-IDF keyword scorer with bigram boost

    tokens = _lower_case(query)
    if not tokens or not snippets:
        return []
    
    df = Counter()

    tokenized: List[Tuple[str,str,Counter,Counter]] = []
    for id,text in snippets:
        t_tokens = _lower_case(text)
        if not t_tokens:
            continue
        token_counts = Counter(t_tokens)
        token_bigrams = Counter(" ".join(t_tokens[i:i+2]) for i in range(len(t_tokens)-1)) 
        tokenized.append((id,text,token_counts,token_bigrams)) 
        df.update(set(t_tokens))

    if not tokenized:
        return []
    
    N = len(tokenized)
    
    idf = {w: 1.0 +log1p(N / (1+c)) for w,c in df.items() }

    q_counts = Counter(tokens)
    q_bigrams = Counter(" ".join(tokens[i:i+2]) for i in range(len(tokens) - 1))
    results = []

    for id, text, token_counts, token_bigrams in tokenized:
        kw_score = sum((q_counts[w] * token_counts[w]) * idf.get(w,1.0) for w in q_counts if w in token_counts)
        if kw_score <= 0:
            continue
        bigram_score = sum(q_bigrams[b] * token_bigrams[b] for b in q_bigrams if b in token_bigrams)
        score = float(kw_score + 1.0 * bigram_score)
        results.append((id,text,score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]



def format_context_blocks(hits):
    # Turn hits into labeled blocks to prepend to the prompt.
    lines = []
    for i, (id, text, _) in enumerate(hits,1):
        lines.append(f"[CONTEXT {i} | {id}]\n{text}\n")
    return "\n".join(lines)
