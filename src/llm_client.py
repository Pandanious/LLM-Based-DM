import os
from functools import lru_cache
from typing import List

# Ensure CUDA/ggml DLLs are discoverable when llama_cpp loads.
_dll_dirs = (
    r"H:\CUDA\bin",
    r"H:\Python\Agentic-Tutorial\.venv\lib\site-packages\llama_cpp\lib",
)
for _dll_dir in _dll_dirs:
    if os.path.isdir(_dll_dir):
        try:
            os.add_dll_directory(_dll_dir)  # preferred on Windows 3.8+
        except (AttributeError, FileNotFoundError):
            pass
        # Also extend PATH as a fallback for loaders that ignore add_dll_directory.
        if _dll_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{_dll_dir};{os.environ.get('PATH', '')}"

from llama_cpp import Llama
from src.agent.types import Message

from src.config import (
    cpu_threads,
    default_max_tokens,
    default_temp,
    gpu_layers,
    max_CTX,
    model_path,
)


@lru_cache(maxsize=1)
def get_llm() -> Llama:
    """Load and cache the Llama model."""
    return Llama(
        model_path=str(model_path),
        n_ctx=max_CTX,
        n_threads=cpu_threads,
        n_gpu_layers=gpu_layers,
        verbose=True,  # set to True for terminal logs, False if too noisy
    )


def format_prompt(messages: List[Message]) -> str:
    # how to instruct the model.. {role:user:content}

    parts = []
    for msg in messages:
        if msg.role == "system":
            parts.append(f"[SYSTEM]\n{msg.content}\n")
        elif msg.role == "assistant":
            parts.append(f"[ASSISTANT]\n{msg.content}\n")  # model responds as ASSISTANT
        else:  # This is content
            speaker = msg.speaker or "Player"
            parts.append(f"[PLAYER {speaker}]\n{msg.content}\n")

    parts.append("[ASSISTANT]\n")  # Model Responds as ASSISTANT
    return "\n".join(parts)


def chat_completion(
    messages: List[Message],
    temperature: float = default_temp,
    max_tokens: int = default_max_tokens,
    prefix: str = "",
) -> str:

    llm = get_llm()

    # Trim prompt to fit within context window budget.
    prompt_budget_chars = max_CTX * 3  # rough heuristic: ~3 chars per token
    trimmed_messages = _trim_messages(messages, max_chars=prompt_budget_chars)

    prompt_body = format_prompt(trimmed_messages)
    prompt = f"{prefix}\n{prompt_body}" if prefix else prompt_body
    # Debug: show the prompt in the console
    print("\n=== LLM PROMPT START ===\n")
    print(prompt)
    print("\n=== LLM PROMPT END ===\n")
    result = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
        # Stop the model as soon as it tries to start a new turn or switch speaker
        stop=["[PLAYER", "[ASSISTANT", "[SYSTEM", "[ITEM", "</s>"],
    )

    choices = result.get("choices", [])
    if not choices:
        return "[DM is silent: no output from model]"
    reply = result["choices"][0].get("text", "")
    return reply.strip()


def reset_model():
    get_llm.cache_clear()


def _trim_messages(messages: List[Message], max_chars: int) -> List[Message]:
    #keep most recent+more inputs
    
    if len(messages) <= 1:
        return messages

    system_msgs = [m for m in messages if m.role == "system"]
    keep_system = system_msgs[:1]  # keep the first system prompt

    # Take recent non-system messages from the end until we exceed budget
    recent: List[Message] = []
    total = sum(len(m.content or "") for m in keep_system) + 50 * len(keep_system)

    for msg in reversed(messages):
        if msg in keep_system:
            continue
        approx_len = len(msg.content or "") + 50  # header/prefix fudge factor
        if total + approx_len > max_chars and recent:
            break
        recent.append(msg)
        total += approx_len

    recent.reverse()
    return keep_system + recent
