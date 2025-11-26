import sys
from pathlib import Path

import streamlit as st

# Make src importable when Streamlit runs this page directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.game.game_state import get_global_games


def get_game_and_world():
    query_params = st.query_params
    game_id = query_params.get("game_id", "default")

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        return None, None, game_id

    return game, game.world, game_id


st.set_page_config(page_title="How to Play / Local DM", layout="wide")
st.title("How to Play / Help")

game, world, game_id = get_game_and_world()
st.markdown(f"**Game ID:** `{game_id}`")

if world:
    st.markdown(f"**Current World:** **{world.title}**")
    st.markdown(world.world_summary)
else:
    st.info("No active world detected for this Game ID yet. You can still read the instructions below.")

st.markdown("---")

# -------------------------
# Quick start
# -------------------------

st.header("1) Quick Start")
st.markdown(
    """
1. In the main app sidebar, enter a **Game ID** (everyone who uses the same ID shares the table) and click **Reset Game** if you want a clean slate.
2. In the chat box, describe the **setting** you want. The app forges a titled world, lore, locations, NPC roster, and saves it under `saves/<game_id>.json`.
3. Open **Character Manager** to create a sheet for each local player (name, ancestry, concept). Sheets are saved to `saves/<game_id>_players.json`.
4. Return to the main page, click **Refresh Party Summary** if needed, then play by chatting in-character and using `/action ...` when you want mechanics.
"""
)

st.markdown("---")

# -------------------------
# Pages and controls
# -------------------------

st.header("2) Pages and Controls")
st.markdown(
    """
- **Main page (Game Log):** chat with the DM, see history, and manage the table from the sidebar.
- **Sidebar controls:** set **Game ID**, **Reset Game** (clears world/chat/PCs for that ID), and **Reset the LLM Model** if you change model config.
- **World Information:** read-only world summary, lore, locations, and NPCs.
- **Character Manager:** generate or re-roll player characters tied to this Game ID.
- **Quest Log:** read-only list of generated quests and their status.
- **NPC Overview:** grouped list of NPCs by location.
- **Initiative Order controls:** build the turn order from PC initiatives and advance to the next turn.
- **This Help:** opens in a new tab from the sidebar button.
"""
)

st.markdown("---")

# -------------------------
# World building
# -------------------------

st.header("3) Building the World")
st.markdown(
    """
- The very first chat message you send (when no world exists) should describe the desired setting, tone, or themes.
- The app creates:
  - a world title and summary,
  - lore plus major/minor locations,
  - an NPC roster placed at locations,
  - a starter set of quests tied to those NPCs and places.
- All of this is shared across tabs that use the same **Game ID**.
"""
)

st.markdown("---")

# -------------------------
# Characters and party summary
# -------------------------

st.header("4) Characters and Party Summary")
st.markdown(
    """
- Use **Character Manager** for each player name you enter (local to your browser) to generate a sheet.
- Sheets include stats, skills, inventory, and are saved per world so they reload automatically.
- Back on the main page, **Refresh Party Summary** pulls characters from disk and injects a `PARTY SUMMARY` system message so the DM respects existing PCs.
- If the DM seems to forget your PC, refresh the summary and continue; do not recreate the character manually.
"""
)

st.markdown("---")

# -------------------------
# Playing in chat
# -------------------------

st.header("5) Playing in Chat")
st.markdown(
    """
- Normal messages are treated as in-character narration or dialogue.
- Saying `start` or `let's begin` after PCs exist prompts the DM to introduce the party from the current summary.
- Keep using the same **Game ID** to resume a table later; the world, PCs, NPCs, and quests load automatically.
"""
)

st.markdown("---")

# -------------------------
# Initiative / turn order
# -------------------------

st.header("6) Initiative and Turn Order")
st.markdown(
    """
- PCs have an `initiative` value on their sheet.
- In the main page right column, use **Build Initiative Order** to sort PCs by initiative and set the first turn.
- Use **Next Turn** to advance to the next PC in the order; the current actor is shown above the Game Log.
- No auto re-roll is provided; update initiatives on the sheets if you need to change them, then rebuild the order.
"""
)

st.markdown("---")

# -------------------------
# Dice, actions, and rolls
# -------------------------

st.header("7) Dice, Actions, and Rolls")
st.markdown(
    """
- Use `/action <what you attempt>` when you want mechanics:
  - `/action I try to sneak past the guard`
  - `/action I pick the lock on the chest`
  - `/action I strike the bandit with my axe`
- The DM will reply with a line like `[ROLL_REQUEST: 1d20+2 | stealth_check: sneaking past the guard]`.
- The game system (not the DM) rolls using your stats/skills and difficulty cues, then posts `[ROLL_RESULT: ... outcome=success|failure ...]`.
- The DM then narrates the outcome based on that result. You do not need to roll manually.
- Standard action types the system expects:
  - `attack`, `stealth_check`, `perception_check`, `lockpick`, `persuasion`, `athletics`, `acrobatics`, `damage_light`, `damage_heavy`.
"""
)

st.markdown("---")

# -------------------------
# Quests
# -------------------------

st.header("8) Quests")
st.markdown(
    """
- Quests are generated alongside the world and saved to `saves/<game_id>_quests.json`.
- In chat you can manage status without bothering the DM:
  - `/quest list` - show all quests for this world.
  - `/quest start <title fragment>` - mark one in progress.
  - `/quest complete <title fragment>` - mark finished.
  - `/quest fail <title fragment>` - mark failed.
- The **Quest Log** page shows all quests, their steps, rewards, and current status.
"""
)

st.markdown("---")

# -------------------------
# NPCs and world reference
# -------------------------

st.header("9) World Reference")
st.markdown(
    """
- **World Information** shows the generated lore, themes, and major/minor locations.
- **NPC Overview** lists NPCs by location with roles, tags, and hooks when available.
- These pages are read-only; they follow the same **Game ID** in the query string.
"""
)

st.markdown("---")

# -------------------------
# Tips and fixes
# -------------------------

st.header("10) Tips and Fixes")
st.markdown(
    """
- If rolls are missing stats, refresh the party summary so the system links the acting player to a PC sheet.
- If nothing responds, confirm you are using the correct **Game ID** in every tab.
- Use **Reset Game** only when you truly want to wipe world/chat/PCs for that ID.
- You can leave out-of-character notes with plain text; only `/action` and `/quest ...` have special handling right now.
"""
)
