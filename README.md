# Local RPG Dungeon Master

Local-first tabletop RPG assistant: Streamlit UI + on-device GGUF LLM (llama-cpp). Builds worlds, NPCs, quests, items, and runs turn-based sessions with dice-backed actions - no cloud calls or data leaves your machine.

![CI](https://github.com/Pandanious/LLM-Based-DM/actions/workflows/ci.yaml/badge.svg)

## Highlights
- World forge: name + lore + locations + themes + skills from a single prompt, saved by Game ID.
- NPCs, quests, merchants: location-tied NPCs, quests with rewards, merchants with refreshable stock.
- Play loop: chat with the DM; `/action ...` triggers rolls with PC stats; logs outcomes.
- Initiative + turns: build order, step through turns, and export recaps.
- Saves + retrieval: worlds/PCs/NPCs/quests/turn logs stored under `saves/`; DM responses prepend `[CONTEXT]` snippets from your data to stay grounded.
- Summaries: long chats auto-collapse into `[SUMMARY]` notes to stay within context budget.

## Quickstart
1) Install Python 3.10+ and create a virtualenv.
2) `pip install -r requirements.txt`
3) Place a GGUF model in `model/` and set `model_path` (plus `cpu_threads`, `gpu_layers` if desired) in `src/config.py`.
4) Run: `streamlit run src/UI/streamlit_webapp.py` (or use `run_app.bat` on Windows).
5) In the sidebar: choose a Game ID, add player names, click **Reset Game** if needed, then describe your world to begin.

## Demo path
- Generate a world with a short setting description.
- Open **Character Manager** to create PCs for each player.
- Back on the main page: **Refresh Party Summary**, **Build Initiative** (if multiple players), type `start`, then chat. Use `/action ...` for mechanics.
- Check **Quest Log** for quests and item rewards; **NPC Overview** shows merchants with refreshable stock.

## Configuration
- Model path: `src/config.py::model_path` (defaults to `model/Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf` - swap in your own GGUF).
- Performance knobs: `cpu_threads`, `gpu_layers`, `default_temp`, `default_max_tokens`.
- Saves directory: `saves/` (auto-created).

## Tech stack
- Python, Streamlit, llama-cpp-python.
- Data: JSON saves under `saves/` for worlds, PCs, NPCs, quests, bundles, turn logs.
- Retrieval: keyword search over saved JSON to feed `[CONTEXT]` into DM prompt; history summarization trims chat length.

## Repository map
- `src/UI/streamlit_webapp.py` - main app shell.
- `src/UI/pages/` - pages for character manager, quest log, NPC log, world info.
- `src/agent/world_build.py`, `npc_gen.py`, `quest_gen.py` - generation prompts/parsers.
- `src/agent/char_gen.py`, `item_gen.py` - character and item generation.
- `src/game/` - game state, models, dice, save/load.
- `run_app.bat` - convenience launcher for Streamlit + ngrok.

## Troubleshooting
- Model not found: ensure your GGUF file exists and `model_path` points to it.
- GPU layers: set `gpu_layers=0` to stay CPU-only if you hit GPU issues.
- Port conflicts: change the Streamlit port via `streamlit run ... --server.port 8502`.
- Slow responses: lower `default_max_tokens` or increase `cpu_threads` within your hardware limits.

## Tests
- Tests can be run locally with -m pytest src/test (or run src/tests/run_test.bat (windows))
- Github Actions runs the same tests on push/pull request. (see badge above)

## Privacy
Everything runs locally: no external API calls or data uploads. Your worlds, characters, and logs stay on your device.
