import os
from functools import lru_cache
from typing import Dict, List

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
        verbose=False,
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
    max_tokens: int = default_max_tokens):

    llm = get_llm()
    prompt = format_prompt(messages)
    result = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
        #stop=["[PLAYER", "[ASSISTANT", "[DM]", "</s>"]
        )

    choices = result.get("choices", [])
    if not choices:
# do something other than crashing
        return '[DM is silent – no output from model]'    
    reply = result["choices"][0].get("text","")
    return reply.strip()

def reset_model():
    get_llm.cache_clear()
    
 

