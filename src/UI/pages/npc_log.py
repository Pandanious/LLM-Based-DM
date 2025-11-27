import sys
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitAPIException

# Page config must be set before any other Streamlit calls.
try:
    st.set_page_config(page_title="NPC Overview", layout="wide")
except StreamlitAPIException:
    pass

# --- Make src importable ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.game.game_state import get_global_games
from src.game.npc_store import save_npcs
from src.agent.item_gen import generate_items_for_character

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

    world = game.world
    return game, world, game_id


st.title("NPC Overview")

game, world, game_id = get_game_and_world()

st.markdown(f"**Game ID:** `{game_id}`")
st.markdown("---")

if world is None:
    st.warning("No world found for this Game ID yet.")
    st.stop()

st.markdown(f"**World:** **{world.title}**")
st.markdown(world.world_summary)
st.markdown("---")

npc_dict = getattr(game, "npcs", {}) or {}
npc_count = len(npc_dict)

st.subheader(f"NPCs in this world ({npc_count})")

if npc_count == 0:
    st.info("No NPCs generated yet for this world.")
    st.stop()

# Group by location
npcs_by_location = {}
for npc_id, npc in npc_dict.items():
    loc = getattr(npc, "location", "Unknown location")
    npcs_by_location.setdefault(loc, []).append(npc)

for location in sorted(npcs_by_location.keys()):
    npcs_here = npcs_by_location[location]
    with st.expander(f"{location} ({len(npcs_here)} NPCs)", expanded=False):
        for npc in npcs_here:
            name = getattr(npc, "name", "Unnamed NPC")
            role = getattr(npc, "role", "Unknown role")
            desc = getattr(npc, "description", "")

            # Optional tiny highlights for merchant / leader / quest giver
            role_lower = str(role).lower()
            highlight = ""
            if "merchant" in role_lower:
                highlight = " 🛒"
            elif "leader" in role_lower:
                highlight = " ⭐"
            elif "quest" in role_lower:
                highlight = " 📜"

            st.markdown(f"**{name}** — {role}{highlight}")
            if desc:
                st.markdown(f"> {desc}")

            if getattr(npc, "inventory", None):
                st.markdown("**Inventory:**")
                for item in npc.inventory:
                    st.markdown(f"- {item}")

            if "merchant" in role_lower or "vendor" in role_lower or "shop" in role_lower:
                if st.button(f"Refresh stock for {name}", key=f"refresh_{npc.npc_id}"):
                    try:
                        items = generate_items_for_character(
                            world_summary=world.world_summary if world else "",
                            archetype="merchant_stock",
                            count=4,
                        )
                        npc.inventory = [f"{it.item_name} ({it.item_category or 'gear'})" for it in items]
                        game.npcs[npc.npc_id] = npc
                        save_npcs(game.world.world_id, game.npcs)
                        st.success(f"Updated stock for {name}.")
                    except Exception as e:
                        st.error(f"Could not refresh stock: {e}")

            st.markdown("---")
