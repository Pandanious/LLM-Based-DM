from dataclasses import dataclass,field,asdict
from typing import List,Optional,Dict
from datetime import datetime


@dataclass
class World_State:
    # description of the game world.

    world_id : str          # some id 
    title : str             # Name of setting
    setting_prompt : str            # user def settings             
    world_summary : str             # LLM gen setting
    lore : str                      # LLM gen, details for DM
    players : List[str]             
    created_on : datetime           #creaton date for reuse.
    last_played : Optional[datetime] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        # convert datetimes to iso strings
        if isinstance(self.created_on, datetime):
            data["created_on"] = self.created_on.isoformat()
        if isinstance(self.last_played, datetime):
            data["last_played"] = self.last_played.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "World_State":
        created_raw = data.get("created_on")
        last_raw = data.get("last_played")

        created_on = (
            datetime.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else datetime.utcnow()
        )
        last_played = (
            datetime.fromisoformat(last_raw)
            if isinstance(last_raw, str)
            else None
        )

        return cls(
            world_id=data["world_id"],
            title=data["title"],
            setting_prompt=data["setting_prompt"],
            world_summary=data["world_summary"],
            lore=data["lore"],
            players=list(data.get("players", [])),
            created_on=created_on,
            last_played=last_played,
            notes=list(data.get("notes", [])),
        )

@dataclass
class PlayerCharacter:
    """
    A single player character (PC) in the world.
    This is what we save to JSON and feed summaries to the LLM.
    """
    pc_id: str                # unique id, e.g. "alice_pc_1"
    player_name: str          # the human player at the table: "Alice"
    name: str                 # the character's name in-game
    concept: str              # short concept: "grizzled ex-soldier turned hunter"
    ancestry: str             # race/species/etc.
    archetype: str            # class/role: "hacker", "fighter", etc.
    level: int
    stats: Dict[str, int]     # e.g. {"STR": 12, "DEX": 14, ...}
    max_hp: int
    current_hp: int
    skills: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    created_on: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        # datetime to ISO
        if isinstance(self.created_on, datetime):
            data["created_on"] = self.created_on.isoformat()
        if isinstance(self.last_updated, datetime):
            data["last_updated"] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerCharacter":
        created_raw = data.get("created_on")
        updated_raw = data.get("last_updated")

        created_on = (
            datetime.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else datetime.utcnow()
        )
        last_updated = (
            datetime.fromisoformat(updated_raw)
            if isinstance(updated_raw, str)
            else None
        )

        return cls(
            pc_id=data["pc_id"],
            player_name=data["player_name"],
            name=data["name"],
            concept=data["concept"],
            ancestry=data.get("ancestry", ""),
            archetype=data.get("archetype", ""),
            level=int(data.get("level", 1)),
            stats={k: int(v) for k, v in data.get("stats", {}).items()},
            max_hp=int(data.get("max_hp", 10)),
            current_hp=int(data.get("current_hp", 10)),
            skills=list(data.get("skills", [])),
            inventory=list(data.get("inventory", [])),
            notes=list(data.get("notes", [])),
            created_on=created_on,
            last_updated=last_updated,
        )