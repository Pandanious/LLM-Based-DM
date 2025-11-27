import streamlit as st

from typing import Optional

from src.agent.persona import DM_SYSTEM_PROMPT_TEMPLATE
from src.agent.types import Message
from src.agent.world_build import generate_world_state
from src.game.save_state import save_world_state
from src.agent.npc_gen import generate_npcs_for_world
from src.game.npc_store import save_npcs
from src.agent.quest_gen import generate_quests_for_world
from src.game.quest_store import save_quests
from src.agent.quest_commands import handle_quest_command
from src.agent.dm_dice import dm_turn_with_dice
from src.game.turn_store import load_turn_log,add_turn_note,save_turn_log,add_turn_action,begin_turn
from src.game.game_state import GameState
from src.game.models import PlayerCharacter
from src.agent.encounter_build import detect_encounter, encounter_prompt
from src.UI.mechanics_prompt import refresh_mechanics_prompt
from src.UI.initiative import current_actor, add_turn_system_message


def _resolve_actor(game: GameState, speaker: str) -> Optional[PlayerCharacter]:
    """
    Try to find the PlayerCharacter being referenced by the current speaker label.
    Speaker may be 'player' or 'player:character'.
    """
    if not game.player_characters:
        return None

    player_name = speaker
    pc_name = None
    if ":" in speaker:
        player_name, pc_name = [part.strip() for part in speaker.split(":", 1)]

    # Prefer explicit character match, then player name match.
    for pc in game.player_characters.values():
        if pc_name and pc.name.lower() == pc_name.lower():
            return pc
    for pc in game.player_characters.values():
        if pc.player_name.lower() == player_name.lower():
            return pc
    return None


def handle_world_creation(user_input: str, game_id: str, game: GameState) -> None:
    """
    Handle the very first input that creates a world.
    """
    desc_msg = Message(role="user", content=user_input, speaker="Player")
    game.messages.append(desc_msg)

    game.busy = True
    game.busy_by = "World creation"
    game.busy_task = "Forging world..."
    try:
        with st.spinner("Forging world..."):
            world = generate_world_state(
            setting_prompt=user_input,
            players=st.session_state.get("player_names") or ["Player"],
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

        players_str = ", ".join(world.players) if world.players else "Unnamed adventurers"

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
    finally:
        game.busy = False
        game.busy_by = None
        game.busy_task = None


def handle_gameplay_input(user_input: str, game: GameState, speaker: str) -> None:
    """
    Handle normal gameplay input when a world and PCs exist.
    Includes /quest commands and dice-enabled DM turns.
    """
    if game.world is not None and not hasattr(game, "turn_log"):
        game.turn_log = load_turn_log(game.world.world_id)

    # 1) Intercept /quest commands
    if handle_quest_command(user_input, game):
        game.messages.append(
            Message(role="user", content=user_input, speaker=speaker)
        )
        return

    # 2) Start-game normalization
    normalized = user_input.strip().lower()
    is_start = False
    if normalized in {"start", "begin", "let's begin", "i am ready"}:
        is_start = True
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
    refresh_mechanics_prompt(game)
    game.messages.append(
        Message(role="user", content=user_input, speaker=speaker)
    )

    # If this is the kickoff prompt, instruct the DM to name the party and active turn.
    if is_start:
        party_labels = []
        for pc in game.player_characters.values():
            party_labels.append(f"{pc.player_name} as {pc.name}")
        party_text = ", ".join(party_labels) or "the party"
        turn_label = "no initiative set yet"
        active_pc = current_actor(game)
        if active_pc:
            turn_label = f"{active_pc.player_name} as {active_pc.name}"
        game.messages.append(
            Message(
                role="system",
                content=(
                    "Opening scene guidance: explicitly mention the whole party "
                    f"({party_text}) and state whose turn it is ({turn_label}). "
                    "Then describe the scene."
                ),
            )
        )
        # Auto-advance to the current actor so everyone sees whose turn it is.
        if game.initiative_order:
            actor = current_actor(game)
            if actor:
                add_turn_system_message(game, actor)
                if game.world is not None:
                    if not hasattr(game, "turn_log"):
                        game.turn_log = load_turn_log(game.world.world_id)
                    game.turn_log = begin_turn(game.turn_log, actor)
                    save_turn_log(game.turn_log)

    # 3a) Enforce initiative order: block out-of-turn actions
    if game.initiative_order:
        expected_actor = current_actor(game)
        actor = _resolve_actor(game, speaker)
        if expected_actor and (not actor or expected_actor.pc_id != actor.pc_id):
            expected_label = f"{expected_actor.player_name} as {expected_actor.name}"
            game.messages.append(
                Message(
                    role="system",
                    content=(
                        f"It's not your turn. Active turn: {expected_label}. "
                        "Click Next Turn when they finish."
                    ),
                )
            )
            return

    # 3b) Encounter detection
    encounter = detect_encounter(user_input)
    actor = _resolve_actor(game, speaker)
    if encounter and game.active_encounter != encounter.encounter_type:
        game.active_encounter = encounter.encounter_type
        game.active_encounter_summary = encounter.summary
        game.encounter_history.append(encounter.summary)
        player_name = actor.player_name if actor else speaker
        char_name = actor.name if actor else "Unknown character"
        game.messages.append(
            Message(
                role="system",
                content=encounter_prompt(encounter, player_name, char_name),
            )
        )
        if hasattr(game, "turn_log"):
            note = f"Encounter started: {encounter.encounter_type}"
            game.turn_log = add_turn_note(game.turn_log, note)
            save_turn_log(game.turn_log)

    # 4) DM turn, with dice support for /action
    game.busy = True
    game.busy_by = speaker
    game.busy_task = "DM is thinking..."
    try:
        with st.spinner("The DM is thinking..."):
            game.messages = dm_turn_with_dice(
            game.messages,
            game.player_characters,
        )
        if hasattr(game, "turn_log"):
            note = f"{speaker}: {user_input}"
            game.turn_log = add_turn_note(game.turn_log, note)
            actor = _resolve_actor(game, speaker)
            tags = ["action"] if user_input.strip().startswith("/action") else None
            game.turn_log = add_turn_action(
                game.turn_log,
                player_name=speaker,
                actor=actor,
                content=user_input,
                tags=tags,
            )
            save_turn_log(game.turn_log)
        # Explicitly remind to advance the turn, with both player and character names.
        actor = _resolve_actor(game, speaker)
        if actor:
            reminder = (
                f"Turn resolved for {actor.player_name} as {actor.name}. "
                "Click Next Turn to move to the next character."
            )
        else:
            reminder = (
                f"Turn resolved for {speaker}. "
                "Click Next Turn to move to the next character."
            )
        game.messages.append(Message(role="system", content=reminder))
        # Suggest who is next in initiative, if available
        if game.initiative_order:
            if game.initiative_order:
                next_idx = (game.active_turn_index + 1) % len(game.initiative_order)
                next_pc = game.player_characters.get(game.initiative_order[next_idx])
                if next_pc:
                    game.messages.append(
                        Message(
                            role="system",
                            content=(
                                f"Next up: {next_pc.player_name} as {next_pc.name}. "
                                "Press Next Turn to hand over."
                            ),
                    )
                )
    finally:
        game.busy = False
        game.busy_by = None
        game.busy_task = None
