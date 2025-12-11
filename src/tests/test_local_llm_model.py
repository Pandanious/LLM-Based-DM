import os
from pathlib import Path

import pytest

from src.agent.dm_dice import _summarize_history
from src.agent.types import Message
from src.config import model_path

MODEL_READY = bool(os.getenv("RUN_LLM_TESTS")) and Path(model_path).exists()


@pytest.mark.skipif(not MODEL_READY, reason="Set RUN_LLM_TESTS=1 and ensure model_path exists")
def test_summarize_history_with_model():
    pytest.importorskip("llama_cpp")
    summary = _summarize_history(
        [Message(role="user", content="Turn 1: The hero enters the tavern and meets a hooded figure.")]
    )
    assert summary


@pytest.mark.skipif(not MODEL_READY, reason="Set RUN_LLM_TESTS=1 and ensure model_path exists")
def test_generate_world_state_with_model():
    pytest.importorskip("llama_cpp")
    from src.agent.world_build import generate_world_state

    world = generate_world_state("a tiny village by a lake", players=["Tester"], world_id="smoke")
    assert world.title
    assert world.world_summary
    assert world.major_locations
    assert world.minor_locations
    assert world.skills


@pytest.mark.skipif(not MODEL_READY, reason="Set RUN_LLM_TESTS=1 and ensure model_path exists")
def test_chat_completion_smoke():
    pytest.importorskip("llama_cpp")
    from src.llm_client import chat_completion

    msgs = [Message(role="system", content="Reply briefly"), Message(role="user", content="Hello there")]
    reply = chat_completion(msgs, max_tokens=50)
    assert isinstance(reply, str)
    assert reply
