from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class World_State:
    world_id: str
    title: str
    setting_prompt: str
    world_summary: str
    lore: str
    players: List[str]
    created_on: datetime
    last_played: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)

    # NEW: structured world content
    skills: List[str] = field(default_factory=list)  # world-wide skill list

    # list of {"name": str, "description": str}
    major_locations: List[Dict[str, str]] = field(default_factory=list)
    minor_locations: List[Dict[str, str]] = field(default_factory=list)

    # list of theme/tone bullet strings
    themes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
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
            skills=list(data.get("skills", [])),  # safe for old saves
            major_locations=list(data.get("major_locations", [])),
            minor_locations=list(data.get("minor_locations", [])),
            themes=list(data.get("themes", [])),
        )
@dataclass
class PlayerCharacter:
    """
    A single player character (PC) in the world.
    This is what we save to JSON and feed summaries to the LLM.
    """
    pc_id: str                # unique id, e.g. "default_alice"
    player_name: str          # real player name at the table
    name: str                 # character's in-world name
    gender: str               # "female", "male", "non-binary", etc.
    ancestry: str             # race/species/etc.
    archetype: str            # class/role: "hacker", "fighter", etc.
    level: int
    concept: str              # short concept/background
    stats: Dict[str, int]     # {"STR": 12, "DEX": 14, ...}
    max_hp: int
    current_hp: int
    initiative: int = 0
    skills: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    created_on: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None
    

    def to_dict(self) -> dict:
        data = asdict(self)
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
            gender=data.get("gender", ""),
            ancestry=data.get("ancestry", ""),
            archetype=data.get("archetype", ""),
            level=int(data.get("level", 1)),
            concept=data.get("concept", ""),
            stats={k: int(v) for k, v in data.get("stats", {}).items()},
            max_hp=int(data.get("max_hp", 10)),
            initiative=int(data.get("initiative", 0)),
            current_hp=int(data.get("current_hp", 10)),
            skills=list(data.get("skills", [])),
            inventory=list(data.get("inventory", [])),
            notes=list(data.get("notes", [])),
            created_on=created_on,
            last_updated=last_updated,
        )
    

@dataclass
class NPC:
    npc_id: str
    world_id: str

    name: str
    role: str
    location: str

    description: str
    hooks: List[str] = field(default_factory=list)
    attitude: str = "neutral"
    tags: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    
    created_on: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(self.created_on, datetime):
            data["created_on"] = self.created_on.isoformat()
        if isinstance(self.last_updated, datetime):
            data["last_updated"] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
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
            npc_id=data["npc_id"],
            world_id=data["world_id"],
            name=data["name"],
            role=data.get("role", ""),
            location=data.get("location", ""),
            description=data.get("description", data.get("desc", "")),
            hooks=list(data.get("hooks", [])),
            attitude=data.get("attitude", "neutral"),
            tags=list(data.get("tags", [])),
            inventory=list(data.get("inventory", [])),
            created_on=created_on,
            last_updated=last_updated,
        )
    
@dataclass
class Quest:
    quest_id: str
    world_id: str

    title: str
    summary: str

    giver_npc_id: Optional[str] = None
    giver_name: Optional[str] = None
    target_location: Optional[str] = None

    steps: List[str] = field(default_factory=list)
    rewards: List[str] = field(default_factory=list)
    reward_items: List[str] = field(default_factory=list)

    status: str = "available"  # "available", "in_progress", "completed", "failed"

    created_on: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(self.created_on, datetime):
            data["created_on"] = self.created_on.isoformat()
        if isinstance(self.last_updated, datetime):
            data["last_updated"] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
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
            quest_id=data["quest_id"],
            world_id=data["world_id"],
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            giver_npc_id=data.get("giver_npc_id"),
            giver_name=data.get("giver_name"),
            target_location=data.get("target_location"),
            steps=list(data.get("steps", [])),
            rewards=list(data.get("rewards", [])),
            reward_items=list(data.get("reward_items", [])),
            status=data.get("status", "available"),
            created_on=created_on,
            last_updated=last_updated,
        )
    

@dataclass
class Item:
    item_id: str
    item_name: str
    item_category: str = ""
    item_subcategory: str = ""
    item_dice_damage: str = ""
    item_damage_type: str = ""
    item_properties: List[str] = field(default_factory=list)
    created_on: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(self.created_on, datetime):
            data["created_on"] = self.created_on.isoformat()
        if isinstance(self.last_updated, datetime):
            data["last_updated"] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        created_raw = data.get("created_on")
        updated_raw = data.get("last_updated")
        item_properties = list(data.get("item_properties", []))
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
            item_id=data["item_id"],
            item_name=data.get("item_name", ""),
            item_category=data.get("item_category", ""),
            item_subcategory=data.get("item_subcategory", ""),
            item_dice_damage=data.get("item_dice_damage", ""),
            item_damage_type=data.get("item_damage_type", ""),
            item_properties=item_properties,
            created_on=created_on,
            last_updated=last_updated,
        )
