import streamlit as st

from src.agent.persona import DM_SYSTEM_PROMPT_TEMPLATE
from src.agent.types import Message
from src.agent.party_summary import build_party_summary
from src.game.player_store import load_player_characters
from src.game.party_store import save_party_summary
from src.game.save_load import save_world_bundle, save_world_seed_bundle, load_world_bundle
from src.game.turn_store import load_turn_log
from src.game.game_state import GameState


def render_save_controls(game: GameState):
    #Render buttons + handlers for saving/loading world bundles and refreshing the party summary. called from the sidebar.
    
    save_state_clicked = st.button("Save world state", disabled=game.world is None)
    quick_seed_clicked = st.button(
        "Auto-save world seed (title + players)",
        disabled=game.world is None,
        help="Writes a deterministic bundle named after the world title and players so you can reload without re-forging.",
    )
    bundle_file = st.file_uploader("Load world state (bundle .json)", type=["json"])

    # Save current world bundle
    if save_state_clicked:
        try:
            export_path = save_world_bundle(game)
            st.success(f"Game state saved to {export_path}")
        except Exception as e:
            st.error(f"Could not save game state: {e}")

    # Save deterministic bundle keyed to world title + players
    if quick_seed_clicked:
        try:
            export_path = save_world_seed_bundle(game)
            st.success(f"World seed saved to {export_path}")
        except Exception as e:
            st.error(f"Could not save seed bundle: {e}")

    # Load bundle
    if bundle_file is not None:
        try:
            world, players, npcs, quests, init_order, active_idx = load_world_bundle(
                bundle_file.getvalue()
            )
            game.world = world
            game.player_characters = players
            game.npcs = npcs
            game.quests = quests
            game.initiative_order = init_order
            game.active_turn_index = active_idx
            game.turn_log = load_turn_log(world.world_id)

            players_str = ", ".join(world.players) if world.players else "Unnamed adventurers"
            system_prompt = DM_SYSTEM_PROMPT_TEMPLATE.format(
                title=world.title,
                world_summary=world.world_summary,
                lore=world.lore,
                players=players_str,
            )

            game.messages = [Message(role="system", content=system_prompt)]

            intro = (
                f"World loaded: **{world.title}**.\n\n"
                f"{world.world_summary}\n\n"
                "Tell me who you are and what you do next."
            )
            game.messages.append(
                Message(
                    role="assistant",
                    content=intro,
                    speaker="Dungeon Master",
                )
            )

            # Inject party summary if PCs exist
            if game.player_characters:
                summary_text = build_party_summary(game.player_characters)
                if summary_text:
                    game.messages.append(Message(role="system", content=summary_text))

            st.success("Bundle loaded successfully.")
        except Exception as e:
            st.error(f"Could not load bundle: {e}")

    # Refresh party summary
    if st.button("Refresh Party Summary"):
        if game.world is None:
            st.warning("Create or load a world before refreshing the party summary.")
        else:
            pcs = load_player_characters(game.world.world_id)
            game.player_characters = pcs
            if not pcs:
                st.warning("No player characters found for this world.")
            else:
                summary_text = build_party_summary(pcs)
                if not summary_text:
                    st.warning("Could not build a party summary.")
                else:
                    # Remove old PARTY SUMMARY system messages
                    game.messages = [
                        m
                        for m in game.messages
                        if not (m.role == "system" and "PARTY SUMMARY" in m.content)
                    ]
                    game.messages.append(Message(role="system", content=summary_text))
                    path = save_party_summary(game.world.world_id, summary_text)
                    st.success(f"Party summary refreshed and saved to {path}")
