
import streamlit as st
import streamlit.components.v1 as components

from src.UI.game_state import get_or_create_game
from src.UI.save_controls import render_save_controls
from src.game.game_state import GameState
from typing import Dict, Tuple


def render_sidebar(
    games: Dict[str, GameState],
) -> Tuple[GameState, str, str, bool, st.delta_generator.DeltaGenerator]:
    """
    Render the entire sidebar and return:
      - game: GameState for current ID
      - game_id: current Game ID
      - players_raw: raw CSV string of player names
      - startbutton: whether reset button was pressed
      - initiative_sidebar: container to render initiative controls into
    """
    with st.sidebar:
        st.subheader("Game / Table")

        # Game ID selection
        game_id_input = st.text_input(
            "Game ID (share this with others to join)",
            value=st.session_state.get("game_id", "default"),
        )
        game_id = (game_id_input.strip() or "default")
        st.session_state.game_id = game_id

        game = get_or_create_game(games, game_id)

        world_url = f"http://localhost:8501/world_info?game_id={game_id}"
        char_url = f"http://localhost:8501/char_manager?game_id={game_id}"
        quest_url = f"http://localhost:8501/quest_log?game_id={game_id}"
        npc_url = f"http://localhost:8501/npc_log?game_id={game_id}"

        st.markdown(f"**Current Game ID:** `{game_id}`")

        st.markdown("---")

        # Local player names
        players_raw = st.text_input(
            "Player names (comma-separated, local only)",
            value="Alice, Bob",
        )

        startbutton = st.button("Reset Game (this ID)", type="primary")

        # Save / load / party-summary controls
        render_save_controls(game)

        # LLM reset
        if st.button("Reset the LLM Model"):
            from src.llm_client import reset_model
            reset_model()
            st.success("Model reloaded!")

        # Help
        if st.button("Help / How to Interact"):
            help_url = f"http://localhost:8501/help?game_id={game_id}"
            components.html(
                f"""
                <script>
                    window.open("{help_url}", "_blank");
                </script>
                """,
                height=0,
            )

        st.markdown("**World Options:**")
        if st.button("Open World Info"):
            components.html(
                f"""
                <script>
                    window.open("{world_url}", "_blank");
                </script>
                """,
                height=0,
            )
        if st.button("Open Character Manager"):
            components.html(
                f"""
                <script>
                    window.open("{char_url}", "_blank");
                </script>
                """,
                height=0,
            )
        if st.button("Open Quest Log"):
            components.html(
                f"""
                <script>
                    window.open("{quest_url}", "_blank");
                </script>
                """,
                height=0,
            )
        if st.button("Open NPC Log"):
            components.html(
                f"""
                <script>
                    window.open("{npc_url}", "_blank");
                </script>
                """,
                height=0,
            )

        # Placeholder for initiative controls (rendered later)
        initiative_sidebar = st.container()

    return game, game_id, players_raw, startbutton, initiative_sidebar
