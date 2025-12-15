import types
from src.agent import dm_dice

def test_context_no_corpus(monkeypatch):
    monkeypatch.setattr(dm_dice,"_get_corpus",lambda:[])
    prefix = dm_dice._build_context_prefix([])
    assert prefix == dm_dice.NO_CONTEXT_GUARD

def test_build_context_no_hits(monkeypatch):
    monkeypatch.setattr(dm_dice,"_get_corpus",lambda:["stub"])
    monkeypatch.setattr(dm_dice,"search_snippets",lambda q, s, top_k=5: [])
    prefix = dm_dice._build_context_prefix([])
    assert prefix == dm_dice.NO_CONTEXT_GUARD

def test_build_context_with_hits(monkeypatch):
    monkeypatch.setattr(dm_dice,"_get_corpus",lambda:["stub"])
    hits = [("pc:Alice","Alice the sniper", 3.0)]
    monkeypatch.setattr(dm_dice,"search_snippets",lambda q, s, top_k=5: hits)
    prefix = dm_dice._build_context_prefix([])
    assert "[CONTEXT 1 | pc:Alice]" in prefix
    assert dm_dice.CONTEXT_GUARD.strip() in prefix