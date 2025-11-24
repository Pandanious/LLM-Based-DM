# src/UI/streamlit_webapp.py

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from src.agent.persona import DM_SYSTEM_PROMPT_TEMPLATE
from src.agent.types import Message
from src.llm_client import chat_completion
from src.agent.world_build import generate_world_state
from src.game.save_state import save_world_state
from src.game.game_state import get_global_games, GameState
from src.game.player_store import load_player_characters
from src.agent.npc_gen import generate_npcs_for_world
from src.game.npc_store import save_npcs
from src.agent.party_summary import build_party_summary

st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")
st.title("Local Dungeon Master")

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
    if hasattr(game, "npcs"):
        game.npcs.clear()

# ---------- Determine current state (BEFORE layout) ----------

world_exists = game.world is not None
pcs_exist = bool(game.player_characters)

# Decide chat prompt based on state
if not world_exists:
    chat_prompt = "Describe the world to begin. This will be used to forge the campaign setting."
elif world_exists and not pcs_exist:
    chat_prompt = "World created. Create characters in the Character Manager, then return here to play."
else:
    chat_prompt = "Play as your character(s). What do you do?"

# Single global chat input (must be outside columns)
user_input = st.chat_input(chat_prompt)

# ---------- Handle input / world creation / DM interaction ----------

if user_input:
    # CASE 1: world not yet created -> treat input as world description
    if not world_exists:
        # Initial system + prompt will be set after world generation.
        # For now, just show the player's description as a user message in the log.
        desc_msg = Message(role="user", content=user_input, speaker="Player")
        game.messages.append(desc_msg)

        # Generate world + NPCs
        with st.spinner("Forging your world..."):
            world = generate_world_state(
                setting_prompt=user_input,
                players=st.session_state.player_names or ["Player"],
                world_id=game_id,
            )

            save_world_state(world)
            game.world = world

            # Load any existing PCs for this world (if saved earlier)
            game.player_characters = load_player_characters(world.world_id)

            # Auto-generate NPCs once per world
            if hasattr(game, "npcs"):
                game.npcs = generate_npcs_for_world(world, max_npcs=10)
                save_npcs(world.world_id, game.npcs)

            players_str = (
                ", ".join(world.players) if world.players else "Unnamed adventurers"
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

            game.messages.append(
                Message(
                    role="assistant",
                    content=intro,
                    speaker="Dungeon Master",
                )
            )

    # CASE 2: world exists and PCs exist -> normal DM interaction
    elif world_exists and pcs_exist:
        # We decide who is speaking later inside the left column (UI selectbox),
        # but we need a default speaker now in case current_speaker isn't set yet.
        speaker = st.session_state.player_names[0] if st.session_state.player_names else "Player"

        user_msg = Message(role="user", content=user_input, speaker=speaker)
        game.messages.append(user_msg)

        with st.spinner("The DM is thinking...."):
            reply = chat_completion(
                game.messages,
                temperature=0.6,
            )

        dm_msg = Message(
            role="assistant", content=reply, speaker="Dungeon Master"
        )
        game.messages.append(dm_msg)

    # CASE 3: world exists but no PCs yet -> ignore input (we already tell the user via prompt)
    else:
        pass  # No-op; user should create characters first in Character Manager

# After handling input, recompute state (world may now exist)
world_exists = game.world is not None
pcs_exist = bool(game.player_characters)
# If we have PCs and no party summary yet, add one as a system message
if world_exists and pcs_exist:
    has_party_summary = any(
        m.role == "system" and "PARTY SUMMARY" in m.content
        for m in game.messages
    )
    if not has_party_summary:
        summary_text = build_party_summary(game.player_characters)
        if summary_text:
            game.messages.append(
                Message(
                    role="system",
                    content=summary_text,
                    speaker=None,
                )
            )
# ---------- Layout columns ----------

left_col, right_col = st.columns([3, 1])

# =========================
# RIGHT COLUMN: TABLE INFO
# =========================

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

    # URLs for the other pages (these pages must exist under src/UI/pages/)
    world_url = f"http://localhost:8501/world_info?game_id={game_id}"
    char_url = f"http://localhost:8501/char_manager?game_id={game_id}"

    # Buttons are always shown (even before world creation)
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

    if world is None:
        st.info(
            "Create a world first. Once the world is generated, you can create characters and NPCs."
        )
    else:
        # quick NPC summary
        npc_dict = getattr(game, "npcs", {}) or {}
        npc_count = len(npc_dict)
        st.markdown(f"**NPCs in this world:** {npc_count}")

        if npc_count > 0:
            sample_npcs = list(npc_dict.values())[:5]
            st.markdown("Some NPCs:")
            for npc in sample_npcs:
                st.markdown(f"- **{npc.name}** ({npc.role}) in *{npc.location}*")

# =========================
# LEFT COLUMN: GAME LOG
# =========================

with left_col:
    st.subheader("Game Log")

    st.markdown(f"**Game ID:** `{game_id}`")
    st.caption("Share this ID with other players so they join the same game.")

    # Initial greeting only if no world and no assistant messages at all
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

    # Speaker selection (only meaningful once PCs exist)
    if st.session_state.player_names:
        current_speaker = st.selectbox(
            "Who is speaking (local to this browser)?",
            options=st.session_state.player_names,
            index=0,
        )
    else:
        current_speaker = None
        st.info("No local players defined, use the sidebar to add them.")

    