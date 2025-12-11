import pytest

from src.agent.world_build import generate_world_state, _parse_world_output
from src.llm_client import format_prompt, _trim_messages
from src.agent.types import Message


class FakeLLM:
    def __init__(self, text: str):
        self.text = text
        self.last_prompt = None
        self.last_kwargs = None

    def __call__(self, prompt: str, **kwargs):
        self.last_prompt = prompt
        self.last_kwargs = kwargs
        return {"choices": [{"text": self.text}]}


def test_generate_world_state_parses_model_output(monkeypatch):
    fake_output = """TITLE: Skyforge
                     WORLD SUMMARY:
                     Floating isles and sky docks.
                     LORE:
                     Ancient engines hold the islands aloft.
                     MAJOR LOCATIONS (1):
                     1. Nimbus Port - hub of airships and sky markets.
                     MINOR LOCATIONS (2):
                     1. Driftway - abandoned airship graveyard.
                     2. Cloudspire - lightning-wreathed tower.
                     WORLD SKILLS:
                     - Soar
                     - Tinker
                     THEMES & TONE:
                     - hopeful
                     - perilous
"""
    fake_llm = FakeLLM(fake_output)
    monkeypatch.setattr("src.agent.world_build.get_llm", lambda: fake_llm)

    world = generate_world_state("sky islands", players=["Alice"], world_id="g1")


    assert world.title.startswith("Floating isles")
    assert world.players == ["Alice"]
    assert world.major_locations and world.major_locations[0]["name"] == "Nimbus Port"
    assert "Soar" in world.skills
    assert "hopeful" in world.themes


def test_parse_world_output_fallbacks():
    title, summary, lore, skills, major, minor, themes = _parse_world_output(
        "WORLD SUMMARY:\nClockwork world.", fallback_setting="gears and brass"
    )
    assert title  # inferred from summary
    assert summary.startswith("Clockwork world.")
    assert major == [] and minor == []
    assert skills == [] and themes == []


def test_format_prompt_and_trim():
    messages = [
        Message(role="system", content="Be concise."),
        Message(role="user", content="Hello", speaker="Alice"),
        Message(role="assistant", content="Hi there."),
    ]
    prompt = format_prompt(messages)
    assert "[SYSTEM]\nBe concise." in prompt
    assert "[PLAYER Alice]\nHello" in prompt
    assert prompt.strip().endswith("[ASSISTANT]")

    trimmed = _trim_messages(messages, max_chars=120)
    assert trimmed[0].role == "system"
    assert trimmed[-1].content == "Hello" or trimmed[-1].content == "Hi there."
