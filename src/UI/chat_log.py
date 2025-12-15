import time
import streamlit as st
import streamlit.components.v1 as components

from src.game.game_state import GameState

CHAT_REFRESH_SECONDS = 2.5


def render_chat_log(game: GameState):
    
    #Render the game log, scroll button, and speaker selector
    
    st.subheader("Game Log")
    st.caption("Chat auto-refreshes so everyone sees the latest messages; scroll button is still available.")

    # Per-session toggle so multiple open browsers keep in sync without manual refresh.
    auto_refresh = st.checkbox(
        "Auto-refresh chat (all tabs)",
        value=st.session_state.get("chat_auto_refresh", True),
        key="chat_auto_refresh",
        help="Keeps the log in sync across open browsers. Turn off if you are drafting a long message.",
    )

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
    game_key = st.session_state.get("game_id", "default")
    last_seen_key = f"chat_last_seen_{game_key}"
    last_seen = st.session_state.get(last_seen_key, 0)
    new_message = len(game.messages) > last_seen
    st.session_state[last_seen_key] = len(game.messages)

    for msg in game.messages:
        if msg.role == "user":
            with st.chat_message("user"):
                st.markdown(f"**{msg.speaker}:** {msg.content}")
        elif msg.role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # Auto-scroll when a new message arrives (useful with auto-refresh on).
    if new_message:
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

    if auto_refresh:
        time.sleep(CHAT_REFRESH_SECONDS)
        st.rerun()
