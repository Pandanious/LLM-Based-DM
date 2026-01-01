from pathlib import Path
from src.agent.RAG import collect_snippets, LocalVectorStore, Embedder, build_index, search

def test_collect_snippets(tmp_path: Path):
    # create fake split saves
    gdir = tmp_path / "games" / "demo"
    gdir.mkdir(parents=True)
    (gdir / "world.json").write_text('{"world_summary":"Sky docks","lore":"Ancient"}', encoding="utf-8")
    (gdir / "npcs.json").write_text('{"npc1":{"name":"Aerin","location":"Dock","description":"Sky trader"}}', encoding="utf-8")
    snippets = collect_snippets("demo", root=tmp_path / "games")
    ids = {sid for sid, _ in snippets}
    assert "world:summary" in ids and "npc:Aerin" in ids

def test_index_search(tmp_path: Path):
    gdir = tmp_path / "games" / "demo"
    gdir.mkdir(parents=True)
    (gdir / "world.json").write_text('{"world_summary":"Sky docks"}', encoding="utf-8")
    embedder = Embedder(model_name="all-MiniLM-L6-v2") 
    store = build_index("demo", embedder, saves_root=tmp_path / "games")
    hits = search("demo", "dock", embedder, top_k=3, saves_root=tmp_path / "games")
    assert hits
