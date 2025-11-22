import streamlit as st
from urllib.parse import urlparse, parse_qs

from src.game.game_state import get_global_games


def get_world_from_query():
    """Extract ?game_id=XYZ and fetch world data."""
    query_params = st.query_params
    game_id = query_params.get("game_id", "default")

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        st.error(f"No active game for game_id '{game_id}'")
        return None, game_id

    return game.world, game_id


st.set_page_config(page_title="World Information", layout="wide")
st.title("World Information")

world, game_id = get_world_from_query()

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