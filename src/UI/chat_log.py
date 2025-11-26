import streamlit as st
import streamlit.components.v1 as components

from src.game.game_state import GameState


def render_chat_log(game: GameState) -> None:
    """
    Render the game log, scroll button, and speaker selector.
    """
    st.subheader("Game Log")
    st.caption("Use Scroll button to jump to bottom.")

    # Scroll-to-latest button
    if st.button("Scroll to latest message"):
        components.html(
            """
            <script>
            const doc = window.parent.document || document;
            const block = doc.querySelector('.block-container');
            if (block) block.scrollTop = block.scrollHeight;
            doc.documentElement.scrollTop = doc.documentElement.scrollHeight;
            </script>
            """,
            height=0,
        )

    # Render chat history
    for msg in game.messages:
        if msg.role == "user":
            with st.chat_message("user"):
                st.markdown(f"**{msg.speaker}:** {msg.content}")
        elif msg.role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # Speaker selector (use player:character when PCs exist)
    if game.player_characters:
        pc_options = [
            f"{pc.player_name}:{pc.name}"
            for pc in game.player_characters.values()
        ]
        st.selectbox(
            "Who is speaking (player:character)?",
            options=pc_options,
            index=0,
            key="current_speaker",
        )
    elif st.session_state.get("player_names"):
        st.selectbox(
            "Who is speaking (local)?",
            options=st.session_state["player_names"],
            index=0,
            key="current_speaker",
        )
    else:
        st.info("Add players in sidebar.")
