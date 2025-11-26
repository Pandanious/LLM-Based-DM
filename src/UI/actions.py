import streamlit as st

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
from src.game.turn_store import load_turn_log, add_turn_note, save_turn_log
from src.game.game_state import GameState


def handle_world_creation(user_input: str, game_id: str, game: GameState) -> None:
    """
    Handle the very first input that creates a world.
    """
    desc_msg = Message(role="user", content=user_input, speaker="Player")
    game.messages.append(desc_msg)

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


def handle_gameplay_input(user_input: str, game: GameState, speaker: str) -> None:
    """
    Handle normal gameplay input when a world and PCs exist.
    Includes /quest commands and dice-enabled DM turns.
    """
    # 1) Intercept /quest commands
    if handle_quest_command(user_input, game):
        game.messages.append(
            Message(role="user", content=user_input, speaker=speaker)
        )
        return

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
