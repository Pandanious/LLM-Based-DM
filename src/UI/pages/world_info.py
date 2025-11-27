import streamlit as st
from streamlit.errors import StreamlitAPIException

from src.game.game_state import get_global_games
from src.game.npc_store import load_npcs

# Page config must be set before any other Streamlit calls.
try:
    st.set_page_config(page_title="World Information", layout="wide")
except StreamlitAPIException:
    pass

# Hide Streamlit's built-in page navigation links (use sidebar buttons instead).
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_world_from_query():
    """Extract ?game_id=XYZ and fetch world data."""
    query_params = st.query_params
    game_id = query_params.get("game_id") or st.session_state.get("game_id") or "default"

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        st.error(f"No active game for game_id '{game_id}'")
        return None, None, game_id

    return game, game.world, game_id


st.title("World Information")

game, world, game_id = get_world_from_query()

st.markdown(f"**Game ID:** `{game_id}`")

if world is None:
    st.warning("World has not been created yet.")
    st.stop()

st.header(world.title)
st.markdown(world.world_summary)

st.markdown("---")
st.subheader("Themes & Tone")
for theme in world.themes:
    st.markdown(f"- {theme}")

st.markdown("---")
st.subheader("Major Locations")
for loc in world.major_locations:
    st.markdown(f"### {loc['name']}")
    st.markdown(loc["description"])

st.markdown("---")
st.subheader("Minor Locations")
for loc in world.minor_locations:
    st.markdown(f"- **{loc['name']}** — {loc['description']}")

st.markdown("---")
st.subheader("World Lore")
st.write(world.lore)


# NPC overview

st.markdown("---")
st.subheader("NPCs in this World")

# Ensure we have NPCs loaded (from shared memory or disk)
if not game.npcs:
    game.npcs = load_npcs(world.world_id)

if not game.npcs:
    st.info("No NPCs have been generated yet for this world.")
else:
    for npc_id, npc in game.npcs.items():
        with st.expander(f"{npc.name} ({npc.role}) — {npc.location}"):
            st.markdown(f"**Attitude:** {npc.attitude}")
            if npc.tags:
                st.markdown("**Tags:** " + ", ".join(npc.tags))

            st.markdown("**Description:**")
            st.write(npc.description)

            if npc.hooks:
                st.markdown("**Hooks:**")
                for h in npc.hooks:
                    st.markdown(f"- {h}")
