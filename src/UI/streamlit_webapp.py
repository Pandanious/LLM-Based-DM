import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import streamlit as st
from src.agent.char_gen import generate_character_sheet
from src.game.player_store import load_player_characters, save_player_characters
from src.agent.persona import DM_SYSTEM_PROMPT_TEMPLATE
from src.agent.types import Message
from src.llm_client import chat_completion
from src.agent.world_build import generate_world_state
from src.game.save_state import save_world_state  # load_world_state kept for later


st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")

st.title("Local Dungeon Master")

st.write(
    "The DM will first ask you to describe the world. "
    "Your description will be used to create a campaign world, which is then saved."
)

# --- Session state setup ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if "world_built" not in st.session_state:
    st.session_state.world_built = False

if "current_world" not in st.session_state:
    st.session_state.current_world = None

if "player_names" not in st.session_state:
    st.session_state.player_names = []

if "player_characters" not in st.session_state:
    st.session_state.player_characters = {}

# --- Sidebar: players + controls ---

with st.sidebar:
    setting = st.text_area(
        "Setting / scenario description (optional for now)",
        value="A classic high-fantasy world filled with magic, dungeons, and dragons.",
        height=120,
    )

    players_raw = st.text_input(
        "Player names (comma-separated)",
        value="Alice, Bob",
        help="These are the player characters at the table.",
    )

    startbutton = st.button("Start/Reset Game", type="primary")

    if st.button("Reset the LLM Model"):
        from src.llm_client import reset_model
        reset_model()
        st.success("Model reloaded with fresh settings!")


# Parse player names from sidebar
player_names = [p.strip() for p in players_raw.split(",") if p.strip()]
if player_names:
    st.session_state.player_names = player_names


# (Optional for later) Start/Reset Game via sidebar
# For now, we'll just clear the state if startbutton is pressed
if startbutton:
    st.session_state.messages = []
    st.session_state.world_built = False
    st.session_state.current_world = None




# --- LEFT / RIGHT layout ---

left_col, right_col = st.columns([3, 1])

with left_col:
    st.subheader("Game Log")

    # If no world and no DM greeting yet, add initial system + DM question
    if (
        not st.session_state.world_built
        and not any(m.role == "assistant" for m in st.session_state.messages)
    ):
        setup_system_prompt = (
            "You are an AI Dungeon Master preparing to run a new campaign. "
            "Your first job is ONLY to ask the player to describe the world or setting "
            "they want to play in. Ask 1–3 short guiding questions, then wait."
        )
        st.session_state.messages.append(
            Message(role="system", content=setup_system_prompt, speaker=None)
        )

        initial_dm_text = (
            "Welcome, adventurer!\n\n"
            "Before we begin, tell me about the world or setting you want to play in. "
            "You can mention the genre (fantasy, sci-fi, horror, etc.), the tone "
            "(light-hearted, dark, epic), the level of magic or technology, and any themes you like."
        )
        st.session_state.messages.append(
            Message(role="assistant", content=initial_dm_text, speaker="DM")
        )

    # Render chat history (skip system messages visually)
    for msg in st.session_state.messages:
        if msg.role == "user":
            label = msg.speaker or "Player"
            with st.chat_message("user"):
                st.markdown(f"**{label}:** {msg.content}")
        elif msg.role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # Who is speaking (only used once world is built)
    current_speaker = None
    if st.session_state.player_names:
        current_speaker = st.selectbox(
            "Who is speaking?",
            options=st.session_state.player_names,
            index=0,
        )
    else:
        st.info("Participants are not defined, use the sidebar to add them.")

    # --- Main chat input ---
    user_input = st.chat_input(
        "Describe the world to begin, then play as your character(s)."
    )

    if user_input:
        # CASE 1: world is NOT built yet → treat this input as world description
        if not st.session_state.world_built:
            # Log the player's description of the world
            desc_msg = Message(role="user", content=user_input, speaker="Player")
            st.session_state.messages.append(desc_msg)

            with st.chat_message("user"):
                st.markdown(f"**Player:** {user_input}")

            # Build the world from this description
            with st.chat_message("assistant"):
                with st.spinner("Forging your world..."):
                    world = generate_world_state(
                        setting_prompt=user_input,
                        players=st.session_state.player_names or ["Player"],
                        world_id="default",
                    )

                    save_world_state(world)
                    st.session_state.current_world = world
                    st.session_state.world_built = True

                    players_str = (
                        ", ".join(world.players)
                        if world.players
                        else "Unnamed adventurers"
                    )

                    system_prompt = DM_SYSTEM_PROMPT_TEMPLATE.format(
                        title=world.title,
                        world_summary=world.world_summary,
                        lore=world.lore,
                        players=players_str,
                    )

                    # Reset history to proper world-based system message
                    st.session_state.messages = [
                        Message(role="system", content=system_prompt, speaker=None)
                    ]

                    intro = (
                        f"Very well. We will play in the world of **{world.title}**.\n\n"
                        f"{world.world_summary}\n\n"
                        "You stand at the beginning of a new adventure. "
                        "Tell me who you are and what you are doing as the story opens."
                    )
                    st.markdown(intro)

                    st.session_state.messages.append(
                        Message(
                            role="assistant",
                            content=intro,
                            speaker="Dungeon Master",
                        )
                    )

        # CASE 2: world IS built → normal multi-player DM interaction
        else:
            speaker = current_speaker or "Player"

            user_msg = Message(role="user", content=user_input, speaker=speaker)
            st.session_state.messages.append(user_msg)

            with st.chat_message("user"):
                st.markdown(f"**{speaker}:** {user_input}")

            with st.chat_message("assistant"):
                with st.spinner("The DM is thinking...."):
                    reply = chat_completion(
                        st.session_state.messages,
                        temperature=0.6,
                    )
                    st.markdown(reply)

            dm_msg = Message(
                role="assistant", content=reply, speaker="Dungeon Master"
            )
            st.session_state.messages.append(dm_msg)


with right_col:
    st.subheader("Table Info")
    st.markdown("Players at the table:")
    if st.session_state.player_names:
        for name in st.session_state.player_names:
            st.markdown(f"- {name}")
    else:
        st.markdown("No players defined.")
    st.markdown("---")
    st.markdown("Use the sidebar to update the setting or restart the game.")
