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
from src.game.save_state import save_world_state


st.set_page_config(page_title="Local RPG Dungeon Master", layout="wide")

st.title("Local Dungeon Master")

st.write(
    "The DM will first ask you to describe the world. "
    "Your description will be used to create a campaign world, which is then saved. "
    "After that, you can create character sheets for each player on the right."
)


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
        help="These are the human players at the table.",
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

# Start/Reset Game via sidebar: clear state
if startbutton:
    st.session_state.messages = []
    st.session_state.world_built = False
    st.session_state.current_world = None
    st.session_state.player_characters = {}

# --- LEFT / RIGHT layout ---

left_col, right_col = st.columns([3, 1])

# =========================
# LEFT COLUMN: GAME LOG
# =========================

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

    pcs_exist = bool(st.session_state.player_characters)
    world_exists = st.session_state.world_built

    # --- Main chat input ---
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
        user_input = st.chat_input(
            "Play as your character(s). Describe what you do."
        )

    if user_input:
        # CASE 1: world is NOT built yet → treat this input as world description
        if not st.session_state.world_built:
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

                    st.session_state.player_characters = load_player_characters(
                        world.world_id
                    )

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

        # CASE 2: world IS built AND we have characters → normal interaction
        else:
            if not pcs_exist:
                st.warning(
                    "Create at least one character on the right before continuing."
                )
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


# =========================
# RIGHT COLUMN: TABLE INFO + CHARACTERS
# =========================

with right_col:
    st.subheader("Table Info")

    st.markdown("**Players at the table:**")
    if st.session_state.player_names:
        for name in st.session_state.player_names:
            st.markdown(f"- {name}")
    else:
        st.markdown("_No players defined. Use the sidebar to add them._")

    st.markdown("---")

    current_world = st.session_state.get("current_world", None)
    if current_world is None:
        st.info(
            "Create a world first. Once the world is generated, you can create characters here."
        )
    else:
        world_id = current_world.world_id
        st.markdown("### Characters")

        for player_name in st.session_state.player_names:
            pc_id = f"{world_id}_{player_name.lower().replace(' ', '_')}"
            existing_pc = st.session_state.player_characters.get(pc_id)

            st.markdown(f"**{player_name}**")

            # user-defined fields
            name_key = f"char_name_{pc_id}"
            gender_key = f"gender_{pc_id}"
            ancestry_key = f"ancestry_{pc_id}"
            concept_key = f"concept_{pc_id}"

            default_name = existing_pc.name if existing_pc else f"{player_name}'s character"
            default_gender = existing_pc.gender if existing_pc else ""
            default_ancestry = existing_pc.ancestry if existing_pc else ""
            default_concept = existing_pc.concept if existing_pc else ""

            char_name = st.text_input(
                f"Character name for {player_name}",
                key=name_key,
                value=default_name,
            )
            gender = st.text_input(
                f"Gender for {player_name}'s character",
                key=gender_key,
                value=default_gender,
                placeholder="e.g. female, male, non-binary",
            )
            ancestry = st.text_input(
                f"Ancestry for {player_name}'s character",
                key=ancestry_key,
                value=default_ancestry,
                placeholder="e.g. human, elf, android",
            )
            concept = st.text_area(
                f"Character idea / concept for {player_name}",
                key=concept_key,
                value=default_concept,
                height=80,
                placeholder="e.g. A jaded street doctor who patches up gangsters for cash.",
            )

            cols = st.columns([1, 1])
            with cols[0]:
                if st.button(
                    f"Generate / Re-roll for {player_name}", key=f"gen_{pc_id}"
                ):
                    if not concept.strip():
                        st.warning("Please describe the character idea first.")
                    else:
                        with st.spinner(f"Generating character for {player_name}..."):
                            pc = generate_character_sheet(
                                world_summary=current_world.world_summary,
                                world_skills=current_world.skills,
                                player_name=player_name,
                                character_prompt=concept,
                                pc_id=pc_id,
                                char_name=char_name,
                                gender=gender,
                                ancestry=ancestry,
                            )
                            st.session_state.player_characters[pc_id] = pc
                            save_player_characters(
                                world_id, st.session_state.player_characters
                            )
                            st.success(
                                f"Character generated for {player_name}: {pc.name}"
                            )

            with cols[1]:
                if existing_pc:
                    st.markdown("_Character sheet available below._")

            existing_pc = st.session_state.player_characters.get(pc_id)
            if existing_pc:
                render_character_card(existing_pc)

        st.markdown("---")
        st.markdown("Use this panel to create and inspect player character sheets.")
