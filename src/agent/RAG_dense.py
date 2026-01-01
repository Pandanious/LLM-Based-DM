from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

import numpy as np

Save_dir = Path("saves/games")
default_model = "all-MiniLM-L6-v2"
model_dir = Path("model")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "game"

# collect corpus from split saves
def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@lru_cache(maxsize=1)
def _ensure_model_download():
    model_dir.mkdir(parents=True, exist_ok=True)
    from sentence_transformers import SentenceTransformer
    SentenceTransformer(default_model, cache_folder=str(model_dir))
    return True


def collect_snippets(game_id, root):
    x = Path(root) / _slug(game_id)
    if not x.exists():
        return []
    snippets = []

    # collect world info

    world = _read_json(x / "world.json") or {}
    if world:
        snippets.append(("world:summary", world.get("world_summary", "")))
        snippets.append(("world:lore", world.get("lore", "")))
        for loc in world.get("major_locations", []):
            snippets.append((f"loc:{loc.get('name','')}", loc.get("description", "")))
        for loc in world.get("minor_locations", []):
            snippets.append((f"loc_minor:{loc.get('name','')}", loc.get("description", "")))

    # collect player char info

    pcs = _read_json(x / "players.json") or {}
    for pc_id, pc in pcs.items():
        name = pc.get("name", pc_id)
        p_summary = (
            f"{name} ({pc.get('archetype','')}) by {pc.get('player_name','')}. "
            f"Stats: {pc.get('stats',{})}. Inventory: {pc.get('inventory',[])}"
        )
        snippets.append((f"pc:{name}", p_summary))


    # collect NPC

    npcs = _read_json(x / "npcs.json") or {}
    for npc_id, npc in npcs.items():
        snippets.append(
            (
                f"npc:{npc.get('name', npc_id)}",
                f"{npc.get('name','')}. {npc.get('location','')}. {npc.get('description','')}",
            )
        )
 

    # collect quests

    quests = _read_json(x / "quests.json") or {}
    for q_id, q in quests.items():
        snippets.append(
            (
                f"quest:{q.get('title', q_id)}",
                f"{q.get('title','')} [{q.get('status','unknown')}] "
                f"{q.get('giver_name','')}. {q.get('summary', q.get('description',''))}",
            )
        )

    # collect turn info
    turns = _read_json(x / "turns.json") or {}
    for entry in turns.get("entries", []):
        txt = entry.get("description") or entry.get("content") or ""
        if txt:
            snippets.append(("turn", txt))

    return [(sid, (text or "").strip()) for sid, text in snippets if (text or "").strip()]
    
# Embeddings

class Embedder:
    def __init__(self, model_name = default_model):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, cache_folder=str(model_dir))

    def embed(self, texts):
        return np.asarray(
            self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        )

            
# Storing local vector

class VectorStore:
    def __init__(self, dir):
        self.dir = Path(dir)
        self.emb_path = self.dir / "embeddings.npy"
        self.meta_path = self.dir / "meta.jsonl"
        self._embeddings = None
        self._meta = None
        _ensure_model_download()


    def build(self, snippets, embedder: Embedder):
        self.dir.mkdir(parents=True,exist_ok = True)
        texts = [t for _, t in snippets]
        if not texts:
            return
        emb = embedder.embed(texts)
        np.save(self.emb_path, emb)
        with self.meta_path.open("w", encoding="utf-8") as f:
            for sid, text in snippets:
                f.write(json.dumps({"id": sid, "text": text}) + "\n")
        self._embeddings, self._meta = emb, [{"id": i, "text": t} for i, t in snippets]

        
    def _load(self):
        if self._embeddings is None and self.emb_path.exists():
            self._embeddings = np.load(self.emb_path)
        if self._meta is None and self.meta_path.exists():
            self._meta = [json.loads(line) for line in self.meta_path.read_text(encoding = "utf-8").splitlines()]


    def search(self, query, embedder: Embedder, top_k=5):
        self._load()
        if self._embeddings is None or not query.strip():
            return []
        q_emb = embedder.embed([query])[0]
        scores = (self._embeddings @ q_emb).tolist()
        meta = self._meta or []
        hits = [
                (meta[i]["id"], meta[i]["text"], float(scores[i])) for i in range(len(scores))]
        hits.sort(key=lambda x: x[2], reverse=True)
        return hits[:top_k]
    

# funcs to call

def build_idx(game_id, embedder: Embedder, saves_root=Save_dir):
    snippets = collect_snippets(game_id, root=saves_root)
    store = VectorStore(Path(saves_root) / _slug(game_id) / "index")
    store.build(snippets, embedder)
    return store

def search(game_id, query, embedder: Embedder, top_k=5, saves_root=Save_dir):
    store = VectorStore(Path(saves_root) / _slug(game_id) / "index")
    return store.search(query, embedder, top_k=top_k)

def context_block_format(hits):
    lines = []
    for i, (s_id, text, _) in enumerate(hits, 1):
        lines.append(f"[CONTEXT {i} | {s_id}]\n{text}\n")
    return "\n".join(lines)
    
