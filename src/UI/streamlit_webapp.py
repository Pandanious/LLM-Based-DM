import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import streamlit as st

from src.UI.game_state import get_games, reset_game
from src.UI.sidebar import render_sidebar
from src.UI.actions import handle_world_creation, handle_gameplay_input
from src.UI.initiative import render_initiative_controls
from src.UI.chat_log import render_chat_log
from src.agent.types import Message

from src.agent.party_summary import build_party_summary
from src.game.party_store import save_party_summary


# ---------------------------------------
# UI SETTINGS & CSS
# ---------------------------------------

st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")

hide_css = """
<style>
[data-testid="stSidebarNav"] { display: none; }
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)


# ---------------------------------------
# TITLE
# ---------------------------------------

st.title("Local Dungeon Master")


# ---------------------------------------
# INIT GAME STATE + SIDEBAR
# ---------------------------------------

games = get_games()
game, game_id, players_raw, startbutton, initiative_sidebar = render_sidebar(games)

# Parse local player names
player_names = [p.strip() for p in players_raw.split(",") if p.strip()]
st.session_state.player_names = player_names

# Reset game if requested
if startbutton:
    reset_game(game)

# ---------------------------------------
# INPUT HANDLING
# ---------------------------------------

world_exists = game.world is not None
pcs_exist = bool(game.player_characters)

if not world_exists:
    chat_prompt = "Describe the world to begin."
elif world_exists and not pcs_exist:
    chat_prompt = "World created. Make characters first."
else:
    chat_prompt = "Play your turn. Use /action for mechanics."

user_input = st.chat_input(chat_prompt)


# World creation
if user_input and not world_exists:
    handle_world_creation(user_input, game_id, game)
    world_exists = True

# Gameplay input
if user_input and world_exists and pcs_exist:
    speaker = (
        st.session_state.player_names[0]
        if st.session_state.player_names
        else "Player"
    )
    handle_gameplay_input(user_input, game, speaker)


# ---------------------------------------
# PARTY SUMMARY (add once)
# ---------------------------------------

world_exists = game.world is not None
pcs_exist = bool(game.player_characters)

if world_exists and pcs_exist:
    has_summary = any(
        m.role == "system" and "PARTY SUMMARY" in m.content
        for m in game.messages
    )

    if not has_summary:
        summary_text = build_party_summary(game.player_characters)
        if summary_text:
            game.messages.append(
                Message(role="system", content=summary_text)
            )
            if game.world is not None:
                save_party_summary(game.world.world_id, summary_text)


# ---------------------------------------
# INITIATIVE (SIDEBAR CONTAINER)
# ---------------------------------------

with initiative_sidebar:
    render_initiative_controls(game)


# ---------------------------------------
# MAIN GAME LOG
# ---------------------------------------

render_chat_log(game)
