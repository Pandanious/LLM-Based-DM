import sys
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitAPIException

# Page config must be set before any other Streamlit calls.
try:
    st.set_page_config(page_title="How to Play / Local DM", layout="wide")
except StreamlitAPIException:
    pass

# Make src importable when Streamlit runs this page directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.game.game_state import get_global_games

# Hide Streamlit's built-in page navigation links (use sidebar buttons instead).
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_game_and_world():
    query_params = st.query_params
    game_id = query_params.get("game_id") or st.session_state.get("game_id") or "default"

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        return None, None, game_id

    return game, game.world, game_id


st.title("How to Play / Help")

game, world, game_id = get_game_and_world()
st.markdown(f"**Game ID:** `{game_id}`")

if world:
    st.markdown(f"**Current World:** **{world.title}**")
    st.markdown(world.world_summary)
else:
    st.info("No active world yet for this Game ID. You can still read these tips.")

st.markdown("---")

st.header("Quick Start")
st.markdown(
    """
1. In the sidebar, set a **Game ID** (shared across tabs) and click **Reset Game** if you want a clean slate.
2. In the chat, describe your **setting**. The app builds the world, NPCs, quests (with item rewards), and saves them locally.
3. Open **Character Manager** to create/re-roll a sheet for each local player (saved per Game ID).
4. Back on the main page, click **Refresh Party Summary**, then type `start` to begin. Use `/action ...` when you want mechanics.
"""
)

st.markdown("---")

st.header("Pages & Controls")
st.markdown(
    """
- **Main page (Game Log):** chat with the DM, see history, manage table controls.
- **Character Manager:** generate or re-roll player characters for this Game ID.
- **Quest Log:** view quests (including item rewards) and statuses.
- **NPC Overview:** see NPCs by location; merchants show their stock and can be refreshed.
- **Initiative:** build and advance turn order.
- **Save/Load/Reset:** bundle saves, load saves, reset game state, and reset the LLM model cache if you change models.
"""
)

st.markdown("---")

st.header("Playing in Chat")
st.markdown(
    """
- Normal messages are in-character; `start` or `let's begin` prompts the DM to introduce the party.
- Use `/action <what you attempt>` for mechanics:
  - `/action I try to sneak past the guard`
  - `/action I pick the lock on the chest`
  - `/action I strike the bandit with my axe`
- The DM will reply with `[ROLL_REQUEST: ...]`; the app rolls with your stats and posts `[ROLL_RESULT: ...]` before the DM narrates.
- Standard action types: `attack`, `stealth_check`, `perception_check`, `lockpick`, `persuasion`, `athletics`, `acrobatics`, `damage_light`, `damage_heavy`.
"""
)

st.markdown("---")

st.header("World, NPCs, and Items")
st.markdown(
    """
- World creation saves lore, locations, themes, NPCs, quests, and skills under `saves/` for your Game ID.
- Quests list both text rewards and generated item rewards.
- Merchants have inventories you can refresh from the NPC Overview page; items are also added to new characters automatically.
"""
)

st.markdown("---")

st.header("Saving and Troubleshooting")
st.markdown(
    """
- **Save world state** writes a bundle JSON of world, PCs, NPCs, quests, and initiative to `saves/bundles/`.
- **Load world state** restores from a bundle and rebuilds prompts and party summary.
- If rolls seem off, refresh the party summary to sync PCs.
- If something is stuck, verify you’re using the same **Game ID** in all tabs, then try a gentle page reload.
"""
)
