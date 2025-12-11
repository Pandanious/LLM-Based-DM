import pytest, os

from src.agent.dm_dice import _maybe_summarize_history, _summarize_history
from src.agent.types import Message


def test_maybe_summarize_history(monkeypatch):
    calls = []

    def fake_chat(messages, temperature=0.3, max_tokens=260, prefix=""):
        calls.append(messages)
        return "condensed notes"

    monkeypatch.setattr("src.agent.dm_dice.chat_completion", fake_chat)

    messages = [
        Message(role="system", content="World lore"),
        Message(role="user", content="Turn 1", speaker="Alice"),
        Message(role="user", content="Turn 2", speaker="Bob"),
        Message(role="user", content="Turn 3", speaker="Alice"),
    ]

    result = _maybe_summarize_history(messages, limit=3, keep_recent=1)

    assert calls, "chat_completion should be invoked for summarization"
    assert result[0].role == "system"
    assert result[1].role == "system"
    assert result[1].content.startswith("[SUMMARY]\ncondensed notes")
    assert result[-1].content == "Turn 3"
    assert len(result) == 3


def test_summarize_history_no_change():
    messages = [
        Message(role="system", content="World lore"),
        Message(role="user", content="Turn 1"),
    ]
    result = _maybe_summarize_history(messages, limit=5, keep_recent=2)
    assert result is messages
    assert len(result) == 2


def test_summarize_history_on_empty(monkeypatch):
    monkeypatch.setattr("src.agent.dm_dice.chat_completion", lambda *args, **kwargs: "")
    summary = _summarize_history([Message(role="user", content="Turn 1")])
    assert summary is None

@pytest.mark.skipif(not os.getenv("RUN_LLM_TESTS"), reason="LLM not enabled")
def test_summarize_with_model():
    summary = _summarize_history([Message(role="user",content="Turn 1")])
    assert summary