
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.game.game_state import get_global_games
from src.game.quest_store import load_quests


def get_game_and_world():
    query_params = st.query_params
    game_id = query_params.get("game_id", "default")

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        return None, None, game_id

    world = game.world
    return game, world, game_id


st.set_page_config(page_title="Quest Log", layout="wide")
st.title("Quest Log")

game, world, game_id = get_game_and_world()

st.markdown(f"**Game ID:** `{game_id}`")
st.markdown("---")

if world is None:
    st.warning("No world found for this Game ID yet.")
    st.stop()

st.markdown(f"**World:** **{world.title}**")
st.markdown(world.world_summary)
st.markdown("---")

# Load quests from disk (and update in-memory state)
quests = load_quests(world.world_id)
if game is not None:
    game.quests = quests

if not quests:
    st.info("No quests have been generated for this world yet.")
    st.stop()

st.subheader("All Quests")

# Sort by title for stable display
for quest_id, quest in sorted(quests.items(), key=lambda kv: kv[1].title.lower()):
    with st.expander(f"{quest.title} [{quest.status}]", expanded=False):
        if quest.giver_name or quest.giver_npc_id:
            giver_label = quest.giver_name or quest.giver_npc_id
            st.markdown(f"**Giver:** {giver_label}")

        if quest.target_location:
            st.markdown(f"**Location:** {quest.target_location}")

        if quest.summary:
            st.markdown("**Summary:**")
            st.markdown(quest.summary)

        if quest.steps:
            st.markdown("**Steps:**")
            for step in quest.steps:
                st.markdown(f"- {step}")

        if quest.rewards:
            st.markdown("**Rewards:**")
            for r in quest.rewards:
                st.markdown(f"- {r}")
        if getattr(quest, "reward_items", None):
            st.markdown("**Item Rewards:**")
            for r in quest.reward_items:
                st.markdown(f"- {r}")
