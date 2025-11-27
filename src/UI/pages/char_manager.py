import streamlit as st

from src.game.game_state import get_global_games
from src.game.player_store import save_player_characters
from src.agent.char_gen import generate_character_sheet


def get_game_and_world():
    query_params = st.query_params
    game_id = query_params.get("game_id", "default")

    games = get_global_games()
    game = games.get(game_id)

    if not game:
        st.error(f"No active game for game_id '{game_id}'")
        return None, None, game_id

    world = game.world
    if world is None:
        st.warning("World has not been created yet for this game.")
        return game, None, game_id

    return game, world, game_id


def render_character_card(pc) -> None:
    # Show a character sheet in a collapsible card.
    with st.expander(f"{pc.name} ({pc.player_name}) - Level {pc.level}"):
        st.markdown(f"**Concept:** {pc.concept}")
        st.markdown(f"**Gender:** {pc.gender}")
        st.markdown(f"**Ancestry:** {pc.ancestry}")
        st.markdown(f"**Archetype:** {pc.archetype}")
        st.markdown(f"**HP:** {pc.current_hp} / {pc.max_hp}")
        st.markdown(f"**Initiative:** {getattr(pc, 'initiative', '?')}")


        st.markdown("**Stats**")
        cols = st.columns(6)
        for i, key in enumerate(["STR", "DEX", "CON", "INT", "WIS", "CHA"]):
            with cols[i]:
                st.metric(key, pc.stats.get(key, 10))

        if pc.skills:
            with st.expander("Skills", expanded=False):
                for s in pc.skills:
                    st.markdown(f"- {s}")

        if pc.inventory:
            with st.expander("Inventory", expanded=False):
                for item in pc.inventory:
                    st.markdown(f"- {item}")

        if pc.notes:
            with st.expander("Notes", expanded=False):
                for note in pc.notes:
                    st.markdown(f"- {note}")

# layout

st.set_page_config(page_title="Character Manager", layout="wide")
st.title("Character Manager")

game, world, game_id = get_game_and_world()

st.markdown(f"**Game ID:** `{game_id}`")

if world is None:
    st.stop()

if getattr(game, "busy", False):
    st.info(
        f"Model busy: {game.busy_task or 'In progress'} "
        f"(started by {game.busy_by or 'another player'})."
    )

st.markdown(f"**World:** {world.title}")
st.markdown(world.world_summary)
st.markdown("---")

st.subheader("Local Players at This Browser")

# Initialize local_player_names from main app's player_names if present

if "local_player_names" not in st.session_state:
    # Prefer names set on the main page; fallback to game-stored names; else placeholder
    base = (
        st.session_state.get("player_names", [])
        or getattr(game, "player_names", [])
        or getattr(game.world, "players", [])
    )
    if base:
        st.session_state.local_player_names = list(base)
    else:
        st.session_state.local_player_names = ["char1", "char2"]

players_csv = st.text_input(
    "Player names (comma-separated, local to this browser)",
    placeholder=", ".join(st.session_state.local_player_names),
    help=(
        "Everyone who connects with this Game ID shares the same world and characters. "
        "These names are just for this browser's character generation UI."
    ),
)

local_player_names = [p.strip() for p in players_csv.split(",") if p.strip()]
st.session_state.local_player_names = local_player_names
st.session_state.player_names = local_player_names

if not local_player_names:
    st.info("Add at least one player name above to start creating characters.")
    st.stop()

# Character generation queue (FIFO) per game_id
queue_key = f"char_gen_queue_{game_id}"
busy_key = f"char_gen_busy_{game_id}"
if queue_key not in st.session_state:
    st.session_state[queue_key] = []
if busy_key not in st.session_state:
    st.session_state[busy_key] = False

st.markdown("---")
st.subheader("Create / Re-roll Characters for Local Players")

# per char Ui

for player_name in local_player_names:
    st.markdown(f"### Player: {player_name}")

    # pc_id and any existing PC for this player
    pc_id = f"{world.world_id}_{player_name.lower().replace(' ', '_')}"
    existing_pc = game.player_characters.get(pc_id)

    # Keys for Streamlit widgets (must be unique per player)
    name_key = f"char_name_{pc_id}"
    gender_key = f"gender_{pc_id}"
    ancestry_key = f"ancestry_{pc_id}"
    concept_key = f"concept_{pc_id}"

    # Defaults from existing character, if any
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
        placeholder="e.g. The model can ignore obtuse prompts/inputs.""\nTry to keep it close to the world generated.",
    )

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button(
            f"Generate / Re-roll for {player_name}", key=f"gen_{pc_id}"
        ):
            if not concept.strip():
                st.warning(f"Please describe the character idea for {player_name} first.")
            else:
                st.session_state[queue_key].append(
                    {
                        "player_name": player_name,
                        "pc_id": pc_id,
                        "char_name": char_name,
                        "gender": gender,
                        "ancestry": ancestry,
                        "concept": concept,
                    }
                )
                st.success(f"Queued generation for {player_name}.")

    with cols[1]:
        if existing_pc:
            st.markdown("_Existing character sheet available below._")

    # Refresh existing_pc in case we just re-rolled
    
    existing_pc = game.player_characters.get(pc_id)
    if existing_pc:
        render_character_card(existing_pc)

st.markdown("---")
st.subheader("All Characters in This Game")

if not game.player_characters:
    st.info("No characters created yet for this game.")
else:
    for pc_id, pc in game.player_characters.items():
        render_character_card(pc)

st.markdown("---")
st.subheader("Queued Character Generations (FIFO)")

queue = st.session_state[queue_key]
if not queue:
    st.caption("Queue is empty.")
else:
    for idx, item in enumerate(queue, start=1):
        st.caption(f"{idx}. {item['player_name']} \u2192 {item['char_name']} ({item['ancestry']})")

global_busy = getattr(game, "busy", False)
if global_busy:
    st.warning(
        f"Character generation locked: {game.busy_task or 'In progress'} "
        f"(started by {game.busy_by or 'another player'})."
    )
process_disabled = (not queue) or st.session_state[busy_key] or global_busy
if st.button("Process next queued generation", disabled=process_disabled):
    st.session_state[busy_key] = True
    job = queue.pop(0)
    game.busy = True
    game.busy_by = job["player_name"]
    game.busy_task = "Generating character"
    try:
        with st.spinner(f"Generating character for {job['player_name']}..."):
            pc = generate_character_sheet(
                world_summary=world.world_summary,
                world_skills=world.skills,
                player_name=job["player_name"],
                character_prompt=job["concept"],
                pc_id=job["pc_id"],
                char_name=job["char_name"],
                gender=job["gender"],
                ancestry=job["ancestry"],
            )
            game.player_characters[job["pc_id"]] = pc
            save_player_characters(world.world_id, game.player_characters)
            st.success(f"Character generated for {job['player_name']}: {pc.name}")
    except Exception as e:
        st.error(f"Character generation failed: {e}")
    finally:
        game.busy = False
        game.busy_by = None
        game.busy_task = None
        st.session_state[busy_key] = False
