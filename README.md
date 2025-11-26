<!-- NOT YET FINAL-
     README-IS-AI-GEN-BASED-ON-REPO-NEEDS-REFINEMENT -->


# Local RPG Dungeon Master

Local-first Streamlit toolkit for running a tabletop-style RPG session powered by a local GGUF model through `llama-cpp-python`. Everything (worldbuilding, NPCs, quests, dice, sheets) runs on your machine; no external API calls.

## What it does
- World forge: first chat message creates a titled world with summary, lore, skills, themes, major/minor locations, and saves it under the chosen Game ID.
- Roster building: generates an NPC list tied to locations plus a set of quests linked to those NPCs and places.
- Character Manager: per-player character sheets with stats/skills/inventory, saved per world and re-loadable across browser tabs.
- DM persona with server-side dice: `/action ...` prompts the DM to issue `[ROLL_REQUEST: ...]`; the app rolls with PC stats/difficulty heuristics, posts `[ROLL_RESULT ...]`, and has   the DM narrate outcomes.
- Initiative + turn log: build turn order from PC initiatives, step through turns, and record actions with an exportable recap.
- Save/load & summaries: refreshable party summary system message, bundle save/load for full state, and resettable LLM cache.
- Multi-page UI: main chat plus World Info, Character Manager, Quest Log, NPC Overview, and Help pages that follow the current `game_id`.

## Setup
1. Python 3.10+ recommended.
2. Place a GGUF model in `model/` and set `model_path`, `cpu_threads`, and `gpu_layers` in `src/config.py`.
3. Install deps (ideally in a virtualenv): `pip install -r requirements.txt`.
4. Optional: on Windows, `run_app.bat` launches Streamlit and an ngrok tunnel secured by `src/UI/policy.yaml` (basic auth).

## Run
1. From repo root: `streamlit run src/UI/streamlit_webapp.py` (or `run_app.bat` on Windows).
2. In the sidebar, pick a **Game ID** (shared across tabs) and enter local player names. Use **Reset Game** if you want a clean slate for that ID.
3. First chat input describes the setting; the app forges the world, NPC roster, and quests and saves them.
4. Open **Character Manager** (sidebar button) to create/re-roll PCs for each local player; sheets auto-save per Game ID.
5. Back on the main page, use **Refresh Party Summary** if PCs were added elsewhere, then play by chatting and using `/action ...` when you want mechanics.
6. Use **World Info**, **Quest Log**, and **NPC Overview** pages for read-only reference; **Help** opens the in-app guide.

## Gameplay notes
- `/action <what you attempt>` triggers DM `[ROLL_REQUEST: ...]` lines. Supported action types: `attack`, `stealth_check`, `perception_check`, `lockpick`, `persuasion`, `athletics`, `acrobatics`, `damage_light`, `damage_heavy`. The app rolls using PC stats/skills and difficulty hints, then posts `[ROLL_RESULT ... outcome=success|failure ...]` before the DM narrates.
- Quest commands in chat: `/quest list`, `/quest start <title fragment>`, `/quest complete <title fragment>`, `/quest fail <title fragment>`.
- Initiative controls on the main page build turn order from PC initiatives; **Next Turn** advances and records a turn entry. The **Export action recap** button saves a JSON + text summary under `saves/snapshots/`.
- Bundle saves: **Save world state** writes a one-file bundle of world/PCs/NPCs/quests/initiative; **Load world state** restores it and rebuilds DM/system prompts.
- **Reset the LLM Model** clears the cached llama-cpp instance if you change model files or settings.

## Data locations
- Worlds: `saves/<game_id>.json`
- Player characters: `saves/<game_id>_players.json`
- NPCs: `saves/npcs/<game_id>_npcs.json`
- Quests: `saves/<game_id>_quests.json`
- Party summary: `saves/<game_id>_party_summary.txt`
- Turn log: `saves/turns/<game_id>_turns.json`
- Action recap exports: `saves/snapshots/<game_id>_actions/`
- Bundle saves: `saves/bundles/<timestamp>_<players>.json`

