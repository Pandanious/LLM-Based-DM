# Local RPG Dungeon Master

Local-first Streamlit toolkit for running a tabletop-style RPG session powered by a GGUF model through `llama-cpp-python`. The app handles worldbuilding, NPCs, character sheets, and a DM chat loop without calling any external APIs.

## Features
- Worldbuilding: `src/agent/world_build.py` expands a one-line setting into a titled world summary, lore, locations, skills, and themes, then saves it to `saves/<game_id>.json`.
- Character Manager: `src/UI/pages/char_manager.py` plus `src/agent/char_gen.py` turn player prompts into level 1 sheets (stats, skills, inventory) stored per world in `saves/<game_id>_players.json`.
- NPC Roster: `src/agent/npc_gen.py` auto-creates 6-10 NPCs tied to locations and saves them under `saves/npcs/`.
- Shared table state: `src/game/game_state.py` keeps chat history, PCs, NPCs, and world data keyed by a Game ID so multiple browser tabs share the same table.
- DM persona and dice protocol: `src/agent/persona.py` forces the model to request rolls via `[ROLL_REQUEST: 1d20+3 | reason]`; helpers in `src/game/dice.py` and `src/game/md_dice_handler.py` parse and roll.
- Multi-page UI: main chat at `src/UI/streamlit_webapp.py`, read-only world view at `src/UI/pages/world_info.py`, and character builder at `src/UI/pages/char_manager.py`.

## Setup
1. Python 3.10+ recommended.
2. Place a GGUF model in `model/` and set `model_path` (plus `cpu_threads`, `gpu_layers`) in `src/config.py`.
3. Install deps (ideally in `.venv`): `pip install -r requirements.txt`.

## Run
1. From repo root: `streamlit run src/UI/streamlit_webapp.py`.
2. In the sidebar, pick a Game ID (shared across tabs) and enter local player names.
3. First chat input describes the desired setting; the app forges the world, saves it, and loads generated NPCs.
4. Open **Character Manager** (sidebar button) to create PCs for each local player, then return to the main page to play.
5. Open **World Information** to view the generated lore, locations, and NPCs.
6. Use **Start/Reset Game** to clear world/chat for the current Game ID or **Reset the LLM Model** if you change model config.

## Data locations
- Worlds: `saves/<game_id>.json`
- Player characters: `saves/<game_id>_players.json`
- NPCs: `saves/npcs/<game_id>_npcs.json`

## Notes
- `src/agent/quest_gen.py` is a stub; quests are not yet generated.
- DLL search paths for llama-cpp are pre-set in `src/llm_client.py` (Windows-friendly). Adjust if your CUDA/ggml layout differs.
