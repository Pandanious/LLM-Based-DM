from typing import Optional

import streamlit as st

from src.agent.types import Message
from src.game.game_state import GameState
from src.game.turn_store import load_turn_log, begin_turn, save_turn_log
from src.UI.mechanics_prompt import refresh_mechanics_prompt
from src.agent.dm_dice import refresh_corpus


def rebuild_initiative_order(game: GameState):
    pcs = game.player_characters or {}
    ordered = sorted(
        pcs.values(),
        key=lambda pc: getattr(pc, "initiative", 0),
        reverse=True,
    )
    game.initiative_order = [pc.pc_id for pc in ordered]
    game.active_turn_index = 0 if game.initiative_order else 0
    refresh_corpus()



def current_actor(game: GameState):
    if not game.initiative_order:
        return None
    if game.active_turn_index >= len(game.initiative_order):
        game.active_turn_index = 0
    pc_id = game.initiative_order[game.active_turn_index]
    return game.player_characters.get(pc_id)


def add_turn_system_message(game: GameState, pc):
    if not pc:
        return
    turn_line = (
        f"[TURN] It is now {pc.player_name} playing {pc.name}. "
        "Use this character for all actions until the turn advances. "
        "Click Next Turn when done."
    )
    game.messages.append(Message(role="system", content=turn_line))


def render_initiative_controls(game: GameState):
    
    #initiative controls.
    
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
            refresh_mechanics_prompt(game)
            # Show a quick UI notice about the active player/character
            st.info(f"Now acting: {actor.player_name} as {actor.name}")
            # Re-offer any stored options for this turn
            if getattr(game, "turn_log", None) and game.turn_log.entries:
                options = game.turn_log.entries[-1].options
                if options:
                    st.caption(f"Actions to use this turn: {', '.join(options)}")
                    game.messages.append(
                        Message(
                            role="system",
                            content=(
                                f"[TURN ACTIONS] {actor.player_name} as {actor.name}, "
                                f"available actions: {', '.join(options)}"
                            ),
                        )
                    )
            st.success(
                f"Initiative set. First turn: {actor.name} "
                f"(Initiative {getattr(actor, 'initiative', 0)})."
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
                refresh_mechanics_prompt(game)
                st.info(
                    f"Next up: {actor.player_name} as {actor.name} "
                    f"(Initiative {getattr(actor, 'initiative', 0)})."
                )
                if getattr(game, "turn_log", None) and game.turn_log.entries:
                    options = game.turn_log.entries[-1].options
                    if options:
                        st.caption(f"Actions to use this turn: {', '.join(options)}")
                        game.messages.append(
                            Message(
                                role="system",
                                content=(
                                    f"[TURN ACTIONS] {actor.player_name} as {actor.name}, "
                                    f"available actions: {', '.join(options)}"
                                ),
                            )
                        )

    if game.initiative_order:
        order_names = [
            game.player_characters.get(pc_id).name
            for pc_id in game.initiative_order
            if game.player_characters.get(pc_id)
        ]
        st.caption(f"Order: {', '.join(order_names)}")
        
