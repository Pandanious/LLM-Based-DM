import sys
import time
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
from src.game.turn_store import build_action_summary, export_turn_log_snapshot


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
    started = any(
        m.role == "user"
        and m.content.strip().lower() in {"start", "begin", "let's begin", "lets begin", "i am ready"}
        for m in game.messages
    )
    if not started:
        chat_prompt = "Lets begin our adventure. Type <Start> to begin."
    else:
        chat_prompt = (
            "Input your choice here. You can use /action for mechanics; format actions like {/action I shoot} etc."
        )

user_input = st.chat_input(chat_prompt)
speaker_label = st.session_state.get("current_speaker")
default_speaker = (
    st.session_state.player_names[0]
    if st.session_state.player_names
    else "Player"
)
speaker = speaker_label or default_speaker

# Shared busy indicator so all sessions know someone is using the model
if getattr(game, "busy", False):
    st.warning(
        f"Model busy: {game.busy_task or 'In progress'} "
        f"(started by {game.busy_by or 'another player'})."
    )
    time.sleep(0.8)
    st.rerun()


# World creation
if user_input and not world_exists:
    handle_world_creation(user_input, game_id, game)
    world_exists = True

# Gameplay input
if user_input and world_exists and pcs_exist:
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
# ENCOUNTER STATUS
# ---------------------------------------

if getattr(game, "active_encounter", None):
    st.warning(
        f"Active encounter: {game.active_encounter} | "
        f"{getattr(game, 'active_encounter_summary', '')}"
    )


# ---------------------------------------
# ACTION RECAP EXPORT
# ---------------------------------------

if game.world is not None and hasattr(game, "turn_log") and getattr(game.turn_log, "entries", None):
    if st.button("Export action recap"):
        summary_text = build_action_summary(
            game.turn_log,
            limit=25,
            encounter_summary=getattr(game, "active_encounter_summary", None),
            encounter_history=getattr(game, "encounter_history", None),
        )
        json_path, summary_path = export_turn_log_snapshot(game.turn_log, summary_text)
        st.success(
            f"Action recap saved to `{json_path}` and `{summary_path}`"
        )


# ---------------------------------------
# MAIN GAME LOG
# ---------------------------------------

render_chat_log(game)
