# src/UI/streamlit_webapp.py

import sys
import json
import re
from datetime import datetime
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
from src.game.save_state import save_world_state, load_world_state
from src.game.game_state import get_global_games, GameState
from src.game.player_store import load_player_characters
from src.agent.npc_gen import generate_npcs_for_world
from src.game.npc_store import save_npcs, load_npcs
from src.agent.party_summary import build_party_summary
from src.game.party_store import save_party_summary
from src.game.dice import roll_dice
from src.agent.dm_dice import dm_turn_with_dice

from src.agent.quest_gen import generate_quests_for_world
from src.game.quest_store import save_quests, load_quests
from src.agent.quest_commands import handle_quest_command
from src.game.save_load import save_world_bundle, load_world_bundle
from src.game.turn_store import load_turn_log, save_turn_log, begin_turn, add_turn_note


# Initiative helpers
def rebuild_initiative_order(game: GameState) -> None:
    pcs = game.player_characters or {}
    ordered = sorted(
        pcs.values(),
        key=lambda pc: getattr(pc, "initiative", 0),
        reverse=True,
    )
    game.initiative_order = [pc.pc_id for pc in ordered]
    game.active_turn_index = 0 if game.initiative_order else 0


def current_actor(game: GameState):
    if not game.initiative_order:
        return None
    if game.active_turn_index >= len(game.initiative_order):
        game.active_turn_index = 0
    pc_id = game.initiative_order[game.active_turn_index]
    return game.player_characters.get(pc_id)


def add_turn_system_message(game: GameState, pc) -> None:
    if not pc:
        return
    turn_line = (
        f"[TURN] Active character: {pc.name} (player {pc.player_name}). "
        "Use this character for all actions until the turn advances."
    )
    game.messages.append(Message(role="system", content=turn_line))


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "game"


def export_game_snapshot(game: GameState) -> Path:
    if game.world is None:
        raise ValueError("Cannot export snapshot without a world.")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    world_slug = _slug(getattr(game.world, "title", "") or getattr(game.world, "world_id", "world"))
    char_names = "-".join(_slug(pc.name) for pc in game.player_characters.values()) or "no_chars"
    folder_name = f"{timestamp}_{world_slug}_{char_names}"

    export_root = Path("saves") / "snapshots" / folder_name
    export_root.mkdir(parents=True, exist_ok=True)

    world_path = export_root / "world.json"
    players_path = export_root / "players.json"
    npcs_path = export_root / "npcs.json"
    quests_path = export_root / "quests.json"
    summary_path = export_root / "party_summary.txt"

    world_data = game.world.to_dict() if hasattr(game.world, "to_dict") else {}
    players_data = {pc_id: pc.to_dict() for pc_id, pc in (game.player_characters or {}).items()}
    npcs_data = {npc_id: npc.to_dict() for npc_id, npc in (game.npcs or {}).items()}
    quests_data = {qid: quest.to_dict() for qid, quest in (game.quests or {}).items()}

    summary_text = build_party_summary(game.player_characters) if game.player_characters else "No characters."

    world_path.write_text(json.dumps(world_data, indent=2), encoding="utf-8")
    players_path.write_text(json.dumps(players_data, indent=2), encoding="utf-8")
    npcs_path.write_text(json.dumps(npcs_data, indent=2), encoding="utf-8")
    quests_path.write_text(json.dumps(quests_data, indent=2), encoding="utf-8")
    summary_path.write_text(summary_text, encoding="utf-8")

    return export_root



# UI SETTINGS & CSS CLEANUP


st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")

# Hide Streamlit multipage menu
hide_css = """
<style>
[data-testid="stSidebarNav"] { display: none; }
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)



# SESSION / GAME ID SETUP


st.title("Local Dungeon Master")

if "player_names" not in st.session_state:
    st.session_state.player_names = []

if "game_id" not in st.session_state:
    st.session_state.game_id = "default"

# Initialize shared game state early so sidebar buttons can use it
games = get_global_games()
game_id = st.session_state.game_id


# SIDEBAR


with st.sidebar:
    st.subheader("Game / Table")

    game_id_input = st.text_input(
        "Game ID (share this with others to join)",
        value=st.session_state.game_id,
    )

    game_id = game_id_input.strip() or "default"
    st.session_state.game_id = game_id
    game_id = st.session_state.game_id
    if game_id not in games:
        games[game_id] = GameState()
    game: GameState = games[game_id]

    world_url = f"http://localhost:8501/world_info?game_id={game_id}"
    char_url = f"http://localhost:8501/char_manager?game_id={game_id}"
    quest_url = f"http://localhost:8501/quest_log?game_id={game_id}"
    npc_url = f"http://localhost:8501/npc_log?game_id={game_id}"

    st.markdown(f"**Current Game ID:** `{game_id}`")

    st.markdown("---")

    players_raw = st.text_input(
        "Player names (comma-separated, local only)",
        value="Alice, Bob",
    )

    startbutton = st.button("Reset Game (this ID)", type="primary")
    save_state_clicked = st.button("Save world state", disabled=game.world is None)
    bundle_file = st.file_uploader("Load world state (bundle .json)", type=["json"])

    if st.button("Reset the LLM Model"):
        from src.llm_client import reset_model
        reset_model()
        st.success("Model reloaded!")

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

    if save_state_clicked:
        try:
            export_path = save_world_bundle(game)
            st.success(f"Game state saved to {export_path}")
        except Exception as e:
            st.error(f"Could not save game state: {e}")

    if bundle_file is not None:
        try:
            world, players, npcs, quests, init_order, active_idx = load_world_bundle(bundle_file.getvalue())
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
                        m for m in game.messages
                        if not (m.role == "system" and "PARTY SUMMARY" in m.content)
                    ]
                    game.messages.append(Message(role="system", content=summary_text))
                    path = save_party_summary(game.world.world_id, summary_text)
                    st.success(f"Party summary refreshed and saved to {path}")

    initiative_sidebar = st.container()

player_names = [p.strip() for p in players_raw.split(",") if p.strip()]
st.session_state.player_names = player_names



# GET GAME STATE
# game is already initialized in the sidebar block to ensure buttons work there

if startbutton:
    game.world = None
    game.messages.clear()
    game.player_characters.clear()
    game.npcs = {}
    game.quests = {}
    game.initiative_order = []
    game.active_turn_index = 0
    if hasattr(game, "turn_log"):
        delattr(game, "turn_log")

# Load an existing world (by Game ID)
# INPUT HANDLING


world_exists = game.world is not None
pcs_exist = bool(game.player_characters)

if not world_exists:
    chat_prompt = "Describe the world to begin."
elif world_exists and not pcs_exist:
    chat_prompt = "World created. Make characters first."
else:
    chat_prompt = "Play your turn. Use /action for mechanics."


user_input = st.chat_input(chat_prompt)



# WORLD CREATION


if user_input and not world_exists:
    desc_msg = Message(role="user", content=user_input, speaker="Player")
    game.messages.append(desc_msg)

    with st.spinner("Forging world..."):
        world = generate_world_state(
            setting_prompt=user_input,
            players=st.session_state.player_names or ["Player"],
            world_id=game_id,
        )

        save_world_state(world)
        game.world = world

        # Generate NPCs
        game.npcs = generate_npcs_for_world(world, max_npcs=10)
        save_npcs(world.world_id, game.npcs)

        # Generate quests
        game.quests = generate_quests_for_world(world, game.npcs)
        save_quests(world.world_id, game.quests)

        players_str = ", ".join(world.players)

        system_prompt = DM_SYSTEM_PROMPT_TEMPLATE.format(
            title=world.title,
            world_summary=world.world_summary,
            lore=world.lore,
            players=players_str,
        )

        game.messages = [
            Message(role="system", content=system_prompt)
        ]

        intro = (
            f"Welcome to **{world.title}**.\n\n"
            f"{world.world_summary}\n\n"
            "Tell me who you are as the story opens."
        )
        game.messages.append(
            Message(role="assistant", content=intro, speaker="Dungeon Master")
        )

        game.turn_log = load_turn_log(world.world_id)

    world_exists = True



# GAMEPLAY INPUT (WORLD EXISTS + PCS EXIST)


if user_input and world_exists and pcs_exist:
    speaker = (
        st.session_state.player_names[0]
        if st.session_state.player_names
        else "Player"
    )

    # 1) Intercept /quest commands
    if handle_quest_command(user_input, game):
        game.messages.append(
            Message(role="user", content=user_input, speaker=speaker)
        )

    else:
        # 2) Start-game normalization
        normalized = user_input.strip().lower()
        if normalized in {"start", "begin", "let's begin", "i am ready"}:
            if len(game.player_characters) == 1:
                pc = next(iter(game.player_characters.values()))
                user_input = (
                    "We are ready to begin. "
                    f"Introduce {pc.name}, a level {pc.level} "
                    f"{pc.ancestry} {pc.archetype}, and describe the opening scene."
                )
            else:
                user_input = (
                    "We are ready to begin. Use PARTY SUMMARY. "
                    "Describe the opening scene without making new characters."
                )

        # 3) Normal player message
        game.messages.append(
            Message(role="user", content=user_input, speaker=speaker)
        )

        # 4) DM turn, with dice support for /action
        with st.spinner("The DM is thinking..."):
            game.messages = dm_turn_with_dice(
                game.messages,
            game.player_characters,
            )
            if hasattr(game, "turn_log"):
                note = f"{speaker}: {user_input}"
                game.turn_log = add_turn_note(game.turn_log, note)
                save_turn_log(game.turn_log)



# PARTY SUMMARY (add once)


world_exists = game.world is not None
pcs_exist = bool(game.player_characters)

if world_exists and pcs_exist:
    has_summary = any(
        m.role == "system" and "PARTY SUMMARY" in m.content
        for m in game.messages
    )

    if not has_summary:
        summary_text = build_party_summary(game.player_characters)
        if summary_text:
            game.messages.append(
                Message(role="system", content=summary_text)
            )
            if game.world is not None:
                save_party_summary(game.world.world_id, summary_text)



# INITIATIVE CONTROLS (SIDEBAR)

with initiative_sidebar:
    st.subheader("Initiative")
    pcs_exist = bool(game.player_characters)
    if st.button("Build Initiative Order", disabled=not pcs_exist):
        rebuild_initiative_order(game)
        actor = current_actor(game)
        if actor:
            add_turn_system_message(game, actor)
            if game.world is not None:
                if not hasattr(game, "turn_log"):
                    game.turn_log = load_turn_log(game.world.world_id)
                game.turn_log = begin_turn(game.turn_log, actor)
                save_turn_log(game.turn_log)
            st.success(
                f"Initiative set. First turn: {actor.name} (Initiative {getattr(actor, 'initiative', 0)})."
            )
        else:
            st.info("Initiative order is empty.")

    if st.button("Next Turn", disabled=not game.initiative_order):
        if game.initiative_order:
            game.active_turn_index = (game.active_turn_index + 1) % len(game.initiative_order)
            actor = current_actor(game)
            if actor:
                add_turn_system_message(game, actor)
                if game.world is not None:
                    if not hasattr(game, "turn_log"):
                        game.turn_log = load_turn_log(game.world.world_id)
                    game.turn_log = begin_turn(game.turn_log, actor)
                    save_turn_log(game.turn_log)
                st.info(f"Next up: {actor.name} (Initiative {getattr(actor, 'initiative', 0)}).")

    if game.initiative_order:
        order_names = [
            game.player_characters.get(pc_id).name
            for pc_id in game.initiative_order
            if game.player_characters.get(pc_id)
        ]
        st.caption(f"Order: {', '.join(order_names)}")



# LAYOUT - SINGLE COLUMN (Game Log only)
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
elif st.session_state.player_names:
    st.selectbox(
        "Who is speaking (local)?",
        options=st.session_state.player_names,
        index=0,
        key="current_speaker",
    )
else:
    st.info("Add players in sidebar.")



# END
