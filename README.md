# Local RPG Dungeon Master

A local-first Streamlit app that runs a tabletop-style RPG session with your own GGUF LLM (llama-cpp). It forges worlds, NPCs, quests, and handles dice-backed DM turns without any cloud calls.

## What it does
- World forge: turn a single prompt into a titled world (summary, lore, locations, themes, skills) and save it by Game ID.
- NPCs & quests: generate location-tied NPCs plus quests with text + item rewards; merchants auto-stock items you can refresh.
- Character Manager: per-player sheets with stats/skills/inventory, saved per Game ID and viewable across tabs.
- Play loop: chat with the DM; `/action ...` triggers roll requests, the app rolls with PC stats and logs results.
- Initiative & turns: build order, step through turns, and export action recaps.
- Saves: load/save worlds, PCs, NPCs, quests, party summary, and bundle snapshots locally.
- Retrieval: DM turns pull top snippets from your saved world/NPC/quest data and prepend them as `[CONTEXT]` blocks to stay grounded.
- Summaries: long chats auto-collapse older turns into a concise `[SUMMARY]` system note to keep within context budget.

## Why it’s interesting 
- Fully local: privacy-safe, no external APIs.
- Structured prompts + parsing: consistent world/quest/NPC generation with guards for missing data.
- Stateful multiplayer via Game ID: tabs share the same state, with reset and reload controls.
- Extensible: item generation feeds quests and merchants; inventories show up in UI expanders.

## Run it
1) `pip install -r requirements.txt` (use a venv).
2) Drop a GGUF model into `model/` and set `model_path` (and optional `cpu_threads`, `gpu_layers`) in `src/config.py`.
3) `streamlit run src/UI/streamlit_webapp.py`
4) In the sidebar: pick a Game ID, add player names, click **Reset Game** if needed, then describe your world to begin.

## Quick demo path
- Generate a world with a short setting description.
- Open **Character Manager** to create PCs for each local player.
- Back on the main page, click **Refresh Party Summary**, click **Build Initiative** if there are more than one player, type `start`, then chat. Use `/action ...` for mechanics.
- Check **Quest Log** for quests and item rewards; **NPC Overview** shows merchants with refreshable stock.

## Tech stack
- Python, Streamlit, llama-cpp-python
- Data: JSON saves under `saves/` (worlds, PCs, NPCs, quests, bundles, turn logs)
- Retrieval layer: keyword search over saved JSON to feed `[CONTEXT]` into the DM prompt; history summarization to trim chat length.

## Key files
- `src/UI/streamlit_webapp.py` – main app shell
- `src/agent/world_build.py`, `npc_gen.py`, `quest_gen.py` – generation prompts/parsers
- `src/agent/char_gen.py`, `item_gen.py` – character and item generation
- `src/UI/pages/char_manager.py`, `quest_log.py`, `npc_log.py` – UI pages
