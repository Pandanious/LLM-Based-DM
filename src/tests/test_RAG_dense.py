from pathlib import Path

from src.agent import RAG_dense as rag_dense


class FakeEmbedder:
    def embed(self, texts):
        import numpy as np
        return np.asarray(
            [[len(t), sum(c in "aeiou" for c in t.lower())] for t in texts],
            dtype=float,
        )

def test_collect_snippets(tmp_path: Path):
    # create fake split saves
    gdir = tmp_path / "games" / "demo"
    gdir.mkdir(parents=True)
    (gdir / "world.json").write_text('{"world_summary":"Sky docks","lore":"Ancient"}', encoding="utf-8")
    (gdir / "npcs.json").write_text('{"npc1":{"name":"Aerin","location":"Dock","description":"Sky trader"}}', encoding="utf-8")
    snippets = rag_dense.collect_snippets("demo", root=tmp_path / "games")
    ids = {sid for sid, _ in snippets}
    assert "world:summary" in ids and "npc:Aerin" in ids

def test_index_search(tmp_path: Path, monkeypatch):
    gdir = tmp_path / "games" / "demo"
    gdir.mkdir(parents=True)
    (gdir / "world.json").write_text('{"world_summary":"Sky docks"}', encoding="utf-8")
    monkeypatch.setattr(rag_dense, "_ensure_model_download", lambda: True)
    embedder = FakeEmbedder()
    rag_dense.build_idx("demo", embedder, saves_root=tmp_path / "games")
    hits = rag_dense.search("demo", "dock", embedder, top_k=3, saves_root=tmp_path / "games")
    assert hits
