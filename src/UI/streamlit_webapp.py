# src/UI/streamlit_webapp.py

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from src.agent.char_gen import generate_character_sheet
from src.game.player_store import load_player_characters, save_player_characters
from src.agent.persona import DM_SYSTEM_PROMPT_TEMPLATE
from src.agent.types import Message
from src.llm_client import chat_completion
from src.agent.world_build import generate_world_state
from src.game.save_state import save_world_state
from src.game.game_state import get_global_games, GameState


st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")
st.title("Local Dungeon Master")


# ---------- Shared UI helper ----------

def render_character_card(pc) -> None:
    """Show a character sheet in a collapsible card."""
    with st.expander(f"{pc.name} ({pc.player_name}) – Level {pc.level}"):
        st.markdown(f"**Concept:** {pc.concept}")
        st.markdown(f"**Gender:** {pc.gender}")
        st.markdown(f"**Ancestry:** {pc.ancestry}")
        st.markdown(f"**Archetype:** {pc.archetype}")
        st.markdown(f"**HP:** {pc.current_hp} / {pc.max_hp}")

        st.markdown("**Stats**")
        cols = st.columns(6)
        for i, key in enumerate(["STR", "DEX", "CON", "INT", "WIS", "CHA"]):
            with cols[i]:
                st.metric(key, pc.stats.get(key, 10))

        if pc.skills:
            st.markdown("**Skills:**")
            for s in pc.skills:
                st.markdown(f"- {s}")

        if pc.inventory:
            st.markdown("**Inventory:**")
            for item in pc.inventory:
                st.markdown(f"- {item}")

        if pc.notes:
            st.markdown("**Notes:**")
            for note in pc.notes:
                st.markdown(f"- {note}")


# ---------- Session-local UI state ----------

if "player_names" not in st.session_state:
    st.session_state.player_names = []

if "game_id" not in st.session_state:
    st.session_state.game_id = "default"  # default table name


# ---------- Sidebar: Game ID + players + controls ----------

with st.sidebar:
    st.subheader("Game / Table")

    game_id_input = st.text_input(
        "Game ID (share this with others to join the same table)",
        value=st.session_state.game_id,
        help="Everyone who enters the same Game ID shares the same world and chat.",
    )

    game_id = game_id_input.strip() or "default"
    st.session_state.game_id = game_id

    st.markdown(f"**Current Game ID:** `{game_id}`")

    st.markdown("---")

# not needed anymore!
#    setting = st.text_area(
#        "Default setting idea (optional)",
#        value="A classic high-fantasy world filled with magic, dungeons, and dragons.",
#        height=100,
#    )

    players_raw = st.text_input(
        "Player names (comma-separated, local to you)",
        value="Alice, Bob",
        help="Names of the human players at the table. Each browser can set its own list for the speaker dropdown.",
    )

    startbutton = st.button("Start/Reset Game (for this Game ID)", type="primary")

    if st.button("Reset the LLM Model"):
        from src.llm_client import reset_model
        reset_model()
        st.success("Model reloaded with fresh settings!")


# Parse player names (per browser)
player_names = [p.strip() for p in players_raw.split(",") if p.strip()]
if player_names:
    st.session_state.player_names = player_names


# ---------- Get shared GameState for this Game ID ----------

games = get_global_games()
if game_id not in games:
    games[game_id] = GameState()

game: GameState = games[game_id]

# If DM hits "Start/Reset Game", clear the shared state for this game_id
if startbutton:
    game.world = None
    game.messages.clear()
    game.player_characters.clear()


# ---------- Layout ----------

left_col, right_col = st.columns([3, 1])


# =========================
# LEFT COLUMN: GAME LOG
# =========================

with left_col:
    st.subheader("Game Log")

    st.markdown(f"**Game ID:** `{game_id}`")
    st.caption("Share this ID with other players so they join the same game.")

    # Initial DM greeting if no world and no assistant messages yet
    if (
        game.world is None
        and not any(m.role == "assistant" for m in game.messages)
    ):
        setup_system_prompt = (
            "You are an AI Dungeon Master preparing to run a new campaign. "
            "Your first job is ONLY to ask the player to describe the world or setting "
            "they want to play in. Ask 1–3 short guiding questions, then wait."
        )
        game.messages.append(
            Message(role="system", content=setup_system_prompt, speaker=None)
        )

        initial_dm_text = (
            "Welcome, adventurer!\n\n"
            "Before we begin, tell me about the world or setting you want to play in. "
            "You can mention the genre (fantasy, sci-fi, horror, etc.), the tone "
            "(light-hearted, dark, epic), the level of magic or technology, and any themes you like."
        )
        game.messages.append(
            Message(role="assistant", content=initial_dm_text, speaker="DM")
        )

    # Render chat history (skip system messages visually)
    for msg in game.messages:
        if msg.role == "user":
            label = msg.speaker or "Player"
            with st.chat_message("user"):
                st.markdown(f"**{label}:** {msg.content}")
        elif msg.role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # Who is speaking in THIS browser
    current_speaker = None
    if st.session_state.player_names:
        current_speaker = st.selectbox(
            "Who is speaking (local to this browser)?",
            options=st.session_state.player_names,
            index=0,
        )
    else:
        st.info("No local players defined, use the sidebar to add them.")

    pcs_exist = bool(game.player_characters)
    world_exists = game.world is not None

    # Main chat input
    if not world_exists:
        user_input = st.chat_input(
            "Describe the world to begin. This will be used to forge the campaign setting."
        )
    elif world_exists and not pcs_exist:
        st.info(
            "The world is created. Next, create at least one character on the right. "
            "Once you have characters, you can start playing."
        )
        user_input = None
    else:
        user_input = st.chat_input("Play as your character(s). What do you do?")

    if user_input:
        # CASE 1: no world yet => treat as world description
        if game.world is None:
            desc_msg = Message(role="user", content=user_input, speaker="Player")
            game.messages.append(desc_msg)

            with st.chat_message("user"):
                st.markdown(f"**Player:** {user_input}")

            with st.chat_message("assistant"):
                with st.spinner("Forging your world..."):
                    # Use game_id as world_id so saves separate by table
                    world = generate_world_state(
                        setting_prompt=user_input,
                        players=st.session_state.player_names or ["Player"],
                        world_id=game_id,
                    )

                    save_world_state(world)
                    game.world = world

                    # Load any existing PCs for this world (if saved earlier)
                    game.player_characters = load_player_characters(world.world_id)

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

                    # Reset message history to world-based system + intro
                    game.messages = [
                        Message(role="system", content=system_prompt, speaker=None)
                    ]

                    intro = (
                        f"Very well. We will play in the world of **{world.title}**.\n\n"
                        f"{world.world_summary}\n\n"
                        "You stand at the beginning of a new adventure. "
                        "Tell me who you are and what you are doing as the story opens."
                    )
                    st.markdown(intro)

                    game.messages.append(
                        Message(
                            role="assistant",
                            content=intro,
                            speaker="Dungeon Master",
                        )
                    )

        # CASE 2: world exists => normal DM interaction
        else:
            if not pcs_exist:
                st.warning(
                    "Create at least one character on the right before continuing."
                )
            else:
                speaker = current_speaker or "Player"

                user_msg = Message(role="user", content=user_input, speaker=speaker)
                game.messages.append(user_msg)

                with st.chat_message("user"):
                    st.markdown(f"**{speaker}:** {user_input}")

                with st.chat_message("assistant"):
                    with st.spinner("The DM is thinking...."):
                        reply = chat_completion(
                            game.messages,
                            temperature=0.6,
                        )
                        st.markdown(reply)

                dm_msg = Message(
                    role="assistant", content=reply, speaker="Dungeon Master"
                )
                game.messages.append(dm_msg)


# =========================
# RIGHT COLUMN: TABLE INFO + CHARACTERS
# =========================

#''' TRYING WITH THIS COMMENTED OUT!
#with right_col:
#    st.subheader("Table Info")

#    st.markdown(f"**Game ID:** `{game_id}`")
#    st.markdown("Share this with other players so they join the same table.")
#    st.markdown("---")

#    st.markdown("**Local players at this browser:**")
#    if st.session_state.player_names:
#        for name in st.session_state.player_names:
#            st.markdown(f"- {name}")
#    else:
#        st.markdown("_No local player names defined._")#

#    st.markdown("---")

#    world = game.world
#    if world is None:
#        st.info("Create a world first. Once the world is generated, you can create characters here.")
#    
#    if st.button("World Information"):
#        wb.open_new_tab(f"http://localhost:8501/world_info?game_id={game_id}")
        
        
#        st.markdown("---")
#        st.markdown("### Characters")
#'''

with right_col:
    st.subheader("Table Info")

    st.markdown(f"**Game ID:** `{game_id}`")
    st.markdown("Share this with other players so they join the same table.")
    st.markdown("---")

    st.markdown("**Local players at this browser:**")
    if st.session_state.player_names:
        for name in st.session_state.player_names:
            st.markdown(f"- {name}")
    else:
        st.markdown("_No local player names defined._")

    st.markdown("---")

    world = game.world
    if world is None:
        st.info("Create a world first. Once the world is generated, you can create characters here.")
    else:

        # --- OPEN IN NEW TAB BUTTONS ---
        world_url = f"http://localhost:8501/world_info?game_id={game_id}"
        char_url  = f"http://localhost:8501/char_manager?game_id={game_id}"

        if st.button("Open World Information"):
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

        st.markdown("---")
        st.markdown(
            "Use the buttons above to open detailed views in new tabs. "
            "World Information shows the setting; Character Manager handles character creation and sheets."
        )