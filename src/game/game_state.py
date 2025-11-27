from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

from src.game.models import World_State, PlayerCharacter, NPC, Quest
from src.agent.types import Message

@dataclass
class GameState:
    world: Optional[World_State] = None
    messages: List[Message] = field(default_factory=list)
    player_names: List[str] = field(default_factory=list)
    player_characters: Dict[str, PlayerCharacter] = field(default_factory=dict)
    npcs: Dict[str, NPC] = field(default_factory=dict)
    quests: Dict[str, Quest] = field(default_factory=dict)
    initiative_order: List[str] = field(default_factory=list)  # ordered list of pc_ids
    active_turn_index: int = 0  # index into initiative_order
    active_encounter: Optional[str] = None
    active_encounter_summary: Optional[str] = None
    encounter_history: List[str] = field(default_factory=list)
    busy: bool = False  # shared flag so all sessions know the model is running
    busy_by: Optional[str] = None  # who triggered the work
    busy_task: Optional[str] = None  # what is running

@lru_cache(maxsize=1)
def get_global_games() -> Dict[str, GameState]:
    
    # Global dictionary of all active games, keyed by game_id.Because of @lru_cache, this dict is created once 
    # per Python process and reused across all Streamlit sessions. That makes it shared state.
    
    return {}
