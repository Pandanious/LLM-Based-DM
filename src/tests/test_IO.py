from datetime import datetime
from pathlib import Path

from src.game.game_state import GameState
from src.game.models import World_State, PlayerCharacter, NPC, Quest
from src.game.save_load import save_world_bundle, load_world_bundle, save_world_seed_bundle


def _sample_world():
    return World_State(
        world_id="world-1",
        title="Test World",
        setting_prompt="grim swamp",
        world_summary="short summary",
        lore="deep lore",
        players=["Alice", "Bob"],
        created_on=datetime.utcnow(),
        themes=["mystery"],
    )


def _sample_pc():
    return PlayerCharacter(
        pc_id="pc1",
        player_name="Alice",
        name="Aria",
        gender="",
        ancestry="human",
        archetype="rogue",
        level=1,
        concept="sneaky",
        stats={"STR": 8, "DEX": 14},
        max_hp=10,
        current_hp=10,
        inventory=["rope"],
    )


def _sample_npc():
    return NPC(
        npc_id="npc1",
        world_id="world-1",
        name="Gorn",
        role="merchant",
        location="market",
        description="gruff trader",
        hooks=["needs escort"],
    )


def _sample_quest():
    return Quest(
        quest_id="q1",
        world_id="world-1",
        title="Find the Gem",
        summary="Retrieve the gem from the cave",
        giver_npc_id="npc1",
        steps=["enter cave", "find gem"],
        rewards=["50 gold"],
    )


def test_save_and_load_bundle(tmp_path: Path):
    game = GameState(
        world=_sample_world(),
        player_characters={"pc1": _sample_pc()},
        npcs={"npc1": _sample_npc()},
        quests={"q1": _sample_quest()},
        initiative_order=["pc1"],
        active_turn_index=0,
    )

    bundle_path = save_world_bundle(game, dest_dir=tmp_path)
    loaded = load_world_bundle(bundle_path)

    world, players, npcs, quests, initiative_order, active_turn_index = loaded

    assert world.world_id == "world-1"
    assert world.title == "Test World"
    assert list(players.keys()) == ["pc1"]
    assert players["pc1"].name == "Aria"
    assert npcs["npc1"].name == "Gorn"
    assert quests["q1"].title == "Find the Gem"
    assert initiative_order == ["pc1"]
    assert active_turn_index == 0


def test_save_world_seed_bundle(tmp_path: Path):
    game = GameState(world=_sample_world())
    path = save_world_seed_bundle(game, dest_dir=tmp_path)
    assert path.exists()
    assert "Test_World" in path.name
