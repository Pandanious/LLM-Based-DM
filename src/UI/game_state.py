from typing import Dict
from src.game.game_state import get_global_games, GameState


def get_games():
    
    #  the shared games dict from the core game_state module.
    
    return get_global_games()


def get_or_create_game(games: Dict[str, GameState], game_id: str):
    
    #Ensure a GameState exists for this game_id and return it.
    
    if game_id not in games:
        games[game_id] = GameState()
    return games[game_id]


def reset_game(game: GameState):
    
    #Reset a GameState to a clean slate for this Game ID.
    
    game.world = None
    game.messages.clear()
    game.player_characters.clear()
    game.npcs = {}
    game.quests = {}
    game.initiative_order = []
    game.active_turn_index = 0
    if hasattr(game, "turn_log"):
        delattr(game, "turn_log")
    game.busy = False
    game.busy_by = None
    game.busy_task = None
