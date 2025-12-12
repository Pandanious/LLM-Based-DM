import json
from pathlib import Path

from src.agent.RAG import build_corpus, search_snippets, format_context_blocks

def test_build_collect_snippets(tmp_path: Path):
    bundle = {
        "world": {"world_summary": "Sky world", "lore": "Ancient sky docks."},
        "npcs": {
            "npc1": {"name": "Aerin", "description": "Sky trader", "location": "Docks"}
        },
        "quests": {"q1": {"title": "Find Helm", "status": "available", "description": "Helm in the vault"}},
        "turn_log": {"entries": [{"content": "Met the trader at the dock."}]},
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")

    snippets = build_corpus(tmp_path)
    text = {text for _, text in snippets}

    assert "Sky world" in text
    assert "Ancient sky docks." in text
    assert any("Aerin" in t and "Docks" in t for t in text)
    assert any("Find Helm" in t for t in text)

def test_search_returns_scored(tmp_path: Path):
    bundle = {"world": {"world_summary": "Sky traders at the docks"}}
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    snippets = build_corpus(tmp_path)
    hits = search_snippets("sky docks trader", snippets, top_k=3)

    assert hits
    assert hits[0][2] > 0
    assert "Sky traders" in hits[0][1]


def test_search_snippet_matches(tmp_path: Path):
    bundle = {"world": {"world_summary": "Sky traders at the docks"}}
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    snippets = build_corpus(tmp_path)

    hits = search_snippets("volcano", snippets, top_k=3)
    assert hits == []

def test_format_block_number_hits():
    hits = [
        ("id1", "First snippet", 2.0),
        ("id2", "Second snippet", 1.0),
    ]
    ctx = format_context_blocks(hits)
    assert "[CONTEXT 1]" in ctx and "First snippet" in ctx
    assert "[CONTEXT 2]" in ctx and "Second snippet" in ctx


def test_build_corpus_bad_json(tmp_path: Path):
    # What if the json is messed up ?
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
    good = {
        "world": {"world_summary": "Valid world"},
        "quests": {"q1": {"title": "Quest", "status": "available", "giver_name": "Bob", "description": "Do thing"}},
    }
    (tmp_path / "good.json").write_text(json.dumps(good), encoding="utf-8")

    snippets = build_corpus(tmp_path)
    texts = {t for _, t in snippets}
    assert any("Valid world" in t for t in texts)
    assert any("Quest" in t and "Bob" in t for t in texts)


def test_turn_notes_indexed(tmp_path: Path):
    bundle = {
        "turn_log": {"entries": [{"content": "Found secret door in the cellar."}]},
    }
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")

    snippets = build_corpus(tmp_path)
    assert any("secret door" in text for _, text in snippets)


def test_context_blocks_include_top_hit(tmp_path: Path):
    bundle = {
        "world": {"world_summary": "Sky traders at the docks"},
        "npcs": {"npc1": {"name": "Aerin", "description": "sells sky maps", "location": "Dockside"}},
    }
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")

    snippets = build_corpus(tmp_path)
    hits = search_snippets("sky maps dock", snippets, top_k=2)
    ctx = format_context_blocks(hits)

    assert "[CONTEXT 1]" in ctx
    assert "sky maps" in ctx or "Sky traders" in ctx



