from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

from src.game.models import World_State, PlayerCharacter, NPC
from src.agent.types import Message

@dataclass
class GameState:
    world: Optional[World_State] = None
    messages: List[Message] = field(default_factory=list)
    player_characters: Dict[str, PlayerCharacter] = field(default_factory=dict)
    npcs: Dict[str, NPC] = field(default_factory=dict)

    
@lru_cache(maxsize=1)
def get_global_games() -> Dict[str, GameState]:
    
    # Global dictionary of all active games, keyed by game_id.Because of @lru_cache, this dict is created once 
    # per Python process and reused across all Streamlit sessions. That makes it shared state.
    
    return {}