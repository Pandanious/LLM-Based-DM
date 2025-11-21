## Local RPG Dungeon Master

This project is a lightweight Streamlit application that lets you run an entirely local tabletop-style RPG session powered by a GGUF model loaded through `llama-cpp-python`. The flow is intentionally split into two phases:

1. **World-building warmup** – The Dungeon Master first prompts the player to describe the kind of setting they want. That text is sent to `generate_world_state`, which calls the local LLM to produce a campaign title, summary, and lore. The resulting `World_State` dataclass is saved to disk so it can be reused later.
2. **Interactive play** – Once a world exists, the conversation becomes a standard DM ↔ players exchange. The sidebar lets you edit the list of player names, restart the world-generation flow, or hot-reload the underlying model.

### Key files

- `src/UI/streamlit_webapp.py` – Streamlit UI and session-state orchestration.
- `src/agent/world_build.py` – Prompts the LLM for campaign data and sanitizes the response.
- `src/game/models.py` – Dataclasses for storing world metadata plus JSON serialization helpers.
- `src/game/save_state.py` – Read/write helpers for persisting `World_State` objects under `saves/`.
- `src/llm_client.py` – Thin wrapper around `llama_cpp.Llama`, including a cached loader and prompt formatter.

### Running locally

1. Ensure Python 3.10+ and a GGUF model file placed at `model/model.gguf`. Adjust `src/config.py` if your path or llama settings differ.
2. Install dependencies: `pip install -r requirements.txt` (ideally inside the provided `.venv`).
3. Launch the UI: `streamlit run src/UI/streamlit_webapp.py`.

The first chat input will always be treated as the setting description. After the world is built, use the chat box to act as the players and the select box to choose which character is speaking. Use the sidebar buttons to reset the session, regenerate a world from custom text, or reload the model if you tweak config values.
